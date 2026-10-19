import json
import re

import pytest

from app import create_app
from app.config import Config
from app.models.boss_scenario import manifest_sha256, normalize_manifest
from app.services.boss_scenarios import BossScenarioStore


def _payload(**overrides):
    payload = {
        "brand": {
            "name": "Nayi Disha",
            "positioning": "A practical learning service for everyday progress",
            "tone": "warm and clear",
            "audience_relationship": "a helpful partner",
            "red_lines": ["no hidden fees"],
            "preferred_vocabulary": ["simple", "help"],
            "claims_must_not_invent": ["outcomes without evidence"],
        },
        "asset": {
            "type": "text",
            "title": "Learn at your pace",
            "content": "Simple lessons to help you take the next step.",
            "language": "English",
        },
        "audience": {
            "region": "Maharashtra",
            "language": "Marathi",
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
        if section in payload:
            payload[section].update(values)
        else:
            payload[section] = values
    return payload


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "BOSS_SCENARIOS_DIR", str(tmp_path))
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_create_read_and_list_persist_canonical_manifest(client, tmp_path):
    response = client.post("/api/boss/scenarios", json=_payload())

    assert response.status_code == 200
    data = response.json["data"]
    manifest = data["manifest"]
    scenario_id = data["scenario_id"]
    assert re.fullmatch(r"scenario_[a-f0-9]{24}", scenario_id)
    assert data["revision"] == 1
    assert data["status"] == "created"
    assert data["manifest_sha256"] == manifest["provenance"]["manifest_sha256"]
    assert manifest["schema_version"] == "boss.scenario.v1"
    assert manifest["audiences"][0]["country"] == "IN"
    assert manifest["audiences"][0]["language_signal"] == "Marathi"
    assert manifest["audiences"][0]["persona_pack_id"] == "boss-india-v1"
    assert manifest["assets"][0]["kind"] == "text"
    assert manifest["run_config"] == {
        "budget": 20,
        "execution_mode": "offline",
        "graph_memory_update": False,
        "interaction_formats": ["short_post"],
        "persona_count": 6,
        "report_language": "en",
        "seed": None,
        "timezone": "Asia/Kolkata",
    }

    scenario_dir = tmp_path / scenario_id
    assert json.loads((scenario_dir / "manifest.json").read_text(encoding="utf-8")) == manifest
    assert json.loads((scenario_dir / "revisions/1.json").read_text(encoding="utf-8")) == manifest

    read_response = client.get(f"/api/boss/scenarios/{scenario_id}")
    assert read_response.status_code == 200
    assert read_response.json == response.json

    list_response = client.get("/api/boss/scenarios?limit=1")
    assert list_response.status_code == 200
    assert list_response.json["data"][0] == data


def test_legacy_payload_normalization_and_hash_are_deterministic():
    scenario_id = "scenario_0123456789abcdef01234567"
    first = normalize_manifest(_payload(), scenario_id=scenario_id, revision=1)
    second = normalize_manifest(_payload(), scenario_id=scenario_id, revision=1)

    assert first == second
    assert first["scenario_id"] == scenario_id
    assert first["brand"]["claims_must_not_invent"] == ["outcomes without evidence"]
    assert first["audiences"][0]["language_signal"] == "Marathi"
    assert first["assets"][0]["kind"] == "text"
    assert first["run_config"]["interaction_formats"] == ["short_post"]
    assert first["run_config"]["execution_mode"] == "offline"
    assert manifest_sha256(first) == first["provenance"]["manifest_sha256"]


def test_revision_increments_and_replaces_current_manifest(client, tmp_path):
    created = client.post("/api/boss/scenarios", json=_payload()).json["data"]
    scenario_id = created["scenario_id"]
    revised_payload = _payload(brand={"positioning": "A clearer learning service"})

    response = client.post(
        f"/api/boss/scenarios/{scenario_id}/revisions",
        json=revised_payload,
    )

    assert response.status_code == 200
    revised = response.json["data"]
    assert revised["scenario_id"] == scenario_id
    assert revised["revision"] == 2
    assert revised["status"] == "updated"
    assert revised["manifest"]["brand"]["positioning"] == "A clearer learning service"
    assert revised["manifest_sha256"] != created["manifest_sha256"]

    scenario_dir = tmp_path / scenario_id
    assert json.loads((scenario_dir / "revisions/1.json").read_text(encoding="utf-8")) == created["manifest"]
    assert json.loads((scenario_dir / "revisions/2.json").read_text(encoding="utf-8")) == revised["manifest"]
    assert json.loads((scenario_dir / "manifest.json").read_text(encoding="utf-8")) == revised["manifest"]
    assert client.get(f"/api/boss/scenarios/{scenario_id}").json["data"] == revised


def test_invalid_fields_secrets_and_path_traversal_are_safe(client):
    too_long = _payload(brand={"name": "x" * 121})
    response = client.post("/api/boss/scenarios", json=too_long)
    assert response.status_code == 400
    assert response.json["fields"]["brand.name"] == "must be at most 120 characters"
    assert "traceback" not in response.json

    unsafe = _payload(
        asset={"storage_key": "../../secret.txt"},
        config={"api_key": "do-not-persist"},
    )
    response = client.post("/api/boss/scenarios", json=unsafe)
    assert response.status_code == 400
    assert "assets[0].storage_key" in response.json["fields"]
    assert "config.api_key" in response.json["fields"]

    assert client.get("/api/boss/scenarios/../../etc/passwd").status_code == 404
    assert client.get("/api/boss/scenarios/scenario_000000000000000000000000").status_code == 404
    assert client.post(
        "/api/boss/scenarios/scenario_../../etc/revisions",
        json=_payload(),
    ).status_code == 404


def test_store_readback_is_atomic_and_does_not_persist_paths_or_secrets(tmp_path):
    store = BossScenarioStore(tmp_path)
    manifest = store.create(_payload())
    scenario_dir = tmp_path / manifest["scenario_id"]

    assert store.get(manifest["scenario_id"]) == manifest
    assert not list(scenario_dir.rglob("*.tmp"))
    persisted = json.dumps(manifest, ensure_ascii=False)
    assert str(tmp_path) not in persisted
    assert "do-not-persist" not in persisted
    assert "api_key" not in persisted

    revised = store.create_revision(
        manifest["scenario_id"],
        _payload(provenance={"input_source": "user"}),
    )
    assert store.get_revision(manifest["scenario_id"], 2) == revised
    assert store.get(manifest["scenario_id"]) == revised


def test_absolute_provenance_path_and_invalid_list_limits_return_structured_errors(client):
    response = client.post(
        "/api/boss/scenarios",
        json=_payload(provenance={"input_source": "/Users/example/input.json"}),
    )
    assert response.status_code == 400
    assert response.json["fields"]["provenance.input_source"] == "must not be an absolute path"

    assert client.get("/api/boss/scenarios?limit=0").status_code == 400
    assert client.get("/api/boss/scenarios?limit=101").status_code == 400
    assert client.get("/api/boss/scenarios?limit=bad").status_code == 400
