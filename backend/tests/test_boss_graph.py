import json
import time

import pytest

from app import create_app
from app.api import boss as boss_api
from app.config import Config
from app.models.boss_scenario import manifest_sha256
from app.services.boss_graph_adapter import (
    BossGraphPacketBoundsError,
    build_boss_graph,
    build_boss_graph_metadata,
    chunk_scenario_packet,
    fixed_boss_ontology,
    render_scenario_packet,
)
from app.services.boss_scenarios import BossScenarioStore
from app.services.graph_builder import BatchSubmission


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
            "content": "Exact copy: Learn at your pace.\nDo not rewrite this line.",
            "language": "English",
            "storage_key": "assets/asset.txt",
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


def _manifest(tmp_path):
    manifest = BossScenarioStore(tmp_path).create(_payload())
    return manifest


def test_fixed_ontology_is_deterministic_and_has_valid_edge_endpoints():
    first = fixed_boss_ontology()
    second = fixed_boss_ontology()

    assert first == second
    assert [item["name"] for item in first["entity_types"]] == [
        "BrandAccount",
        "AudiencePersona",
        "Asset",
        "AudienceContext",
        "Claim",
    ]
    entity_names = {item["name"] for item in first["entity_types"]}
    assert entity_names == {
        endpoint
        for edge in first["edge_types"]
        for target in edge["source_targets"]
        for endpoint in (target["source"], target["target"])
    }
    first["entity_types"][0]["name"] = "Changed"
    assert fixed_boss_ontology()["entity_types"][0]["name"] == "BrandAccount"


def test_fixed_ontology_is_accepted_by_existing_graph_builder_set_ontology():
    captured = {}

    class GraphApi:
        def set_ontology(self, **kwargs):
            captured.update(kwargs)

    class Client:
        graph = GraphApi()

    from app.services.graph_builder import GraphBuilderService

    builder = object.__new__(GraphBuilderService)
    builder.client = Client()
    builder.set_ontology("boss_graph_test", fixed_boss_ontology())

    assert captured["graph_ids"] == ["boss_graph_test"]
    assert set(captured["entities"]) == {
        "BrandAccount",
        "AudiencePersona",
        "Asset",
        "AudienceContext",
        "Claim",
    }
    assert set(captured["edges"]) == {
        "PUBLISHES",
        "TARGETS_AUDIENCE",
        "HAS_PERSONA_CONTEXT",
        "SUPPORTS_CLAIM",
        "MAKES_CLAIM",
    }


def test_packet_contains_context_exact_asset_and_bounded_chunks_without_paths(tmp_path):
    manifest = _manifest(tmp_path)
    manifest["assets"][0]["derived_artifacts"] = [
        {
            "artifact_id": "ocr_1",
            "processor": "test-ocr",
            "text": "Derived exact evidence",
        }
    ]
    manifest["provenance"]["manifest_sha256"] = manifest_sha256(manifest)

    packet = render_scenario_packet(manifest)

    assert "scenario_id:" in packet
    assert "revision: 1" in packet
    assert f"manifest_sha256: {manifest['provenance']['manifest_sha256']}" in packet
    assert "name: Nayi Disha" in packet
    assert "region: Maharashtra" in packet
    assert manifest["assets"][0]["content"] in packet
    assert "Derived exact evidence" in packet
    assert "storage_key" not in packet
    assert "/tmp" not in packet
    assert "test-ocr" in packet

    chunks = chunk_scenario_packet(packet, chunk_size=160, overlap=20, batch_size=4)
    assert chunks
    assert all(len(chunk) <= 10_000 for chunk in chunks)
    with pytest.raises(BossGraphPacketBoundsError):
        render_scenario_packet(manifest, max_chars=20)


def test_adapter_calls_fake_builder_in_order_and_returns_boss_metadata(tmp_path):
    manifest = _manifest(tmp_path)
    events = []

    class FakeBuilder:
        def create_graph(self, name, *, graph_id_callback=None):
            events.append(("create_graph", name))
            if graph_id_callback:
                graph_id_callback("boss_graph_test")
            return "boss_graph_test"

        def set_ontology(self, graph_id, ontology):
            events.append(("set_ontology", graph_id, ontology))

        def add_text_batches(self, graph_id, chunks, batch_size=350, batch_created_callback=None):
            events.append(("add_text_batches", graph_id, chunks, batch_size))
            if batch_created_callback:
                batch_created_callback("batch_test", "operation_test")
            return BatchSubmission("batch_test", "operation_test", [], len(chunks))

    result = build_boss_graph(
        manifest,
        FakeBuilder(),
        chunk_size=180,
        overlap=20,
        batch_size=4,
    )

    assert [event[0] for event in events] == [
        "create_graph",
        "set_ontology",
        "add_text_batches",
    ]
    assert events[1][2] == fixed_boss_ontology()
    assert events[2][3] == 4
    assert result["source_kind"] == "boss_scenario"
    assert result["scenario_id"] == manifest["scenario_id"]
    assert result["revision"] == manifest["revision"]
    assert result["manifest_sha256"] == manifest["provenance"]["manifest_sha256"]
    assert result["asset_ids"] == [manifest["assets"][0]["asset_id"]]
    assert result["graph_id"] == "boss_graph_test"
    assert result["batch_id"] == "batch_test"
    assert result["operation_id"] == "operation_test"


