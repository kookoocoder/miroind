"""BOSS asset, scenario, manifest, and graph orchestration API."""

from __future__ import annotations

import threading

from flask import jsonify, request, send_file

from . import boss_bp
from ..config import Config
from ..models.boss_asset import BossAssetNotFound, BossAssetValidationError
from ..models.boss_scenario import BossScenarioValidationError
from ..models.task import TaskManager, TaskStatus
from ..services.boss_graph_adapter import (
    BossGraphPacketBoundsError,
    build_boss_graph,
    build_boss_graph_metadata,
    chunk_scenario_packet,
    render_scenario_packet,
    fixed_boss_ontology,
)
from ..services.boss_scenarios import (
    BossScenarioAlreadyExists,
    BossScenarioNotFound,
    BossScenarioStore,
)
from ..services.boss_assets import BossAssetStore, BossAssetTooLarge
from ..services.graph_builder import GraphBuilderService


def _asset_validation_response(error: BossAssetValidationError) -> tuple:
    return jsonify(
        {
            "success": False,
            "error": "Invalid BOSS asset request",
            "fields": error.fields,
        }
    ), 400


def _asset_not_found_response() -> tuple:
    return jsonify({"success": False, "error": "BOSS asset not found"}), 404


@boss_bp.route("/assets", methods=["POST"])
def upload_asset():
    """Store one validated media file without making a model call."""

    uploaded = request.files.get("file")
    if uploaded is None:
        return _asset_validation_response(BossAssetValidationError({"file": "multipart field is required"}))
    try:
        record = BossAssetStore().upload(uploaded, scenario_id=request.form.get("scenario_id"))
    except BossAssetTooLarge as error:
        response = _asset_validation_response(error)
        return response[0], 413
    except BossAssetValidationError as error:
        return _asset_validation_response(error)
    except Exception:
        return jsonify(
            {
                "success": False,
                "error": "BOSS asset could not be stored",
                "fields": {},
            }
        ), 500
    return jsonify({"success": True, "data": record}), 201


@boss_bp.route("/assets/<asset_id>", methods=["GET"])
def get_asset(asset_id: str):
    record = BossAssetStore().get(asset_id)
    if record is None:
        return _asset_not_found_response()
    return jsonify({"success": True, "data": record})


@boss_bp.route("/assets/<asset_id>/status", methods=["GET"])
def get_asset_status(asset_id: str):
    record = BossAssetStore().get(asset_id)
    if record is None:
        return _asset_not_found_response()
    return jsonify({"success": True, "data": record})


@boss_bp.route("/assets/<asset_id>/download", methods=["GET"])
def download_asset(asset_id: str):
    try:
        record, path = BossAssetStore().download_path(asset_id)
    except BossAssetNotFound:
        return _asset_not_found_response()
    return send_file(
        path,
        mimetype=record["mime_type"],
        as_attachment=True,
        download_name=record["original_filename"],
    )


@boss_bp.route("/assets/<asset_id>", methods=["DELETE"])
def delete_asset(asset_id: str):
    if not BossAssetStore().delete(asset_id):
        return _asset_not_found_response()
    return jsonify({"success": True, "data": {"asset_id": asset_id, "deleted": True}})


@boss_bp.route("/assets/<asset_id>/artifacts", methods=["POST"])
def create_asset_artifact(asset_id: str):
    payload = request.get_json(silent=True)
    if payload is None:
        return _asset_validation_response(BossAssetValidationError({"payload": "must be a JSON object"}))
    try:
        artifact = BossAssetStore().add_artifact(asset_id, payload)
    except BossAssetNotFound:
        return _asset_not_found_response()
    except BossAssetValidationError as error:
        return _asset_validation_response(error)
    except Exception:
        return jsonify(
            {
                "success": False,
                "error": "BOSS asset artifact could not be stored",
                "fields": {},
            }
        ), 500
    return jsonify({"success": True, "data": artifact}), 201


@boss_bp.route("/assets/<asset_id>/artifacts", methods=["GET"])
def list_asset_artifacts(asset_id: str):
    try:
        artifacts = BossAssetStore().list_artifacts(asset_id)
    except BossAssetNotFound:
        return _asset_not_found_response()
    return jsonify({"success": True, "data": artifacts})


