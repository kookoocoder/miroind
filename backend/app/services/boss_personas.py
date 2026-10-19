"""Deterministic BOSS persona materialization and OASIS serializers.

The legacy :mod:`oasis_profile_generator` is intentionally model-backed and
uses random values for some fallback fields.  BOSS preparation needs a
different boundary: a canonical scenario must produce the same fictional
accounts every time, without contacting Zep or an LLM.  This module uses the
inspectable research lenses in ``miroind.PERSONA_TEMPLATES`` and only the
audience context explicitly supplied in the manifest.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..models.boss_asset import is_asset_id
from ..models.boss_scenario import manifest_sha256
from .miroind import PERSONA_TEMPLATES, get_persona_templates


BOSS_TIMEZONE = "Asia/Kolkata"
BOSS_SOURCE_KIND = "boss_scenario"
BOSS_PROFILE_SCHEMA_VERSION = "boss.profile.v1"
BOSS_SIMULATION_SCHEMA_VERSION = "boss.simulation.v1"
_SAFE_ID = re.compile(r"[^a-z0-9]+")


class BossSimulationValidationError(ValueError):
    """A safe, structured validation error for BOSS simulation preparation."""

    def __init__(self, fields: dict[str, str], message: str = "BOSS simulation validation failed"):
        self.fields = fields
        super().__init__(message)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _slug(value: Any) -> str:
    """Return a stable ASCII component suitable for an OASIS username."""

    normalized = _text(value).casefold()
    normalized = _SAFE_ID.sub("_", normalized).strip("_")
    return normalized or "unknown"


def _stable_profile_id(scenario_id: str, audience_id: str | None, persona_id: str | None) -> str:
    value = "|".join((scenario_id, audience_id or "brand", persona_id or "brand"))
    return f"boss_profile_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:24]}"


def _stable_username(scenario_id: str, audience_id: str | None, persona_id: str | None) -> str:
    parts = ["boss", _slug(scenario_id)]
    if audience_id is None:
        parts.append("brand")
    else:
        parts.extend((_slug(audience_id), _slug(persona_id)))
    return "_".join(parts)


def _list_text(value: Any) -> str:
    if not isinstance(value, (list, tuple)):
        return ""
    return ", ".join(_text(item) for item in value if _text(item))


def _brand_context(brand: Mapping[str, Any]) -> dict[str, Any]:
    """Copy only canonical brand fields into a profile context."""

    return {
        "name": _text(brand.get("name")),
        "positioning": _text(brand.get("positioning")),
        "tone": _text(brand.get("tone")),
        "audience_relationship": _text(brand.get("audience_relationship")),
        "red_lines": [item for item in brand.get("red_lines", []) if isinstance(item, str)],
        "preferred_vocabulary": [
            item for item in brand.get("preferred_vocabulary", []) if isinstance(item, str)
        ],
        "claims_must_not_invent": [
            item for item in brand.get("claims_must_not_invent", []) if isinstance(item, str)
        ],
    }


def _brand_context_text(brand: Mapping[str, Any]) -> list[str]:
    context = _brand_context(brand)
    return [
        "BOSS brand context",
        f"brand_name: {context['name']}",
        f"positioning: {context['positioning']}",
        f"tone: {context['tone']}",
        f"audience_relationship: {context['audience_relationship']}",
        f"red_lines: {_list_text(context['red_lines'])}",
        f"preferred_vocabulary: {_list_text(context['preferred_vocabulary'])}",
        f"claims_must_not_invent: {_list_text(context['claims_must_not_invent'])}",
    ]


def _audience_context(audience: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {
        "audience_id": _text(audience.get("id")),
        "country": _text(audience.get("country")).upper() or "IN",
        "timezone": BOSS_TIMEZONE,
        "region": _text(audience.get("region")),
        "occupation": _text(audience.get("occupation")),
        "city_tier": _text(audience.get("city_tier")),
        "income_band": _text(audience.get("income_band")),
        "age_band": _text(audience.get("age_band")),
    }
    for key in ("local_context", "language_signal"):
        value = _text(audience.get(key))
        if value:
            context[key] = value
    return context


def _audience_context_text(audience: Mapping[str, Any]) -> list[str]:
    context = _audience_context(audience)
    lines = [
        "India audience context",
        f"country: {context['country']}",
        f"timezone: {context['timezone']}",
        f"region: {context['region']}",
        f"occupation: {context['occupation']}",
        f"city_tier: {context['city_tier']}",
        f"income_band: {context['income_band']}",
        f"age_band: {context['age_band']}",
    ]
    for key in ("local_context", "language_signal"):
        if key in context:
            lines.append(f"{key}: {context[key]}")
    lines.append("sensitive_attributes: not inferred")
    return lines


@dataclass(frozen=True)
class BossAgentProfile:
    """A deterministic profile that can be projected to either OASIS format."""

    agent_id: int
    profile_id: str
    scenario_id: str
    username: str
    name: str
    bio: str
    user_char: str
    account_kind: str
    country: str
    timezone: str
    profile_context: dict[str, Any]
    audience_id: str | None = None
    persona_id: str | None = None
    region: str | None = None
    occupation: str | None = None
    city_tier: str | None = None
    income_band: str | None = None
    local_context: str | None = None
    language_signal: str | None = None

    @property
    def user_id(self) -> int:
        """OASIS and BOSS use the same stable numeric identifier."""

        return self.agent_id

    @property
    def user_name(self) -> str:
        """Compatibility alias used by ``OasisAgentProfile`` callers."""

        return self.username

    @property
    def persona(self) -> str:
        """Compatibility alias for the Reddit persona field."""

        return self.user_char

    def __getitem__(self, key: str) -> Any:
        """Allow small callers/tests to treat a profile like a JSON object."""

        return self.to_dict()[key]

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": BOSS_PROFILE_SCHEMA_VERSION,
            "agent_id": self.agent_id,
            "user_id": self.agent_id,
            "profile_id": self.profile_id,
            "scenario_id": self.scenario_id,
            "username": self.username,
            "user_name": self.username,
            "name": self.name,
            "bio": self.bio,
            "persona": self.user_char,
            "user_char": self.user_char,
            "account_kind": self.account_kind,
            "country": self.country,
            "timezone": self.timezone,
            "profile_context": self.profile_context,
        }
        for key in (
            "audience_id",
            "persona_id",
            "region",
            "occupation",
            "city_tier",
            "income_band",
            "local_context",
            "language_signal",
        ):
            value = getattr(self, key)
            if value is not None:
                result[key] = value
        return result


def _manifest_sections(manifest: Mapping[str, Any]) -> tuple[str, Mapping[str, Any], list[Mapping[str, Any]]]:
    if not isinstance(manifest, Mapping):
        raise BossSimulationValidationError({"manifest": "must be a JSON object"})
    scenario_id = _text(manifest.get("scenario_id"))
    brand = manifest.get("brand")
    audiences = manifest.get("audiences")
    if not scenario_id:
        raise BossSimulationValidationError({"scenario_id": "is required"})
    if not isinstance(brand, Mapping):
        raise BossSimulationValidationError({"brand": "is required and must be a JSON object"})
    if not isinstance(audiences, list) or not audiences:
        raise BossSimulationValidationError({"audiences": "must contain at least one audience"})
    normalized_audiences: list[Mapping[str, Any]] = []
    for index, audience in enumerate(audiences):
        if not isinstance(audience, Mapping):
            raise BossSimulationValidationError({f"audiences[{index}]": "must be a JSON object"})
        audience_id = _text(audience.get("id"))
        if not audience_id:
            raise BossSimulationValidationError({f"audiences[{index}].id": "is required"})
        normalized_audiences.append(audience)
    return scenario_id, brand, normalized_audiences


def _selected_audiences(
    audiences: list[Mapping[str, Any]], audience_ids: Sequence[str] | None
) -> list[Mapping[str, Any]]:
    by_id = {_text(audience.get("id")): audience for audience in audiences}
    if audience_ids is None:
        selected_ids = sorted(by_id)
    else:
        if isinstance(audience_ids, (str, bytes)) or not isinstance(audience_ids, Sequence):
            raise BossSimulationValidationError({"audience_ids": "must be an array of strings"})
        selected_ids = sorted({_text(item) for item in audience_ids})
        if not selected_ids or any(not item for item in selected_ids):
            raise BossSimulationValidationError({"audience_ids": "must contain at least one audience id"})
        missing = [item for item in selected_ids if item not in by_id]
        if missing:
            raise BossSimulationValidationError({"audience_ids": f"unknown audience id: {missing[0]}"})
    return [by_id[item] for item in selected_ids]


def _selected_personas(
    manifest: Mapping[str, Any], persona_ids: Sequence[str] | None
) -> list[dict[str, Any]]:
    run_config = manifest.get("run_config")
    count = run_config.get("persona_count", 6) if isinstance(run_config, Mapping) else 6
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= len(PERSONA_TEMPLATES):
        count = min(6, len(PERSONA_TEMPLATES))
    templates = get_persona_templates(count)
    if persona_ids is None:
        return templates
    if isinstance(persona_ids, (str, bytes)) or not isinstance(persona_ids, Sequence):
        raise BossSimulationValidationError({"persona_ids": "must be an array of strings"})
    requested = {_text(item) for item in persona_ids}
    if not requested or "" in requested:
        raise BossSimulationValidationError({"persona_ids": "must contain at least one persona id"})
    known = {template["id"] for template in PERSONA_TEMPLATES}
    missing = sorted(requested - known)
    if missing:
        raise BossSimulationValidationError({"persona_ids": f"unknown persona id: {missing[0]}"})
    return [template for template in PERSONA_TEMPLATES if template["id"] in requested]


def materialize_boss_profiles(
    manifest: Mapping[str, Any],
    *,
    audience_ids: Sequence[str] | None = None,
    persona_ids: Sequence[str] | None = None,
) -> list[BossAgentProfile]:
    """Materialize one brand account and deterministic audience-lens accounts.

    Numeric IDs are assigned in canonical audience/persona order, with the
    brand fixed at ``0`` and the first audience account fixed at ``1``.  The
    stable profile key and username also include all three scenario identity
    components, so repeated previews do not depend on UUIDs or process state.
    """

    scenario_id, brand, audiences = _manifest_sections(manifest)
    selected_audiences = _selected_audiences(audiences, audience_ids)
    selected_personas = _selected_personas(manifest, persona_ids)
    brand_values = _brand_context(brand)
    brand_lines = _brand_context_text(brand) + [
        f"scenario_id: {scenario_id}",
        f"country: IN",
        f"timezone: {BOSS_TIMEZONE}",
        "account_kind: brand",
        "sensitive_attributes: not inferred",
    ]
    brand_username = _stable_username(scenario_id, None, None)
    brand_profile_context = {
        "brand": brand_values,
        "country": "IN",
        "timezone": BOSS_TIMEZONE,
        "sensitive_attributes_inferred": [],
    }
    profiles = [
        BossAgentProfile(
            agent_id=0,
            profile_id=_stable_profile_id(scenario_id, None, None),
            scenario_id=scenario_id,
            username=brand_username,
            name=brand_values["name"] or "BOSS Brand",
            bio=f"Official fictional brand account for {brand_values['name'] or 'the BOSS scenario'}.",
            user_char="\n".join(brand_lines),
            account_kind="brand",
            country="IN",
            timezone=BOSS_TIMEZONE,
            profile_context=brand_profile_context,
        )
    ]

    next_agent_id = 1
    for audience in selected_audiences:
        audience_values = _audience_context(audience)
        audience_id = audience_values["audience_id"]
        for template in selected_personas:
            persona_id = template["id"]
            persona_lines = _brand_context_text(brand)
            persona_lines.extend(
                [
                    f"scenario_id: {scenario_id}",
                    f"audience_id: {audience_id}",
                    f"persona_id: {persona_id}",
                    f"persona_label: {template['label']}",
                    f"research_lens: {template['research_lens']}",
                    f"priorities: {_list_text(template['priorities'])}",
                ]
            )
            persona_lines.extend(_audience_context_text(audience))
            context = {
                "brand": brand_values,
                "audience": audience_values,
                "persona": {
                    "id": persona_id,
                    "label": template["label"],
                    "research_lens": template["research_lens"],
                    "priorities": list(template["priorities"]),
                },
                "sensitive_attributes_inferred": [],
            }
            bio = (
                f"{template['label']} lens for {audience_values['occupation']} in "
                f"{audience_values['region']}, India."
            )
            profiles.append(
                BossAgentProfile(
                    agent_id=next_agent_id,
                    profile_id=_stable_profile_id(scenario_id, audience_id, persona_id),
                    scenario_id=scenario_id,
                    username=_stable_username(scenario_id, audience_id, persona_id),
                    name=f"{template['label']} — {audience_id}",
                    bio=bio,
                    user_char="\n".join(persona_lines),
                    account_kind="audience",
                    country=audience_values["country"],
                    timezone=BOSS_TIMEZONE,
                    profile_context=context,
                    audience_id=audience_id,
                    persona_id=persona_id,
                    region=audience_values["region"],
                    occupation=audience_values["occupation"],
                    city_tier=audience_values["city_tier"],
                    income_band=audience_values["income_band"],
                    local_context=audience_values.get("local_context"),
                    language_signal=audience_values.get("language_signal"),
                )
            )
            next_agent_id += 1
    return profiles


def materialize_boss_personas(*args: Any, **kwargs: Any) -> list[BossAgentProfile]:
    """Naming alias for callers that describe the operation as persona creation."""

    return materialize_boss_profiles(*args, **kwargs)


def _as_profiles(value: Any) -> list[BossAgentProfile]:
    if isinstance(value, BossAgentProfile):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        profiles = list(value)
        if all(isinstance(profile, BossAgentProfile) for profile in profiles):
            return profiles
    raise TypeError("profiles must be a sequence of BossAgentProfile values")


def serialize_reddit_profiles(profiles: Sequence[BossAgentProfile]) -> list[dict[str, Any]]:
    """Return the OASIS Reddit JSON list without adding inferred attributes."""

    result = []
    for profile in _as_profiles(profiles):
        item: dict[str, Any] = {
            "user_id": profile.agent_id,
            "username": profile.username,
            "name": profile.name,
            "bio": profile.bio,
            "persona": profile.user_char,
            # ``user_char`` is useful to BOSS consumers while ``persona`` is
            # the field used by the existing OASIS Reddit serializer.
            "user_char": profile.user_char,
            "country": profile.country,
            "timezone": profile.timezone,
        }
        for key in (
            "region",
            "occupation",
            "city_tier",
            "income_band",
            "local_context",
            "language_signal",
            "audience_id",
            "persona_id",
        ):
            value = getattr(profile, key)
            if value is not None:
                item[key] = value
        result.append(item)
    return result


def serialize_reddit_json(profiles: Sequence[BossAgentProfile], *, indent: int = 2) -> str:
    return json.dumps(serialize_reddit_profiles(profiles), ensure_ascii=False, indent=indent) + "\n"


def serialize_twitter_profiles(profiles: Sequence[BossAgentProfile]) -> list[dict[str, Any]]:
    """Return stable rows for the existing OASIS Twitter CSV contract."""

    return [
        {
            "agent_id": profile.agent_id,
            "user_id": profile.agent_id,
            "name": profile.name,
            "username": profile.username,
            "user_char": profile.user_char.replace("\n", " ").replace("\r", " "),
            "description": profile.bio.replace("\n", " ").replace("\r", " "),
        }
        for profile in _as_profiles(profiles)
    ]


def serialize_twitter_csv(profiles: Sequence[BossAgentProfile]) -> str:
    """Serialize profiles to OASIS Twitter CSV with a stable ``agent_id``."""

    rows = serialize_twitter_profiles(profiles)
    fields = ["agent_id", "user_id", "name", "username", "user_char", "description"]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


serialize_twitter_profiles_csv = serialize_twitter_csv


def profile_dicts(profiles: Sequence[BossAgentProfile]) -> list[dict[str, Any]]:
    """Return JSON-safe full profile records for the BOSS preparation record."""

    return [profile.to_dict() for profile in _as_profiles(profiles)]


def _manifest_assets(manifest: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise BossSimulationValidationError({"assets": "must contain at least one asset"})
    normalized: list[Mapping[str, Any]] = []
    for index, asset in enumerate(assets):
        if not isinstance(asset, Mapping):
            raise BossSimulationValidationError({f"assets[{index}]": "must be a JSON object"})
        normalized.append(asset)
    return normalized


def _text_from_derived_artifacts(
    asset: Mapping[str, Any], artifact_id: str | None = None
) -> tuple[str, str, str | None] | None:
    artifacts = asset.get("derived_artifacts")
    if not isinstance(artifacts, list):
        return None
    preferred_kinds = {"transcript", "description", "normalized_text", "ocr"}
    candidates: list[tuple[int, Mapping[str, Any]]] = []
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, Mapping):
            continue
        current_id = _text(artifact.get("artifact_id")) or None
        if artifact_id is not None and current_id != artifact_id:
            continue
        kind = _text(artifact.get("kind")).casefold()
        priority = 0 if kind in preferred_kinds else 1
        candidates.append((priority * 1000 + index, artifact))
    for _, artifact in sorted(candidates, key=lambda item: item[0]):
        for key in ("text", "derived_text", "content"):
            value = artifact.get(key)
            if isinstance(value, str) and value.strip():
                return value, "derived_text", _text(artifact.get("artifact_id")) or None
    return None


def resolve_boss_asset_text(
    manifest: Mapping[str, Any],
    *,
    asset_id: str | None = None,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    """Resolve exact text for a BOSS initial post without semantic extraction.

    Text assets use their canonical ``content`` verbatim.  Other assets may
    use a text-bearing manifest artifact or a user-supplied artifact already
    stored in the BOSS asset catalog.  MIME type and filename alone never
    count as usable content.
    """

    assets = _manifest_assets(manifest)
    if asset_id is not None and not isinstance(asset_id, str):
        raise BossSimulationValidationError({"asset_id": "must be a string"})
    candidates = assets
    if asset_id is not None:
        candidates = [asset for asset in assets if _text(asset.get("asset_id")) == asset_id]
        if not candidates:
            raise BossSimulationValidationError({"asset_id": "does not match an asset in the scenario"})

    # Prefer a requested asset, otherwise choose the first usable asset in
    # canonical manifest order.  This allows a scenario to retain technical
    # media alongside a usable text asset without making preparation fragile.
    missing_asset_ids: list[str] = []
    for asset in candidates:
        current_asset_id = _text(asset.get("asset_id"))
        kind = _text(asset.get("kind") or asset.get("type")).casefold()
        if kind == "text":
            content = asset.get("content")
            if isinstance(content, str) and content.strip():
                return {
                    "asset": asset,
                    "asset_id": current_asset_id,
                    "content": content,
                    "content_source_kind": "asset_content",
                    "artifact_id": None,
                }

        derived = _text_from_derived_artifacts(asset, artifact_id=artifact_id)
        if derived is not None:
            content, source_kind, selected_artifact_id = derived
            return {
                "asset": asset,
                "asset_id": current_asset_id,
                "content": content,
                "content_source_kind": source_kind,
                "artifact_id": selected_artifact_id,
            }

        # An uploaded catalog asset stores artifact text separately from the
        # scenario manifest.  Import lazily so deterministic profile tests do
        # not initialize any external service or require a configured root.
        if current_asset_id and is_asset_id(current_asset_id):
            try:
                from .boss_assets import BossAssetStore

                catalog_asset = BossAssetStore().get(current_asset_id)
                catalog_artifacts = catalog_asset.get("artifacts", []) if catalog_asset else []
                for artifact in catalog_artifacts:
                    if not isinstance(artifact, Mapping):
                        continue
                    candidate_id = _text(artifact.get("artifact_id"))
                    if artifact_id is not None and candidate_id != artifact_id:
                        continue
                    if _text(artifact.get("kind")).casefold() not in {
                        "transcript",
                        "description",
                        "normalized_text",
                        "ocr",
                    }:
                        continue
                    try:
                        _, text = BossAssetStore().get_artifact(current_asset_id, candidate_id)
                    except Exception:
                        continue
                    if text.strip():
                        return {
                            "asset": asset,
                            "asset_id": current_asset_id,
                            "content": text,
                            "content_source_kind": "user_supplied_artifact",
                            "artifact_id": candidate_id,
                        }
            except Exception:
                # A missing or malformed catalog record is reported below as
                # a normal usable-content validation error, never as a stack
                # trace or a filesystem detail.
                pass
        missing_asset_ids.append(current_asset_id or f"assets[{len(missing_asset_ids)}]")

    selected = asset_id or (missing_asset_ids[0] if missing_asset_ids else "asset")
    raise BossSimulationValidationError(
        {"asset.content": f"usable text or transcript/description artifact is required for {selected}"},
        message="BOSS simulation requires usable asset text",
    )


def _derived_seed(scenario_id: str, manifest_hash: str, asset_id: str, content: str) -> int:
    digest = hashlib.sha256(
        "|".join((scenario_id, manifest_hash, asset_id, content)).encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big", signed=False) % (2**63 - 1)


def _simulation_id(
    scenario_id: str,
    manifest_hash: str,
    asset_id: str,
    seed: int,
    profiles: Sequence[BossAgentProfile],
) -> str:
    identity = {
        "scenario_id": scenario_id,
        "manifest_sha256": manifest_hash,
        "asset_id": asset_id,
        "seed": seed,
        "profiles": [profile.profile_id for profile in profiles],
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"boss_simulation_{hashlib.sha256(encoded.encode('utf-8')).hexdigest()[:24]}"


def build_boss_simulation_config(
    manifest: Mapping[str, Any],
    profiles: Sequence[BossAgentProfile],
    *,
    asset_id: str | None = None,
    asset_content: str | None = None,
    content_source_kind: str = "asset_content",
    artifact_id: str | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """Build a deterministic, runner-compatible BOSS simulation config.

    The initial post is always authored by the brand account (agent ``0``)
    and contains the exact resolved text.  No generated paraphrase, LLM
    setting, timestamp, or random identifier is introduced here.
    """

    scenario_id, brand, _ = _manifest_sections(manifest)
    selected_profiles = _as_profiles(profiles)
    if not selected_profiles or selected_profiles[0].agent_id != 0:
        raise BossSimulationValidationError({"profiles": "must begin with brand agent id 0"})
    manifest_hash = manifest_sha256(manifest)
    if asset_content is None:
        resolved = resolve_boss_asset_text(manifest, asset_id=asset_id, artifact_id=artifact_id)
        asset_content = resolved["content"]
        asset_id = resolved["asset_id"]
        content_source_kind = resolved["content_source_kind"]
        artifact_id = resolved.get("artifact_id")
    if not isinstance(asset_content, str) or not asset_content.strip():
        raise BossSimulationValidationError({"asset.content": "must contain usable text"})

    assets = _manifest_assets(manifest)
    selected_asset = next((item for item in assets if _text(item.get("asset_id")) == asset_id), None)
    if selected_asset is None:
        if asset_id is None:
            selected_asset = assets[0]
            asset_id = _text(selected_asset.get("asset_id"))
        else:
            raise BossSimulationValidationError({"asset_id": "does not match an asset in the scenario"})
    asset_id = _text(asset_id) or "asset"

    run_config = manifest.get("run_config")
    supplied_seed = run_config.get("seed") if isinstance(run_config, Mapping) else None
    selected_seed = seed if seed is not None else supplied_seed
    if selected_seed is None:
        selected_seed = _derived_seed(scenario_id, manifest_hash, asset_id, asset_content)
    if not isinstance(selected_seed, int) or isinstance(selected_seed, bool):
        raise BossSimulationValidationError({"seed": "must be an integer"})
    if not -(2**63) <= selected_seed <= 2**63 - 1:
        raise BossSimulationValidationError({"seed": "must be a signed 64-bit integer"})

    audience_agent_ids = [profile.agent_id for profile in selected_profiles if profile.account_kind == "audience"]
    simulation_id = _simulation_id(scenario_id, manifest_hash, asset_id, selected_seed, selected_profiles)
    content_hash = hashlib.sha256(asset_content.encode("utf-8")).hexdigest()
    agent_configs = []
    for profile in selected_profiles:
        is_brand = profile.account_kind == "brand"
        agent_configs.append(
            {
                "agent_id": profile.agent_id,
                "entity_uuid": profile.profile_id,
                "entity_name": profile.name,
                "entity_type": "BrandAccount" if is_brand else "AudiencePersona",
                "activity_level": 0.35 if is_brand else 0.7,
                "posts_per_hour": 0.2 if is_brand else 0.5,
                "comments_per_hour": 0.2 if is_brand else 1.0,
                "active_hours": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
                "response_delay_min": 5 if is_brand else 2,
                "response_delay_max": 60 if is_brand else 20,
                "sentiment_bias": 0.0,
                "stance": "observer" if is_brand else "neutral",
                "influence_weight": 2.0 if is_brand else 1.0,
            }
        )

    initial_post: dict[str, Any] = {
        "poster_agent_id": 0,
        "content": asset_content,
        "asset_id": asset_id,
        "content_source_kind": content_source_kind,
    }
    if artifact_id:
        initial_post["artifact_id"] = artifact_id

    return {
        "schema_version": BOSS_SIMULATION_SCHEMA_VERSION,
        "simulation_id": simulation_id,
        "source_kind": BOSS_SOURCE_KIND,
        "scenario_id": scenario_id,
        "manifest_sha256": manifest_hash,
        "asset_id": asset_id,
        "asset_sha256": _text(selected_asset.get("sha256")) or content_hash,
        "content_sha256": content_hash,
        "timezone": BOSS_TIMEZONE,
        "seed": selected_seed,
        "brand_agent_id": 0,
        "audience_agent_ids": audience_agent_ids,
        "agent_configs": agent_configs,
        "time_config": {
            "timezone": BOSS_TIMEZONE,
            "total_simulation_hours": 72,
            "minutes_per_round": 60,
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8],
            "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        },
        "event_config": {
            "initial_posts": [initial_post],
            "scheduled_events": [],
            "hot_topics": [],
            "narrative_direction": _text(brand.get("positioning")),
        },
        "twitter_config": {"platform": "twitter"},
        "reddit_config": {"platform": "reddit"},
        "llm_used": False,
        "zep_used": False,
        "source_metadata": {
            "scenario_id": scenario_id,
            "manifest_sha256": manifest_hash,
            "asset_id": asset_id,
            "content_source_kind": content_source_kind,
        },
    }


__all__ = [
    "BOSS_PROFILE_SCHEMA_VERSION",
    "BOSS_SIMULATION_SCHEMA_VERSION",
    "BOSS_SOURCE_KIND",
    "BOSS_TIMEZONE",
    "BossAgentProfile",
    "BossSimulationValidationError",
    "build_boss_simulation_config",
    "materialize_boss_personas",
    "materialize_boss_profiles",
    "profile_dicts",
    "resolve_boss_asset_text",
    "serialize_reddit_json",
    "serialize_reddit_profiles",
    "serialize_twitter_csv",
    "serialize_twitter_profiles",
    "serialize_twitter_profiles_csv",
]