def test_prepare_endpoint_returns_packet_ontology_and_metadata_without_builder(client):
    response = client.post("/api/boss/scenarios", json=_payload())
    scenario_id = response.json["data"]["scenario_id"]

    def unexpected_builder(*args, **kwargs):
        raise AssertionError("prepare must not construct a graph builder")

    original = boss_api.GraphBuilderService
    boss_api.GraphBuilderService = unexpected_builder
    try:
        prepared = client.post(f"/api/boss/scenarios/{scenario_id}/graph/prepare", json={})
    finally:
        boss_api.GraphBuilderService = original

    assert prepared.status_code == 200
    data = prepared.json["data"]
    assert data["source_kind"] == "boss_scenario"
    assert data["scenario_id"] == scenario_id
    assert data["ontology"] == fixed_boss_ontology()
    assert "Exact copy" in data["packet"]
    assert data["chunk_count"] >= 1


def test_build_without_zep_key_returns_safe_503_and_does_not_create_record(client, monkeypatch):
    created = client.post("/api/boss/scenarios", json=_payload()).json["data"]
    scenario_id = created["scenario_id"]
    monkeypatch.setattr(Config, "ZEP_API_KEY", None)

    response = client.post(f"/api/boss/scenarios/{scenario_id}/graph/build", json={})

    assert response.status_code == 503
    assert response.json["code"] == "BOSS_GRAPH_CREDENTIAL_MISSING"
    assert "ZEP_API_KEY" in response.json["error"]
    assert client.get(f"/api/boss/scenarios/{scenario_id}/graph").status_code == 404


def test_build_rejects_stale_client_manifest_hash_before_any_graph_call(client, monkeypatch):
    created = client.post("/api/boss/scenarios", json=_payload()).json["data"]
    scenario_id = created["scenario_id"]
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")

    class UnexpectedBuilder:
        def __init__(self, *args, **kwargs):
            raise AssertionError("stale manifests must be rejected before builder construction")

    monkeypatch.setattr(boss_api, "GraphBuilderService", UnexpectedBuilder)
    response = client.post(
        f"/api/boss/scenarios/{scenario_id}/graph/build",
        json={"manifest_sha256": "0" * 64},
    )

    assert response.status_code == 409
    assert response.json["fields"]["manifest_sha256"]
    assert client.get(f"/api/boss/scenarios/{scenario_id}/graph").status_code == 404


def test_build_persists_and_reads_graph_metadata_without_mutating_manifest(client, monkeypatch, tmp_path):
    created = client.post("/api/boss/scenarios", json=_payload()).json["data"]
    scenario_id = created["scenario_id"]
    before = BossScenarioStore(tmp_path).get(scenario_id)
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")

    class FakeBuilder:
        def __init__(self, api_key=None):
            assert api_key == "test-zep-key"

        def create_graph(self, name, *, graph_id_callback=None):
            if graph_id_callback:
                graph_id_callback("boss_graph_persisted")
            return "boss_graph_persisted"

        def set_ontology(self, graph_id, ontology):
            assert graph_id == "boss_graph_persisted"
            assert ontology == fixed_boss_ontology()

        def add_text_batches(self, graph_id, chunks, batch_size=350, batch_created_callback=None):
            if batch_created_callback:
                batch_created_callback("batch_persisted", "operation_persisted")
            return BatchSubmission("batch_persisted", "operation_persisted", [], len(chunks))

    monkeypatch.setattr(boss_api, "GraphBuilderService", FakeBuilder)
    response = client.post(
        f"/api/boss/scenarios/{scenario_id}/graph/build",
        json={"manifest_sha256": created["manifest_sha256"]},
    )
    assert response.status_code == 202
    task_id = response.json["data"]["task_id"]

    record = None
    for _ in range(100):
        read_response = client.get(f"/api/boss/scenarios/{scenario_id}/graph")
        if read_response.status_code == 200 and read_response.json["data"]["status"] == "completed":
            record = read_response.json["data"]
            break
        time.sleep(0.01)

    assert record is not None
    assert record["task_id"] == task_id
    assert record["source_kind"] == "boss_scenario"
    assert record["manifest_sha256"] == created["manifest_sha256"]
    assert record["graph_id"] == "boss_graph_persisted"
    assert record["batch_id"] == "batch_persisted"
    assert record["operation_id"] == "operation_persisted"
    assert record["asset_ids"] == [created["manifest"]["assets"][0]["asset_id"]]
    assert before == BossScenarioStore(tmp_path).get(scenario_id)
    persisted = json.dumps(record, ensure_ascii=False)
    assert str(tmp_path) not in persisted
    assert "test-zep-key" not in persisted
