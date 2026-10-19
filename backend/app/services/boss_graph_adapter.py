"""Deterministic BOSS scenario-to-graph adapter.

The adapter is intentionally a small boundary around the existing graph
builder.  It does not generate an ontology from a model and it does not read
or write scenario files.  This keeps preparation deterministic and makes the
low-level build operation easy to exercise with a fake GraphBuilderService.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any, Callable

from ..config import Config
from ..models.boss_scenario import manifest_sha256
from .text_processor import TextProcessor


DEFAULT_PACKET_MAX_CHARS = 100_000
MAX_BATCH_ITEMS = 50_000
MAX_BATCH_ITEM_CHARS = 10_000


# Keep this definition literal and stable.  The names are valid Python/Zep
# model names and every edge endpoint names one of the entity types below.
_BOSS_ONTOLOGY: dict[str, Any] = {
    "entity_types": [
        {
            "name": "BrandAccount",
            "description": "The fictional brand account represented in a BOSS scenario.",
            "attributes": [
                {"name": "brand_name", "type": "text", "description": "Display name of the brand."},
                {"name": "positioning", "type": "text", "description": "Brand positioning in the scenario."},
                {"name": "tone", "type": "text", "description": "Preferred communication tone."},
                {"name": "scenario_id", "type": "text", "description": "Owning BOSS scenario identifier."},
            ],
        },
        {
            "name": "AudiencePersona",
            "description": "A synthetic audience persona used for BOSS exploration.",
            "attributes": [
                {"name": "persona_id", "type": "text", "description": "Stable audience identifier."},
                {"name": "occupation", "type": "text", "description": "Audience occupation context."},
                {"name": "language_signal", "type": "text", "description": "Language or local expression signal."},
            ],
        },
        {
            "name": "Asset",
            "description": "A submitted BOSS asset or bounded derived text artifact.",
            "attributes": [
                {"name": "asset_id", "type": "text", "description": "Stable asset identifier."},
                {"name": "asset_kind", "type": "text", "description": "Asset media kind."},
                {"name": "title", "type": "text", "description": "Asset title."},
                {"name": "content_sha256", "type": "text", "description": "Content hash from the manifest."},
            ],
        },
        {
            "name": "AudienceContext",
            "description": "Geographic, language, and socioeconomic context for an audience.",
            "attributes": [
                {"name": "country", "type": "text", "description": "Two-letter country code."},
                {"name": "region", "type": "text", "description": "Region or state context."},
                {"name": "city_tier", "type": "text", "description": "City tier context."},
                {"name": "income_band", "type": "text", "description": "Non-sensitive declared income band."},
            ],
        },
        {
            "name": "Claim",
            "description": "A claim or message statement grounded in a BOSS asset.",
            "attributes": [
                {"name": "claim_text", "type": "text", "description": "Claim text from the submitted material."},
                {"name": "source_asset_id", "type": "text", "description": "Source asset identifier."},
                {"name": "provenance_kind", "type": "text", "description": "Origin of the claim text."},
            ],
        },
    ],
    "edge_types": [
        {
            "name": "PUBLISHES",
            "description": "The brand account publishes an asset.",
            "attributes": [{"name": "provenance", "type": "text", "description": "Source provenance."}],
            "source_targets": [{"source": "BrandAccount", "target": "Asset"}],
        },
        {
            "name": "TARGETS_AUDIENCE",
            "description": "The brand account is considered for an audience context.",
            "attributes": [{"name": "provenance", "type": "text", "description": "Source provenance."}],
            "source_targets": [{"source": "BrandAccount", "target": "AudienceContext"}],
        },
        {
            "name": "HAS_PERSONA_CONTEXT",
            "description": "A synthetic persona belongs to an audience context.",
            "attributes": [{"name": "provenance", "type": "text", "description": "Source provenance."}],
            "source_targets": [{"source": "AudiencePersona", "target": "AudienceContext"}],
        },
        {
            "name": "SUPPORTS_CLAIM",
            "description": "An asset supports a claim extracted from its text.",
            "attributes": [{"name": "provenance", "type": "text", "description": "Source provenance."}],
            "source_targets": [{"source": "Asset", "target": "Claim"}],
        },
        {
            "name": "MAKES_CLAIM",
            "description": "The brand account makes a claim.",
            "attributes": [{"name": "provenance", "type": "text", "description": "Source provenance."}],
            "source_targets": [{"source": "BrandAccount", "target": "Claim"}],
        },
    ],
}


class BossGraphPacketBoundsError(ValueError):
    """Raised when a packet or graph batch exceeds a declared bound."""


def fixed_boss_ontology() -> dict[str, Any]:
    """Return a fresh copy of the fixed ontology used by BOSS graph builds."""

    return copy.deepcopy(_BOSS_ONTOLOGY)


def build_boss_ontology() -> dict[str, Any]:
    """Compatibility alias for callers that name ontology creation explicitly."""

    return fixed_boss_ontology()


def _canonical_manifest_hash(manifest: Mapping[str, Any]) -> str:
    if not isinstance(manifest, Mapping):
        raise ValueError("BOSS manifest must be a JSON object")
    provenance = manifest.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ValueError("BOSS manifest provenance is required")
    calculated = manifest_sha256(manifest)
    supplied = provenance.get("manifest_sha256")
    if supplied != calculated:
        raise ValueError("BOSS manifest hash does not match its canonical content")
    return calculated


def _value(value: Any) -> str:
    """Render scalar manifest values without exposing arbitrary object data."""

    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _list_lines(label: str, values: Any) -> list[str]:
    if not isinstance(values, list):
        return [f"{label}: "]
    return [f"{label}[{index}]: {_value(item)}" for index, item in enumerate(values)] or [f"{label}: "]


def _derived_texts(asset: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    """Select text-only derived evidence while ignoring unsafe metadata fields."""

    artifacts = asset.get("derived_artifacts", [])
    if not isinstance(artifacts, list):
        return []
    result: list[tuple[str, str, str]] = []
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, Mapping):
            continue
        text = None
        for key in ("text", "derived_text", "content"):
            if isinstance(artifact.get(key), str):
                text = artifact[key]
                break
        if text is None:
            continue
        artifact_id = _value(artifact.get("artifact_id") or f"derived_{index + 1}")
        processor = _value(artifact.get("processor") or artifact.get("processor_name") or "unspecified")
        result.append((artifact_id, processor, text))
    return result


def render_scenario_packet(
    manifest: Mapping[str, Any],
    *,
    max_chars: int = DEFAULT_PACKET_MAX_CHARS,
) -> str:
    """Render a deterministic, bounded textual projection of a BOSS manifest.

    Asset and derived text are inserted as exact text blocks.  If the complete
    projection would exceed ``max_chars`` the function raises instead of
    truncating evidence, so a graph can never silently ingest partial copy.
    Only whitelisted manifest fields are rendered; storage keys and arbitrary
    artifact metadata are intentionally omitted.
    """

    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars <= 0:
        raise ValueError("max_chars must be a positive integer")
    manifest_hash = _canonical_manifest_hash(manifest)
    brand = manifest.get("brand")
    audiences = manifest.get("audiences")
    assets = manifest.get("assets")
    run_config = manifest.get("run_config")
    provenance = manifest.get("provenance")
    if not isinstance(brand, Mapping) or not isinstance(audiences, list) or not isinstance(assets, list):
        raise ValueError("BOSS manifest is missing canonical brand, audience, or asset sections")
    if not isinstance(run_config, Mapping) or not isinstance(provenance, Mapping):
        raise ValueError("BOSS manifest is missing canonical configuration or provenance")

    lines = [
        "BOSS SCENARIO GRAPH PACKET",
        f"scenario_id: {_value(manifest.get('scenario_id'))}",
        f"revision: {_value(manifest.get('revision'))}",
        f"manifest_sha256: {manifest_hash}",
        "",
        "[brand_context]",
        f"name: {_value(brand.get('name'))}",
        f"positioning: {_value(brand.get('positioning'))}",
        f"tone: {_value(brand.get('tone'))}",
        f"audience_relationship: {_value(brand.get('audience_relationship'))}",
    ]
    lines.extend(_list_lines("red_line", brand.get("red_lines")))
    lines.extend(_list_lines("preferred_vocabulary", brand.get("preferred_vocabulary")))
    lines.extend(_list_lines("claim_guardrail", brand.get("claims_must_not_invent")))

    lines.extend(["", "[audience_context]"])
    for index, audience in enumerate(audiences):
        if not isinstance(audience, Mapping):
            raise ValueError(f"audiences[{index}] must be an object")
        lines.extend(
            [
                f"audience[{index}].id: {_value(audience.get('id'))}",
                f"audience[{index}].country: {_value(audience.get('country'))}",
                f"audience[{index}].region: {_value(audience.get('region'))}",
                f"audience[{index}].local_context: {_value(audience.get('local_context'))}",
                f"audience[{index}].language_signal: {_value(audience.get('language_signal'))}",
                f"audience[{index}].age_band: {_value(audience.get('age_band'))}",
                f"audience[{index}].occupation: {_value(audience.get('occupation'))}",
                f"audience[{index}].city_tier: {_value(audience.get('city_tier'))}",
                f"audience[{index}].income_band: {_value(audience.get('income_band'))}",
            ]
        )
        lines.extend(_list_lines(f"audience[{index}].exclusion", audience.get("exclusions")))

    lines.extend(["", "[asset_content]"])
    for index, asset in enumerate(assets):
        if not isinstance(asset, Mapping):
            raise ValueError(f"assets[{index}] must be an object")
        asset_id = _value(asset.get("asset_id"))
        lines.extend(
            [
                f"asset[{index}].asset_id: {asset_id}",
                f"asset[{index}].kind: {_value(asset.get('kind'))}",
                f"asset[{index}].title: {_value(asset.get('title'))}",
                f"asset[{index}].language: {_value(asset.get('language'))}",
                f"asset[{index}].sha256: {_value(asset.get('sha256'))}",
                f"asset[{index}].content.begin",
                _value(asset.get("content")),
                f"asset[{index}].content.end",
            ]
        )
        for derived_index, (artifact_id, processor, text) in enumerate(_derived_texts(asset)):
            lines.extend(
                [
                    f"asset[{index}].derived[{derived_index}].artifact_id: {artifact_id}",
                    f"asset[{index}].derived[{derived_index}].processor: {processor}",
                    f"asset[{index}].derived[{derived_index}].text.begin",
                    text,
                    f"asset[{index}].derived[{derived_index}].text.end",
                ]
            )

    lines.extend(
        [
            "",
            "[run_config]",
            f"execution_mode: {_value(run_config.get('execution_mode'))}",
            f"interaction_formats: {_value(','.join(_value(item) for item in run_config.get('interaction_formats', [])))}",
            f"timezone: {_value(run_config.get('timezone'))}",
            f"seed: {_value(run_config.get('seed'))}",
            "",
            "[provenance]",
            f"hypothetical: {_value(provenance.get('hypothetical'))}",
            f"input_source: {_value(provenance.get('input_source'))}",
            f"manifest_sha256: {manifest_hash}",
        ]
    )
    packet = "\n".join(lines)
    if len(packet) > max_chars:
        raise BossGraphPacketBoundsError(
            f"BOSS scenario packet exceeds the {max_chars} character limit"
        )
    return packet


def validate_packet_chunks(chunks: list[str], *, batch_size: int = 350) -> None:
    """Validate the same batch bounds enforced by GraphBuilderService."""

    if not isinstance(chunks, list) or not chunks:
        raise ValueError("At least one BOSS packet chunk is required")
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or not 1 <= batch_size <= 350:
        raise ValueError("batch_size must be between 1 and 350")
    if len(chunks) > MAX_BATCH_ITEMS:
        raise BossGraphPacketBoundsError("A BOSS graph batch cannot contain more than 50,000 items")
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, str) or not chunk:
            raise ValueError(f"BOSS packet chunk {index} must be non-empty text")
        if len(chunk) > MAX_BATCH_ITEM_CHARS:
            raise BossGraphPacketBoundsError(
                f"BOSS packet chunk {index} exceeds 10,000 characters"
            )


def chunk_scenario_packet(
    packet: str,
    *,
    chunk_size: int | None = None,
    overlap: int | None = None,
    batch_size: int = 350,
) -> list[str]:
    """Chunk and validate a prepared packet using project defaults."""

    selected_size = Config.DEFAULT_CHUNK_SIZE if chunk_size is None else chunk_size
    selected_overlap = Config.DEFAULT_CHUNK_OVERLAP if overlap is None else overlap
    if not isinstance(packet, str) or not packet:
        raise ValueError("BOSS scenario packet must be non-empty text")
    if (
        not isinstance(selected_size, int)
        or isinstance(selected_size, bool)
        or selected_size <= 0
    ):
        raise ValueError("chunk_size must be a positive integer")
    if (
        not isinstance(selected_overlap, int)
        or isinstance(selected_overlap, bool)
        or selected_overlap < 0
        or selected_overlap >= selected_size
    ):
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")
    chunks = TextProcessor.split_text(packet, selected_size, selected_overlap)
    validate_packet_chunks(chunks, batch_size=batch_size)
    return chunks


def chunk_and_validate_packet(
    packet: str,
    *,
    chunk_size: int | None = None,
    overlap: int | None = None,
    batch_size: int = 350,
) -> list[str]:
    """Descriptive alias for ``chunk_scenario_packet``."""

    return chunk_scenario_packet(
        packet,
        chunk_size=chunk_size,
        overlap=overlap,
        batch_size=batch_size,
    )


def build_boss_graph_metadata(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return stable metadata attached to every BOSS graph projection."""

    manifest_hash = _canonical_manifest_hash(manifest)
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise ValueError("BOSS manifest assets are required")
    asset_ids = []
    for index, asset in enumerate(assets):
        if not isinstance(asset, Mapping) or not isinstance(asset.get("asset_id"), str):
            raise ValueError(f"assets[{index}].asset_id is required")
        asset_ids.append(asset["asset_id"])
    return {
        "source_kind": "boss_scenario",
        "manifest_sha256": manifest_hash,
        "scenario_id": manifest.get("scenario_id"),
        "revision": manifest.get("revision"),
        "asset_ids": asset_ids,
    }


