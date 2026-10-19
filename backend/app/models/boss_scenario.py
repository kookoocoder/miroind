"""Canonical BOSS scenario manifest validation and normalization.

The normalizer is deliberately independent from Flask and persistence. It
accepts both the original MiroInd request shape and the versioned BOSS shape,
then emits one JSON-safe manifest. Unknown fields are rejected so credentials,
filesystem paths, and other request metadata cannot accidentally become part
of a persisted scenario snapshot.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from collections.abc import Mapping
from typing import Any


SCHEMA_VERSION = "boss.scenario.v1"
SCENARIO_ID_PATTERN = re.compile(r"^scenario_[a-f0-9]{24}$")
REFERENCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


MAX_LENGTHS = {
    "brand.name": 120,
    "brand.positioning": 500,
    "brand.tone": 160,
    "brand.audience_relationship": 300,
    "brand.red_lines[]": 160,
    "brand.preferred_vocabulary[]": 100,
    "brand.claims_must_not_invent[]": 240,
    "audiences[].id": 64,
    "audiences[].region": 120,
    "audiences[].local_context": 500,
    "audiences[].language_signal": 80,
    "audiences[].age_band": 80,
    "audiences[].occupation": 120,
    "audiences[].city_tier": 80,
    "audiences[].income_band": 80,
    "audiences[].country": 2,
    "audiences[].exclusions[]": 160,
    "audiences[].persona_pack_id": 80,
    "assets[].asset_id": 64,
    "assets[].title": 200,
    "assets[].content": 20_000,
    "assets[].language": 80,
    "assets[].storage_key": 500,
    "assets[].mime_type": 120,
    "assets[].derived_artifacts[].text": 20_000,
    "assets[].derived_artifacts[].processor": 120,
    "run_config[].interaction_formats[]": 80,
    "run_config[].timezone": 80,
    "provenance.input_source": 120,
}


SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


class BossScenarioValidationError(ValueError):
    """Safe, structured validation errors for BOSS scenario requests."""

    def __init__(self, fields: dict[str, str]):
        self.fields = fields
        super().__init__("BOSS scenario validation failed")


ValidationError = BossScenarioValidationError


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _is_absolute_path(value: str) -> bool:
    """Recognize POSIX, Windows, and home-relative filesystem paths."""

    stripped = value.strip()
    if not stripped:
        return False
    if os.path.isabs(stripped) or stripped.startswith(("~/", "\\\\")):
        return True
    if re.match(r"^[A-Za-z]:[\\/]", stripped):
        return True
    return bool(
        re.search(
            r"(?<!:)/(?:Users|home|tmp|var|private|etc|opt|root|srv|mnt|Volumes)/",
            stripped,
            flags=re.IGNORECASE,
        )
    )


def _walk_sensitive_keys(value: Any, path: str, fields: dict[str, str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            folded = key_text.casefold().replace("-", "_")
            child_path = f"{path}.{key_text}" if path else key_text
            if any(part in folded for part in SENSITIVE_KEY_PARTS):
                fields[child_path] = "must not contain credentials or secrets"
            _walk_sensitive_keys(child, child_path, fields)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_sensitive_keys(child, f"{path}[{index}]", fields)


def _reject_unknown(
    container: Mapping[str, Any],
    allowed: set[str],
    path: str,
    fields: dict[str, str],
) -> None:
    for key in container:
        if key not in allowed:
            fields[f"{path}.{key}" if path else str(key)] = "is not supported"


def _required_string(
    container: Mapping[str, Any],
    key: str,
    path: str,
    fields: dict[str, str],
    *,
    max_length: int,
) -> str | None:
    if key not in container:
        fields[path] = "is required"
        return None
    value = container[key]
    if not isinstance(value, str):
        fields[path] = "must be a string"
        return None
    value = value.strip()
    if not value:
        fields[path] = "must not be empty"
    elif len(value) > max_length:
        fields[path] = f"must be at most {max_length} characters"
    elif _is_absolute_path(value):
        fields[path] = "must not be an absolute path"
    else:
        return value
    return None


def _optional_string(
    container: Mapping[str, Any],
    key: str,
    path: str,
    fields: dict[str, str],
    *,
    max_length: int,
    default: str | None = None,
    allow_null: bool = True,
) -> str | None:
    if key not in container or container[key] is None:
        if key in container and not allow_null:
            fields[path] = "must be a string"
        return default
    value = container[key]
    if not isinstance(value, str):
        fields[path] = "must be a string"
        return default
    value = value.strip()
    if not value:
        fields[path] = "must not be empty"
    elif len(value) > max_length:
        fields[path] = f"must be at most {max_length} characters"
    elif _is_absolute_path(value):
        fields[path] = "must not be an absolute path"
    else:
        return value
    return default


def _string_list(
    container: Mapping[str, Any],
    key: str,
    path: str,
    fields: dict[str, str],
    *,
    max_items: int,
    item_max_length: int,
    required: bool,
) -> list[str] | None:
    if key not in container:
        if required:
            fields[path] = "is required"
        return [] if not required else None
    value = container[key]
    if not isinstance(value, list):
        fields[path] = "must be an array of strings"
        return None
    if len(value) > max_items:
        fields[path] = f"must contain at most {max_items} items"
    normalized: list[str] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, str):
            fields[item_path] = "must be a string"
            continue
        item = item.strip()
        if not item:
            fields[item_path] = "must not be empty"
        elif len(item) > item_max_length:
            fields[item_path] = f"must be at most {item_max_length} characters"
        elif _is_absolute_path(item):
            fields[item_path] = "must not be an absolute path"
        else:
            normalized.append(item)
    return normalized


def _safe_reference_id(
    value: Any,
    path: str,
    prefix: str,
    fields: dict[str, str],
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        fields[path] = "must be a safe identifier"
        return None
    value = value.strip()
    if (
        not value
        or len(value) > 64
        or not value.startswith(f"{prefix}_")
        or REFERENCE_ID_PATTERN.fullmatch(value) is None
    ):
        fields[path] = f"must match {prefix}_<safe-id>"
        return None
    return value


def _generated_reference_id(prefix: str, value: Any, index: int) -> str:
    seed = json.dumps(
        {"index": index, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(seed).hexdigest()[:24]}"


def _normalize_brand(brand: Any, fields: dict[str, str]) -> dict[str, Any]:
    path = "brand"
    if not isinstance(brand, Mapping):
        fields[path] = "is required and must be a JSON object"
        return {}
    _reject_unknown(
        brand,
        {
            "name",
            "positioning",
            "tone",
            "audience_relationship",
            "red_lines",
            "preferred_vocabulary",
            "claims_must_not_invent",
        },
        path,
        fields,
    )
    result: dict[str, Any] = {}
    for key in ("name", "positioning", "tone", "audience_relationship"):
        value = _required_string(
            brand,
            key,
            f"{path}.{key}",
            fields,
            max_length=MAX_LENGTHS[f"{path}.{key}"],
        )
        if value is not None:
            result[key] = value
    for key, max_items in (("red_lines", 20), ("preferred_vocabulary", 30)):
        value = _string_list(
            brand,
            key,
            f"{path}.{key}",
            fields,
            max_items=max_items,
            item_max_length=MAX_LENGTHS[f"{path}.{key}[]"],
            required=True,
        )
        if value is not None:
            result[key] = value
    claims = _string_list(
        brand,
        "claims_must_not_invent",
        "brand.claims_must_not_invent",
        fields,
        max_items=30,
        item_max_length=MAX_LENGTHS["brand.claims_must_not_invent[]"],
        required=False,
    )
    result["claims_must_not_invent"] = claims or []
    return result


def _normalize_audience(value: Any, index: int, fields: dict[str, str]) -> dict[str, Any]:
    path = f"audiences[{index}]"
    if not isinstance(value, Mapping):
        fields[path] = "must be a JSON object"
        return {}
    _reject_unknown(
        value,
        {
            "id",
            "country",
            "region",
            "local_context",
            "language_signal",
            "language",
            "age_band",
            "occupation",
            "city_tier",
            "income_band",
            "exclusions",
            "persona_pack_id",
        },
        path,
        fields,
    )
    if "language" in value and "language_signal" in value and value.get("language") != value.get("language_signal"):
        fields[f"{path}.language_signal"] = "conflicts with language"

    supplied_id = _safe_reference_id(value.get("id"), f"{path}.id", "audience", fields)
    country = _optional_string(
        value,
        "country",
        f"{path}.country",
        fields,
        max_length=MAX_LENGTHS["audiences[].country"],
        default="IN",
    )
    if country is not None:
        country = country.upper()
        if not re.fullmatch(r"[A-Z]{2}", country):
            fields[f"{path}.country"] = "must be a two-letter country code"
    result: dict[str, Any] = {"id": supplied_id, "country": country or "IN"}
    for key in ("region", "age_band", "occupation", "city_tier", "income_band"):
        normalized = _required_string(
            value,
            key,
            f"{path}.{key}",
            fields,
            max_length=MAX_LENGTHS[f"audiences[].{key}"],
        )
        if normalized is not None:
            result[key] = normalized
    local_context = _optional_string(
        value,
        "local_context",
        f"{path}.local_context",
        fields,
        max_length=MAX_LENGTHS["audiences[].local_context"],
    )
    language_signal = _optional_string(
        value,
        "language_signal" if "language_signal" in value else "language",
        f"{path}.language_signal",
        fields,
        max_length=MAX_LENGTHS["audiences[].language_signal"],
    )
    result["local_context"] = local_context
    result["language_signal"] = language_signal
    exclusions = _string_list(
        value,
        "exclusions",
        f"{path}.exclusions",
        fields,
        max_items=20,
        item_max_length=MAX_LENGTHS["audiences[].exclusions[]"],
        required=False,
    )
    result["exclusions"] = exclusions or []
    persona_pack_id = _optional_string(
        value,
        "persona_pack_id",
        f"{path}.persona_pack_id",
        fields,
        max_length=MAX_LENGTHS["audiences[].persona_pack_id"],
        default="boss-india-v1",
    )
    result["persona_pack_id"] = persona_pack_id or "boss-india-v1"
    if result["id"] is None:
        result["id"] = _generated_reference_id("audience", result, index)
    return result


def _normalize_asset(value: Any, index: int, fields: dict[str, str]) -> dict[str, Any]:
    path = f"assets[{index}]"
    if not isinstance(value, Mapping):
        fields[path] = "must be a JSON object"
        return {}
    _reject_unknown(
        value,
        {
            "asset_id",
            "kind",
            "type",
            "title",
            "content",
            "language",
            "storage_key",
            "mime_type",
            "size_bytes",
            "sha256",
            "derived_artifacts",
        },
        path,
        fields,
    )
    kind = value.get("kind", value.get("type"))
    if "kind" in value and "type" in value and value.get("kind") != value.get("type"):
        fields[f"{path}.kind"] = "conflicts with type"
    if not isinstance(kind, str) or kind not in {"text", "document", "image", "audio", "video"}:
        fields[f"{path}.kind"] = "must be one of: text, document, image, audio, video"
        kind = "text"
    supplied_id = _safe_reference_id(value.get("asset_id"), f"{path}.asset_id", "asset", fields)
    title = _optional_string(
        value,
        "title",
        f"{path}.title",
        fields,
        max_length=MAX_LENGTHS["assets[].title"],
        allow_null=False,
    )
    if title is None and kind == "text" and "title" not in value:
        fields[f"{path}.title"] = "is required"
    content: str | None = None
    if "content" in value and value.get("content") is not None:
        content = _optional_string(
            value,
            "content",
            f"{path}.content",
            fields,
            max_length=MAX_LENGTHS["assets[].content"],
            allow_null=False,
        )
    elif kind == "text":
        fields[f"{path}.content"] = "is required"
    language = _optional_string(
        value,
        "language",
        f"{path}.language",
        fields,
        max_length=MAX_LENGTHS["assets[].language"],
        allow_null=True,
    )
    storage_key = _optional_string(
        value,
        "storage_key",
        f"{path}.storage_key",
        fields,
        max_length=MAX_LENGTHS["assets[].storage_key"],
        allow_null=True,
    )
    if storage_key is not None and (
        storage_key.startswith(("/", "\\"))
        or ".." in storage_key.split("/")
        or re.match(r"^[A-Za-z]:", storage_key)
    ):
        fields[f"{path}.storage_key"] = "must be a safe relative storage key"
    mime_type = _optional_string(
        value,
        "mime_type",
        f"{path}.mime_type",
        fields,
        max_length=MAX_LENGTHS["assets[].mime_type"],
        default="text/plain" if kind == "text" else "application/octet-stream",
    )
    size_bytes = value.get("size_bytes")
    if size_bytes is None:
        size_bytes = len(content.encode("utf-8")) if content is not None else 0
    elif not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 0:
        fields[f"{path}.size_bytes"] = "must be a non-negative integer"
        size_bytes = 0
    supplied_sha = value.get("sha256")
    if supplied_sha is not None and (
        not isinstance(supplied_sha, str)
        or SHA256_PATTERN.fullmatch(supplied_sha.strip().lower()) is None
    ):
        fields[f"{path}.sha256"] = "must be a lowercase SHA-256 hex digest"
        supplied_sha = None
    if supplied_sha is None and content is not None:
        supplied_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
    derived_artifacts = value.get("derived_artifacts", [])
    normalized_artifacts: list[dict[str, Any]] = []
    if not isinstance(derived_artifacts, list) or len(derived_artifacts) > 50:
        fields[f"{path}.derived_artifacts"] = "must be an array with at most 50 items"
    elif any(not isinstance(item, Mapping) for item in derived_artifacts):
        fields[f"{path}.derived_artifacts"] = "must contain JSON objects"
    else:
        allowed_artifact_keys = {
            "artifact_id",
            "kind",
            "processor",
            "processor_name",
            "processor_version",
            "status",
            "text",
            "derived_text",
            "content",
        }
        for artifact_index, artifact in enumerate(derived_artifacts):
            artifact_path = f"{path}.derived_artifacts[{artifact_index}]"
            _reject_unknown(artifact, allowed_artifact_keys, artifact_path, fields)
            normalized_artifact: dict[str, Any] = {}
            artifact_id = artifact.get("artifact_id")
            if artifact_id is not None:
                if (
                    not isinstance(artifact_id, str)
                    or not artifact_id.strip()
                    or len(artifact_id.strip()) > 120
                    or "/" in artifact_id
                    or "\\" in artifact_id
                ):
                    fields[f"{artifact_path}.artifact_id"] = "must be a safe identifier"
                else:
                    normalized_artifact["artifact_id"] = artifact_id.strip()
            for key in ("kind", "processor", "processor_name", "processor_version", "status"):
                item = artifact.get(key)
                if item is None:
                    continue
                if not isinstance(item, str) or not item.strip():
                    fields[f"{artifact_path}.{key}"] = "must be a non-empty string"
                elif len(item.strip()) > MAX_LENGTHS.get(
                    f"assets[].derived_artifacts[].{key}", 120
                ):
                    fields[f"{artifact_path}.{key}"] = "is too long"
                elif _is_absolute_path(item):
                    fields[f"{artifact_path}.{key}"] = "must not be an absolute path"
                else:
                    normalized_artifact[key] = item.strip()
            text_keys = [key for key in ("text", "derived_text", "content") if key in artifact]
            if len(text_keys) > 1:
                fields[f"{artifact_path}.text"] = "use only one text field"
            if text_keys:
                text_key = text_keys[0]
                text_value = artifact.get(text_key)
                if not isinstance(text_value, str):
                    fields[f"{artifact_path}.{text_key}"] = "must be a string"
                elif len(text_value) > MAX_LENGTHS["assets[].derived_artifacts[].text"]:
                    fields[f"{artifact_path}.{text_key}"] = "is too long"
                else:
                    normalized_artifact[text_key] = text_value
            if normalized_artifact:
                normalized_artifacts.append(normalized_artifact)
    # Preserve only typed, bounded text/artifact references. Binary data,
    # storage paths, and arbitrary metadata never enter the scenario snapshot.
    return {
        "asset_id": supplied_id or _generated_reference_id("asset", value, index),
        "kind": kind,
        "title": title,
        "content": content,
        "storage_key": storage_key,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "sha256": supplied_sha,
        "language": language,
        "derived_artifacts": normalized_artifacts,
    }


def _normalize_run_config(config: Any, fields: dict[str, str]) -> dict[str, Any]:
    path = "run_config"
    if not isinstance(config, Mapping):
        fields[path] = "is required and must be a JSON object"
        return {}
    _reject_unknown(
        config,
        {
            "execution_mode",
            "analysis_mode",
            "interaction_formats",
            "interaction_format",
            "report_language",
            "persona_count",
            "budget",
            "timezone",
            "seed",
            "graph_memory_update",
        },
        path,
        fields,
    )
    execution_mode = config.get("execution_mode", config.get("analysis_mode", "offline"))
    if "execution_mode" in config and "analysis_mode" in config and config.get("execution_mode") != config.get("analysis_mode"):
        fields[f"{path}.execution_mode"] = "conflicts with analysis_mode"
    if execution_mode not in {"offline", "model", "graph_oasis"}:
        fields[f"{path}.execution_mode"] = "must be one of: offline, model, graph_oasis"
        execution_mode = "offline"

    if "interaction_formats" in config and "interaction_format" in config:
        fields[f"{path}.interaction_formats"] = "conflicts with interaction_format"
    formats_value = config.get("interaction_formats", config.get("interaction_format"))
    if formats_value is None:
        fields[f"{path}.interaction_formats"] = "is required"
        interaction_formats: list[str] = []
    elif isinstance(formats_value, str):
        interaction_formats = [formats_value]
    elif isinstance(formats_value, list):
        interaction_formats = []
        if len(formats_value) > 12:
            fields[f"{path}.interaction_formats"] = "must contain at most 12 items"
        for index, item in enumerate(formats_value):
            item_path = f"{path}.interaction_formats[{index}]"
            if not isinstance(item, str) or not item.strip():
                fields[item_path] = "must be a non-empty string"
            elif len(item.strip()) > MAX_LENGTHS["run_config[].interaction_formats[]"]:
                fields[item_path] = "must be at most 80 characters"
            else:
                interaction_formats.append(item.strip())
    else:
        fields[f"{path}.interaction_formats"] = "must be a string or an array of strings"
        interaction_formats = []
    if not interaction_formats:
        fields.setdefault(f"{path}.interaction_formats", "must contain at least one format")

    report_language = config.get("report_language")
    if report_language not in {"en", "hi"}:
        fields[f"{path}.report_language"] = "must be one of: en, hi"
        report_language = "en"
    persona_count = config.get("persona_count")
    if not isinstance(persona_count, int) or isinstance(persona_count, bool) or not 4 <= persona_count <= 10:
        fields[f"{path}.persona_count"] = "must be an integer between 4 and 10"
        persona_count = 4
    budget = config.get("budget")
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1:
        fields[f"{path}.budget"] = "must be an integer greater than or equal to 1"
        budget = 1
    timezone = _optional_string(
        config,
        "timezone",
        f"{path}.timezone",
        fields,
        max_length=MAX_LENGTHS["run_config[].timezone"],
        default="Asia/Kolkata",
    )
    seed = config.get("seed")
    if seed is not None and (
        not isinstance(seed, int)
        or isinstance(seed, bool)
        or not -(2**63) <= seed <= 2**63 - 1
    ):
        fields[f"{path}.seed"] = "must be a signed 64-bit integer"
        seed = None
    graph_memory_update = config.get("graph_memory_update", False)
    if not isinstance(graph_memory_update, bool):
        fields[f"{path}.graph_memory_update"] = "must be a boolean"
        graph_memory_update = False
    return {
        "execution_mode": execution_mode,
        "interaction_formats": interaction_formats,
        "report_language": report_language,
        "persona_count": persona_count,
        "budget": budget,
        "timezone": timezone or "Asia/Kolkata",
        "seed": seed,
        "graph_memory_update": graph_memory_update,
    }


def _normalize_provenance(provenance: Any, fields: dict[str, str]) -> dict[str, Any]:
    path = "provenance"
    if provenance is None:
        provenance = {}
    if not isinstance(provenance, Mapping):
        fields[path] = "must be a JSON object"
        provenance = {}
    _reject_unknown(provenance, {"hypothetical", "input_source", "manifest_sha256"}, path, fields)
    hypothetical = provenance.get("hypothetical", True)
    if not isinstance(hypothetical, bool):
        fields[f"{path}.hypothetical"] = "must be a boolean"
        hypothetical = True
    input_source = _optional_string(
        provenance,
        "input_source",
        f"{path}.input_source",
        fields,
        max_length=MAX_LENGTHS["provenance.input_source"],
        default="user",
    )
    return {"hypothetical": hypothetical, "input_source": input_source or "user"}


def normalize_manifest(
    payload: Any,
    *,
    scenario_id: str | None = None,
    revision: int | None = None,
) -> dict[str, Any]:
    """Return a validated canonical BOSS manifest without performing I/O."""

    fields: dict[str, str] = {}
    if not isinstance(payload, Mapping):
        raise BossScenarioValidationError({"payload": "must be a JSON object"})

    # Permit a response's manifest object to be submitted directly while
    # keeping the public API's normal request shape flat.
    if isinstance(payload.get("manifest"), Mapping) and "brand" not in payload:
        payload = payload["manifest"]
    _walk_sensitive_keys(payload, "", fields)
    _reject_unknown(
        payload,
        {
            "schema_version",
            "scenario_id",
            "revision",
            "brand",
            "audience",
            "audiences",
            "asset",
            "assets",
            "config",
            "run_config",
            "provenance",
            "manifest_sha256",
        },
        "",
        fields,
    )
    schema_version = payload.get("schema_version", SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION:
        fields["schema_version"] = f"must be '{SCHEMA_VERSION}'"

    input_scenario_id = payload.get("scenario_id")
    if scenario_id is not None:
        if input_scenario_id is not None and input_scenario_id != scenario_id:
            fields["scenario_id"] = "does not match the persisted scenario"
        selected_scenario_id = scenario_id
    elif input_scenario_id is None:
        selected_scenario_id = f"scenario_{uuid.uuid4().hex[:24]}"
    else:
        selected_scenario_id = input_scenario_id
    if not isinstance(selected_scenario_id, str) or SCENARIO_ID_PATTERN.fullmatch(selected_scenario_id) is None:
        fields["scenario_id"] = "must match scenario_<24 lowercase hex characters>"

    input_revision = payload.get("revision", 1)
    selected_revision = revision if revision is not None else input_revision
    if revision is not None and input_revision != revision and "revision" in payload:
        fields["revision"] = "does not match the requested revision"
    if not isinstance(selected_revision, int) or isinstance(selected_revision, bool) or selected_revision < 1:
        fields["revision"] = "must be a positive integer"

    brand = _normalize_brand(payload.get("brand"), fields)

    if "audience" in payload and "audiences" in payload:
        fields["audiences"] = "use either audiences or audience, not both"
    audience_values = payload.get("audiences", payload.get("audience"))
    if isinstance(audience_values, Mapping):
        audience_values = [audience_values]
    elif audience_values is None:
        audience_values = []
    elif not isinstance(audience_values, list):
        fields["audiences"] = "must be an array of JSON objects"
        audience_values = []
    if not audience_values:
        fields["audiences"] = "must contain at least one audience"
    elif len(audience_values) > 50:
        fields["audiences"] = "must contain at most 50 audiences"
    audiences = [_normalize_audience(item, index, fields) for index, item in enumerate(audience_values)]

    if "asset" in payload and "assets" in payload:
        fields["assets"] = "use either assets or asset, not both"
    asset_values = payload.get("assets", payload.get("asset"))
    if isinstance(asset_values, Mapping):
        asset_values = [asset_values]
    elif asset_values is None:
        asset_values = []
    elif not isinstance(asset_values, list):
        fields["assets"] = "must be an array of JSON objects"
        asset_values = []
    if not asset_values:
        fields["assets"] = "must contain at least one asset"
    elif len(asset_values) > 50:
        fields["assets"] = "must contain at most 50 assets"
    assets = [_normalize_asset(item, index, fields) for index, item in enumerate(asset_values)]

    if "config" in payload and "run_config" in payload:
        fields["run_config"] = "use either run_config or config, not both"
    config = payload.get("run_config", payload.get("config"))
    run_config = _normalize_run_config(config, fields)
    provenance = _normalize_provenance(payload.get("provenance"), fields)

    if fields:
        raise BossScenarioValidationError(fields)

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "scenario_id": selected_scenario_id,
        "revision": selected_revision,
        "brand": brand,
        "audiences": audiences,
        "assets": assets,
        "run_config": run_config,
        "provenance": provenance,
    }
    manifest_hash = hashlib.sha256(_canonical_json(manifest)).hexdigest()
    manifest["provenance"]["manifest_sha256"] = manifest_hash
    return manifest


def manifest_sha256(manifest: Mapping[str, Any]) -> str:
    """Compute the canonical hash of a manifest, ignoring its stored hash."""

    copy_manifest = json.loads(json.dumps(manifest, ensure_ascii=False))
    provenance = copy_manifest.get("provenance")
    if isinstance(provenance, dict):
        provenance.pop("manifest_sha256", None)
    return hashlib.sha256(_canonical_json(copy_manifest)).hexdigest()


normalise_manifest = normalize_manifest


__all__ = [
    "BossScenarioValidationError",
    "MAX_LENGTHS",
    "SCENARIO_ID_PATTERN",
    "SCHEMA_VERSION",
    "ValidationError",
    "manifest_sha256",
    "normalise_manifest",
    "normalize_manifest",
]
