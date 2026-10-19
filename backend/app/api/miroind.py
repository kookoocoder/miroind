"""Credential-free MiroInd text stress-test API."""

from flask import jsonify, request

from . import miroind_bp
from ..services.miroind import MiroIndService, MiroIndValidationError


@miroind_bp.route("/runs", methods=["POST"])
def create_run():
    """Run the deterministic offline stress test and persist its result."""

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify(
            {
                "success": False,
                "error": "Invalid JSON payload",
                "fields": {"payload": "must be a JSON object"},
            }
        ), 400

    try:
        record = MiroIndService().run(payload)
    except MiroIndValidationError as error:
        return jsonify(
            {
                "success": False,
                "error": "Invalid MiroInd payload",
                "fields": error.fields,
            }
        ), 400
    except Exception:
        # Keep implementation details, paths, and tracebacks out of this
        # credential-free public endpoint.  The existing app logger can still
        # capture an exception through deployment-level error handling.
        return jsonify(
            {
                "success": False,
                "error": "MiroInd run could not be completed",
                "fields": {},
            }
        ), 500

    return jsonify({"success": True, "data": record})


@miroind_bp.route("/runs/<run_id>", methods=["GET"])
def get_run(run_id: str):
    """Read a previously persisted MiroInd result."""

    record = MiroIndService().get_run(run_id)
    if record is None:
        return jsonify(
            {"success": False, "error": "MiroInd run not found"}
        ), 404
    return jsonify({"success": True, "data": record})


__all__ = ["create_run", "get_run"]