@boss_bp.route("/assets/<asset_id>/artifacts/<artifact_id>", methods=["GET"])
def get_asset_artifact(asset_id: str, artifact_id: str):
    try:
        artifact, text = BossAssetStore().get_artifact(asset_id, artifact_id)
    except BossAssetNotFound:
        return jsonify({"success": False, "error": "BOSS artifact not found"}), 404
    return jsonify({"success": True, "data": {"artifact": artifact, "text": text}})


def _record(manifest: dict, *, status: str | None = None) -> dict:
    revision = manifest.get("revision", 1)
    return {
        "scenario_id": manifest["scenario_id"],
        "revision": revision,
        "status": status or ("created" if revision == 1 else "updated"),
        "manifest_sha256": manifest["provenance"]["manifest_sha256"],
        "manifest": manifest,
    }


def _invalid_json_response() -> tuple:
    return jsonify(
        {
            "success": False,
            "error": "Invalid BOSS scenario payload",
            "fields": {"payload": "must be a JSON object"},
        }
    ), 400


def _validation_response(error: BossScenarioValidationError) -> tuple:
    return jsonify(
        {
            "success": False,
            "error": "Invalid BOSS scenario",
            "fields": error.fields,
        }
    ), 400


@boss_bp.route("/scenarios", methods=["POST"])
def create_scenario():
    payload = request.get_json(silent=True)
    if payload is None:
        return _invalid_json_response()
    try:
        manifest = BossScenarioStore().create(payload)
    except BossScenarioValidationError as error:
        return _validation_response(error)
    except BossScenarioAlreadyExists:
        return jsonify(
            {
                "success": False,
                "error": "BOSS scenario already exists",
                "fields": {"scenario_id": "already exists"},
            }
        ), 409
    except Exception:
        return jsonify(
            {
                "success": False,
                "error": "BOSS scenario could not be persisted",
                "fields": {},
            }
        ), 500
    return jsonify({"success": True, "data": _record(manifest, status="created")})


@boss_bp.route("/scenarios/<scenario_id>", methods=["GET"])
def get_scenario(scenario_id: str):
    manifest = BossScenarioStore().get(scenario_id)
    if manifest is None:
        return jsonify({"success": False, "error": "BOSS scenario not found"}), 404
    return jsonify({"success": True, "data": _record(manifest)})


@boss_bp.route("/scenarios", methods=["GET"])
def list_scenarios():
    raw_limit = request.args.get("limit", "20")
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return jsonify(
            {
                "success": False,
                "error": "Invalid BOSS scenario list request",
                "fields": {"limit": "must be an integer between 1 and 100"},
            }
        ), 400
    if not 1 <= limit <= 100:
        return jsonify(
            {
                "success": False,
                "error": "Invalid BOSS scenario list request",
                "fields": {"limit": "must be an integer between 1 and 100"},
            }
        ), 400
    try:
        manifests = BossScenarioStore().list(limit=limit)
    except Exception:
        return jsonify(
            {
                "success": False,
                "error": "BOSS scenarios could not be listed",
                "fields": {},
            }
        ), 500
    return jsonify({"success": True, "data": [_record(item) for item in manifests]})


@boss_bp.route("/scenarios/<scenario_id>/revisions", methods=["POST"])
def create_revision(scenario_id: str):
    store = BossScenarioStore()
    if store.get(scenario_id) is None:
        return jsonify({"success": False, "error": "BOSS scenario not found"}), 404
    payload = request.get_json(silent=True)
    if payload is None:
        return _invalid_json_response()
    try:
        manifest = store.create_revision(scenario_id, payload)
    except BossScenarioValidationError as error:
        return _validation_response(error)
    except BossScenarioNotFound:
        return jsonify({"success": False, "error": "BOSS scenario not found"}), 404
    except Exception:
        return jsonify(
            {
                "success": False,
                "error": "BOSS scenario revision could not be persisted",
                "fields": {},
            }
        ), 500
    return jsonify({"success": True, "data": _record(manifest, status="updated")})


def _request_object() -> tuple[dict, tuple | None]:
    payload = request.get_json(silent=True)
    if payload is None:
        return {}, None
    if not isinstance(payload, dict):
        return {}, (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid BOSS graph request",
                    "fields": {"payload": "must be a JSON object"},
                }
            ),
            400,
        )
    return payload, None