def build_graph_metadata(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Short alias for callers that do not need the BOSS-specific prefix."""

    return build_boss_graph_metadata(manifest)


def build_boss_graph(
    manifest: Mapping[str, Any],
    builder: Any,
    *,
    graph_name: str | None = None,
    chunk_size: int | None = None,
    overlap: int | None = None,
    batch_size: int = 350,
    packet_max_chars: int = DEFAULT_PACKET_MAX_CHARS,
    graph_id_callback: Callable[[str], None] | None = None,
    batch_created_callback: Callable[[str | None, str], None] | None = None,
    wait_for_ingestion: bool = True,
) -> dict[str, Any]:
    """Build a BOSS graph through an injected GraphBuilderService.

    Calls deliberately follow the public signatures of the existing builder:
    ``create_graph`` -> ``set_ontology`` -> ``add_text_batches``.  No builder
    construction or Zep client access happens in this function.
    """

    packet = render_scenario_packet(manifest, max_chars=packet_max_chars)
    chunks = chunk_scenario_packet(
        packet,
        chunk_size=chunk_size,
        overlap=overlap,
        batch_size=batch_size,
    )
    ontology = fixed_boss_ontology()
    metadata = build_boss_graph_metadata(manifest)
    selected_graph_name = graph_name or f"BOSS Scenario {metadata['scenario_id']}"

    create_kwargs: dict[str, Any] = {"name": selected_graph_name}
    if graph_id_callback is not None:
        create_kwargs["graph_id_callback"] = graph_id_callback
    graph_id = builder.create_graph(**create_kwargs)
    builder.set_ontology(graph_id, ontology)
    batch_kwargs: dict[str, Any] = {"batch_size": batch_size}
    if batch_created_callback is not None:
        batch_kwargs["batch_created_callback"] = batch_created_callback
    submission = builder.add_text_batches(graph_id, chunks, **batch_kwargs)
    wait_for_batch = getattr(builder, "_wait_for_batch", None)
    if wait_for_ingestion and callable(wait_for_batch):
        wait_for_batch(submission)
    result = {
        **metadata,
        "graph_id": graph_id,
        "batch_id": getattr(submission, "batch_id", None),
        "operation_id": getattr(submission, "operation_id", None),
        "episode_uuids": list(getattr(submission, "episode_uuids", []) or []),
        "chunk_count": len(chunks),
    }
    return result


class BossGraphAdapter:
    """Object-oriented facade for dependency injection and API orchestration."""

    fixed_ontology = staticmethod(fixed_boss_ontology)
    render_packet = staticmethod(render_scenario_packet)
    chunk_packet = staticmethod(chunk_scenario_packet)
    graph_metadata = staticmethod(build_boss_graph_metadata)

    @staticmethod
    def build(manifest: Mapping[str, Any], builder: Any, **kwargs: Any) -> dict[str, Any]:
        return build_boss_graph(manifest, builder, **kwargs)


__all__ = [
    "BossGraphAdapter",
    "BossGraphPacketBoundsError",
    "DEFAULT_PACKET_MAX_CHARS",
    "build_boss_graph",
    "build_boss_graph_metadata",
    "build_boss_ontology",
    "build_graph_metadata",
    "chunk_and_validate_packet",
    "chunk_scenario_packet",
    "fixed_boss_ontology",
    "render_scenario_packet",
    "validate_packet_chunks",
]
