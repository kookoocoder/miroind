import json

import pytest

from app import create_app
from app.services.miroind import MiroIndService


def _payload(**overrides):
    payload = {
        "brand": {
            "name": "Nayi Disha",
            "positioning": "A practical learning service for everyday progress",
            "tone": "warm and clear",
            "audience_relationship": "a helpful partner",
            "red_lines": ["no hidden fees"],
            "preferred_vocabulary": ["simple", "help"],
        },
        "asset": {
            "type": "text",
            "title": "Learn at your pace",
            "content": "Simple lessons to help you take the next step.",
            "language": "en",
        },
        "audience": {
            "region": "Maharashtra",
            "language": "English",
            "age_band": "25-34",
            "occupation": "small business owner",
            "city_tier": "tier_2",
            "income_band": "middle",
        },
        "config": {
            "report_language": "en",
            "interaction_format": "short_post",
            "persona_count": 6,
            "budget": 20,
        },
    }
    for section, values in overrides.items():
        payload[section].update(values)
    return payload


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(MiroIndService, "RUNS_DIR", tmp_path)
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_successful_offline_run_has_stable_report_shape(client):
    response = client.post("/api/miroind/runs", json=_payload())

    assert response.status_code == 200
    body = response.json
    assert body["success"] is True
    assert body["data"]["status"] == "completed"
    assert body["data"]["run_id"].startswith("miroind_")
    report = body["data"]["report"]
    assert report["usage_metadata"]["offline"] is True
    assert report["usage_metadata"]["network_calls"] is False
    assert len(report["persona_reactions"]) == 6
    repeat = client.post("/api/miroind/runs", json=_payload())
    assert repeat.status_code == 200
    assert repeat.json["data"]["report"] == report
    for field in (
        "scenario",
        "audience_summary",
        "overall_image_impact_direction",
        "positive_reactions",
        "negative_reactions",
        "mixed_reactions",
        "risk_points",
        "misunderstandings",
        "persona_reactions",
        "disagreements",
        "recommendations",
        "rewrite_options",
        "assumptions",
        "uncertainty",
        "limitations",
        "usage_metadata",
    ):
        assert field in report


def test_invalid_and_missing_fields_are_structured_without_traceback(client):
    response = client.post(
        "/api/miroind/runs",
        json={
            "brand": {},
            "asset": {"type": "video"},
            "audience": {},
            "config": {"persona_count": 3, "budget": 0},
        },
    )

    assert response.status_code == 400
    body = response.json
    assert body["success"] is False
    assert body["fields"]["brand.name"] == "is required"
    assert body["fields"]["asset.type"] == "must be 'text'"
    assert body["fields"]["config.persona_count"]
    assert body["fields"]["config.budget"]
    assert "traceback" not in body


def test_risk_detection_covers_reported_categories_and_shape(client):
    payload = _payload(
        asset={
            "content": (
                "Limited time offer: ₹999 today. Share personal data and OTP. "
                "Our 100% guaranteed best result is instant."
            )
        },
        audience={"language": "Hindi"},
    )
    report = client.post("/api/miroind/runs", json=payload).json["data"]["report"]

    categories = {point["category"] for point in report["risk_points"]}
    assert {
        "pricing_urgency",
        "trust_privacy",
        "exaggerated_claims",
        "regional_language_fit",
    } <= categories
    assert all(
        {"category", "severity", "signals", "evidence", "why_it_matters"}
        <= point.keys()
        for point in report["risk_points"]
    )
    assert report["negative_reactions"] or report["mixed_reactions"]


def test_hindi_report_has_translated_labels_and_quality_note(client):
    payload = _payload(
        asset={
            "title": "आसान सीखना",
            "content": "सरल पाठ आपकी मदद करते हैं।",
            "language": "hi",
        },
        audience={"language": "Hindi"},
        config={"report_language": "hi", "persona_count": 4},
    )
    report = client.post("/api/miroind/runs", json=payload).json["data"]["report"]

    assert "रिपोर्ट" in report["title"]
    assert report["labels"]["recommendations"] == "सुझाव"
    assert "हिंदी" in report["usage_metadata"]["translation_quality_note"]
    assert report["usage_metadata"]["report_language"] == "hi"


def test_run_is_persisted_and_get_returns_same_result(client, tmp_path):
    post_body = client.post("/api/miroind/runs", json=_payload()).json
    run_id = post_body["data"]["run_id"]
    stored_path = tmp_path / f"{run_id}.json"

    assert stored_path.exists()
    assert json.loads(stored_path.read_text(encoding="utf-8")) == post_body["data"]

    get_response = client.get(f"/api/miroind/runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json == post_body


def test_unknown_run_returns_404(client):
    response = client.get("/api/miroind/runs/miroind_000000000000000000000000")

    assert response.status_code == 404
    assert response.json["success"] is False
    assert "traceback" not in response.json
