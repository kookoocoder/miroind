import csv
import io
import json
import re

import pytest

from app import create_app
from app.config import Config
from app.models.boss_scenario import normalize_manifest
from app.services.boss_personas import (
    BOSS_TIMEZONE,
    build_boss_simulation_config,
    materialize_boss_profiles,
    serialize_reddit_profiles,
    serialize_twitter_csv,
)


SCENARIO_ID = "scenario_0123456789abcdef01234567"


def _payload(*, asset=None, audiences=None):
    payload = {
        "scenario_id": SCENARIO_ID,
        "brand": {
            "name": "Nayi Disha",
            "positioning": "A practical learning service for everyday progress",
            "tone": "warm and clear",
            "audience_relationship": "a helpful partner",
            "red_lines": ["no hidden fees"],
            "preferred_vocabulary": ["simple", "help"],
            "claims_must_not_invent": ["outcomes without evidence"],
        },
        "asset": asset
        or {
            "type": "text",
            "title": "Learn at your pace",
            "content": "Exact submitted copy: learn at your pace.",
            "language": "English",
        },
        "audiences": audiences
        or [
            {
                "id": "audience_maharashtra_tier2",
                "region": "Maharashtra",
                "language": "Marathi",
                "age_band": "25-34",
                "occupation": "small business owner",
                "city_tier": "tier_2",
                "income_band": "middle",
                "local_context": "Neighbourhood businesses and local referrals",
            }
        ],
        "run_config": {
            "report_language": "en",
            "interaction_formats": ["short_post"],
            "persona_count": 4,
            "budget": 20,
            "seed": 1234,
        },
    }
    return payload


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "BOSS_SCENARIOS_DIR", str(tmp_path))
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_profiles_are_stable_and_use_only_declared_india_context():
    manifest = normalize_manifest(_payload(), scenario_id=SCENARIO_ID, revision=1)

    first = materialize_boss_profiles(manifest)
    second = materialize_boss_profiles(manifest)

    assert [profile.to_dict() for profile in first] == [profile.to_dict() for profile in second]
    assert [profile.agent_id for profile in first] == [0, 1, 2, 3, 4]
    assert first[0].username == "boss_scenario_0123456789abcdef01234567_brand"
    assert all("-" not in profile.username for profile in first)
    assert all(not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", profile.username) for profile in first)

    brand = first[0]
    audience = first[1]
    assert brand.account_kind == "brand"
    assert audience.account_kind == "audience"
    assert audience.country == "IN"
    assert audience.timezone == BOSS_TIMEZONE
    assert audience.region == "Maharashtra"
    assert audience.occupation == "small business owner"
    assert audience.city_tier == "tier_2"
    assert audience.income_band == "middle"
    assert audience.local_context in audience.user_char
    assert audience.language_signal == "Marathi"
    for profile in (brand, audience):
        assert "no hidden fees" in profile.user_char
        assert "simple" in profile.user_char
        assert "outcomes without evidence" in profile.user_char
        assert "sensitive_attributes: not inferred" in profile.user_char
    assert "age" not in audience.profile_context
    assert "gender" not in audience.profile_context
    assert "mbti" not in audience.profile_context


def test_reddit_and_twitter_serializers_keep_stable_agent_ids():
    manifest = normalize_manifest(_payload(), scenario_id=SCENARIO_ID, revision=1)
    profiles = materialize_boss_profiles(manifest)

    reddit = serialize_reddit_profiles(profiles)
    assert [item["user_id"] for item in reddit] == [0, 1, 2, 3, 4]
    assert reddit[0]["username"] == profiles[0].username
    assert reddit[1]["persona"] == reddit[1]["user_char"]
    assert reddit[1]["bio"] == profiles[1].bio

    rows = list(csv.DictReader(io.StringIO(serialize_twitter_csv(profiles))))
    assert rows[0].keys() == {
        "agent_id",
        "user_id",
        "name",
        "username",
        "user_char",
        "description",
    }
    assert [int(row["agent_id"]) for row in rows] == [0, 1, 2, 3, 4]
    assert [int(row["user_id"]) for row in rows] == [0, 1, 2, 3, 4]
    assert rows[1]["username"] == profiles[1].username
    assert "no hidden fees" in rows[1]["user_char"]


def test_config_preserves_exact_initial_post_and_india_timezone():
    manifest = normalize_manifest(_payload(), scenario_id=SCENARIO_ID, revision=1)
    profiles = materialize_boss_profiles(manifest)
    exact_text = manifest["assets"][0]["content"]

    config = build_boss_simulation_config(manifest, profiles)

    assert config["scenario_id"] == SCENARIO_ID
    assert config["manifest_sha256"] == manifest["provenance"]["manifest_sha256"]
    assert config["asset_id"] == manifest["assets"][0]["asset_id"]
    assert config["timezone"] == BOSS_TIMEZONE
    assert config["time_config"]["timezone"] == BOSS_TIMEZONE
    assert config["seed"] == 1234
    assert config["brand_agent_id"] == 0
    assert config["audience_agent_ids"] == [1, 2, 3, 4]
    assert config["source_kind"] == "boss_scenario"
    assert config["llm_used"] is False
    assert config["zep_used"] is False
    post = config["event_config"]["initial_posts"][0]
    assert post["poster_agent_id"] == 0
    assert post["content"] == exact_text
    assert "rewrite" not in post


def test_user_supplied_derived_text_is_accepted_for_media(client):
    media = {
        "kind": "video",
        "type": "video",
        "title": "Launch clip",
        "language": "English",
        "derived_artifacts": [
            {
                "artifact_id": "artifact_transcript",
                "kind": "transcript",
                "processor": "user-provided-v1",
                "text": "Exact user-supplied transcript.",
            }
        ],
    }
    created = client.post("/api/boss/scenarios", json=_payload(asset=media))
    assert created.status_code == 200
    scenario_id = created.json["data"]["scenario_id"]

    response = client.post(f"/api/boss/scenarios/{scenario_id}/simulation/prepare-preview", json={})

    assert response.status_code == 200
    data = response.json["data"]
    assert data["content_source_kind"] == "derived_text"
    assert data["artifact_id"] == "artifact_transcript"
    assert data["config"]["event_config"]["initial_posts"][0]["content"] == (
        "Exact user-supplied transcript."
    )


def test_preview_prepare_and_readback_are_deterministic_and_persist_relative_artifacts(client, tmp_path):
    created = client.post("/api/boss/scenarios", json=_payload())
    assert created.status_code == 200
    scenario_id = created.json["data"]["scenario_id"]

    preview = client.post(f"/api/boss/scenarios/{scenario_id}/simulation/prepare-preview", json={})
    assert preview.status_code == 200
    assert client.get(f"/api/boss/scenarios/{scenario_id}/simulation").status_code == 404

    prepared = client.post(f"/api/boss/scenarios/{scenario_id}/simulation/prepare", json={})
    repeated = client.post(f"/api/boss/scenarios/{scenario_id}/simulation/prepare", json={})
    assert prepared.status_code == 200
    assert repeated.status_code == 200
    assert prepared.json["data"]["status"] == "ready"
    assert prepared.json["data"]["simulation_id"] == preview.json["data"]["simulation_id"]
    assert repeated.json["data"]["simulation_id"] == prepared.json["data"]["simulation_id"]
    assert prepared.json["data"]["config"] == preview.json["data"]["config"]

    readback = client.get(f"/api/boss/scenarios/{scenario_id}/simulation")
    assert readback.status_code == 200
    data = readback.json["data"]
    assert data["status"] == "ready"
    assert data["config"] == prepared.json["data"]["config"]
    assert data["artifact_files"] == {
        "config": "simulation/simulation_config.json",
        "reddit_profiles": "simulation/reddit_profiles.json",
        "twitter_profiles": "simulation/twitter_profiles.csv",
    }
    scenario_dir = tmp_path / scenario_id
    assert (scenario_dir / "simulation.json").is_file()
    assert (scenario_dir / "simulation/reddit_profiles.json").is_file()
    assert (scenario_dir / "simulation/twitter_profiles.csv").is_file()
    assert (scenario_dir / "simulation/simulation_config.json").is_file()

    persisted = json.dumps(data, ensure_ascii=False)
    assert str(tmp_path) not in persisted
    assert "api_key" not in persisted
    assert "SECRET" not in persisted


def test_missing_media_derived_text_is_rejected_without_paths_or_tracebacks(client, tmp_path):
    created = client.post(
        "/api/boss/scenarios",
        json=_payload(
            asset={
                "kind": "audio",
                "type": "audio",
                "title": "Voice note",
                "language": "English",
            }
        ),
    )
    assert created.status_code == 200
    scenario_id = created.json["data"]["scenario_id"]

    response = client.post(f"/api/boss/scenarios/{scenario_id}/simulation/prepare", json={})

    assert response.status_code == 400
    assert response.json["fields"]["asset.content"].startswith("usable text")
    response_text = json.dumps(response.json, ensure_ascii=False)
    assert str(tmp_path) not in response_text
    assert "traceback" not in response_text.casefold()
    assert client.get(f"/api/boss/scenarios/{scenario_id}/simulation").status_code == 404