def _chunk_options(payload: dict) -> tuple[int | None, int | None, int] | tuple[None, tuple]:
    chunk_size = payload.get("chunk_size")
    overlap = payload.get("chunk_overlap", payload.get("overlap"))
    batch_size = payload.get("batch_size", 350)
    for name, value in (("chunk_size", chunk_size), ("chunk_overlap", overlap), ("batch_size", batch_size)):
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            return None, (
                jsonify({"success": False, "error": f"{name} must be an integer"}),
                400,
            )
    if chunk_size is not None and chunk_size <= 0:
        return None, (jsonify({"success": False, "error": "chunk_size must be positive"}), 400)
    if overlap is not None and overlap < 0:
        return None, (jsonify({"success": False, "error": "chunk_overlap must not be negative"}), 400)
    if batch_size is not None and not 1 <= batch_size <= 350:
        return None, (jsonify({"success": False, "error": "batch_size must be between 1 and 350"}), 400)
    if chunk_size is not None and overlap is not None and overlap >= chunk_size:
        return None, (
            jsonify({"success": False, "error": "chunk_overlap must satisfy 0 <= chunk_overlap < chunk_size"}),
            400,
        )
    return (chunk_size, overlap, batch_size), None


def _check_manifest_hash(payload: dict, manifest: dict) -> tuple | None:
    supplied = payload.get("manifest_sha256")
    if supplied is None:
        return None
    expected = manifest["provenance"]["manifest_sha256"]
    if not isinstance(supplied, str) or supplied != expected:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "BOSS scenario manifest is stale; refresh before building",
                    "fields": {"manifest_sha256": "does not match the persisted manifest"},
                }
            ),
            409,
        )
    return None


def _safe_graph_error(error: Exception) -> str:
    """Return an error suitable for task and graph-record persistence."""

    # Exception text from an SDK can contain request bodies, credentials, or
    # local paths.  Keep only a stable type marker in the persisted boundary.
    return f"BOSS graph build failed ({type(error).__name__})"


def _graph_record_base(manifest: dict, task_id: str, *, status: str, chunk_count: int) -> dict:
    return {
        **build_boss_graph_metadata(manifest),
        "task_id": task_id,
        "status": status,
        "graph_id": None,
        "batch_id": None,
        "operation_id": None,
        "chunk_count": chunk_count,
    }


@boss_bp.route("/scenarios/<scenario_id>/graph/prepare", methods=["POST"])
def prepare_scenario_graph(scenario_id: str):
    """Prepare the deterministic BOSS graph projection without contacting Zep."""

    payload, error_response = _request_object()
    if error_response:
        return error_response
    store = BossScenarioStore()
    manifest = store.get(scenario_id)
    if manifest is None:
        return jsonify({"success": False, "error": "BOSS scenario not found"}), 404
    options, error_response = _chunk_options(payload)
    if error_response:
        return error_response
    chunk_size, overlap, batch_size = options
    try:
        packet = render_scenario_packet(manifest)
        chunks = chunk_scenario_packet(
            packet,
            chunk_size=chunk_size,
            overlap=overlap,
            batch_size=batch_size,
        )
        metadata = build_boss_graph_metadata(manifest)
    except (ValueError, BossGraphPacketBoundsError) as error:
        return jsonify({"success": False, "error": str(error)}), 400
    data = {
        **metadata,
        "metadata": metadata,
        "packet": packet,
        "packet_preview": packet,
        "ontology": fixed_boss_ontology(),
        "chunk_count": len(chunks),
        "chunk_size": chunk_size or Config.DEFAULT_CHUNK_SIZE,
        "chunk_overlap": overlap if overlap is not None else Config.DEFAULT_CHUNK_OVERLAP,
    }
    return jsonify({"success": True, "data": data})


@boss_bp.route("/scenarios/<scenario_id>/graph/build", methods=["POST"])
def build_scenario_graph(scenario_id: str):
    """Start an isolated BOSS graph build for the current manifest revision."""

    payload, error_response = _request_object()
    if error_response:
        return error_response
    store = BossScenarioStore()
    manifest = store.get(scenario_id)
    if manifest is None:
        return jsonify({"success": False, "error": "BOSS scenario not found"}), 404
    stale_response = _check_manifest_hash(payload, manifest)
    if stale_response:
        return stale_response
    if not Config.ZEP_API_KEY:
        return jsonify(
            {
                "success": False,
                "error": "ZEP_API_KEY is required to build a BOSS graph",
                "code": "BOSS_GRAPH_CREDENTIAL_MISSING",
            }
        ), 503
    options, error_response = _chunk_options(payload)
    if error_response:
        return error_response
    chunk_size, overlap, batch_size = options
    try:
        packet = render_scenario_packet(manifest)
        chunks = chunk_scenario_packet(
            packet,
            chunk_size=chunk_size,
            overlap=overlap,
            batch_size=batch_size,
        )
        metadata = build_boss_graph_metadata(manifest)
    except (ValueError, BossGraphPacketBoundsError) as error:
        return jsonify({"success": False, "error": str(error)}), 400

    task_manager = TaskManager()
    task_id = task_manager.create_task(
        "boss_graph_build",
        metadata={
            "source_kind": "boss_scenario",
            "scenario_id": metadata["scenario_id"],
            "revision": metadata["revision"],
            "manifest_sha256": metadata["manifest_sha256"],
        },
    )
    record = _graph_record_base(manifest, task_id, status="pending", chunk_count=len(chunks))
    try:
        store.save_graph_record(scenario_id, record)
    except Exception:
        task_manager.fail_task(task_id, "BOSS graph record could not be persisted")
        return jsonify({"success": False, "error": "BOSS graph record could not be persisted"}), 500

    def build_task() -> None:
        task_manager.update_task(task_id, status=TaskStatus.PROCESSING, progress=5, message="BOSS graph build started")
        record["status"] = "building"
        try:
            store.save_graph_record(scenario_id, record)

            def remember_graph(graph_id: str) -> None:
                record["graph_id"] = graph_id
                store.save_graph_record(scenario_id, record)

            def remember_batch(batch_id: str | None, operation_id: str) -> None:
                record["batch_id"] = batch_id
                record["operation_id"] = operation_id
                store.save_graph_record(scenario_id, record)

            builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
            result = build_boss_graph(
                manifest,
                builder,
                chunk_size=chunk_size,
                overlap=overlap,
                batch_size=batch_size,
                graph_id_callback=remember_graph,
                batch_created_callback=remember_batch,
            )
            record.update(
                {
                    "graph_id": result.get("graph_id"),
                    "batch_id": result.get("batch_id"),
                    "operation_id": result.get("operation_id"),
                    "status": "completed",
                }
            )
            store.save_graph_record(scenario_id, record)
            task_manager.complete_task(
                task_id,
                {
                    "source_kind": "boss_scenario",
                    "scenario_id": scenario_id,
                    "revision": metadata["revision"],
                    "manifest_sha256": metadata["manifest_sha256"],
                    "graph_id": result.get("graph_id"),
                    "batch_id": result.get("batch_id"),
                    "operation_id": result.get("operation_id"),
                    "chunk_count": result.get("chunk_count"),
                },
            )
        except Exception as error:
            safe_error = _safe_graph_error(error)
            record["status"] = "failed"
            record["error"] = safe_error
            try:
                store.save_graph_record(scenario_id, record)
            finally:
                task_manager.fail_task(task_id, safe_error)

    threading.Thread(target=build_task, daemon=True).start()
    return jsonify(
        {
            "success": True,
            "data": {
                "task_id": task_id,
                "status": "pending",
                "scenario_id": scenario_id,
                "revision": metadata["revision"],
                "manifest_sha256": metadata["manifest_sha256"],
            },
        }
    ), 202


@boss_bp.route("/scenarios/<scenario_id>/graph", methods=["GET"])
def get_scenario_graph(scenario_id: str):
    store = BossScenarioStore()
    if store.get(scenario_id) is None:
        return jsonify({"success": False, "error": "BOSS scenario not found"}), 404
    record = store.get_graph_record(scenario_id)
    if record is None:
        return jsonify({"success": False, "error": "BOSS graph record not found"}), 404
    return jsonify({"success": True, "data": record})


__all__ = [
    "build_scenario_graph",
    "create_revision",
    "create_scenario",
    "get_scenario",
    "get_scenario_graph",
    "list_scenarios",
    "prepare_scenario_graph",
]
