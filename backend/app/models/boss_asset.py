"""Validation primitives for the BOSS media asset catalog.

The catalog intentionally uses plain JSON records rather than an ORM.  This
module keeps the identifiers, storage keys, and artifact kinds constrained so
the filesystem service can never turn request data into an arbitrary path.
"""

from __future__ import annotations

import copy
import re
import uuid
from dataclasses import dataclass
from typing import Any


ASSET_SCHEMA_VERSION = "boss.asset.v1"
ARTIFACT_SCHEMA_VERSION = "boss.artifact.v1"
ASSET_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
ARTIFACT_ID_PATTERN = ASSET_ID_PATTERN
ARTIFACT_KINDS = frozenset({"transcript", "ocr", "description", "normalized_text"})
ASSET_KINDS = frozenset({"text", "document", "image", "audio", "video"})


class BossAssetValidationError(ValueError):
    """A safe, structured validation error for asset API requests."""

    def __init__(self, fields: dict[str, str]):
        self.fields = fields
        super().__init__("BOSS asset validation failed")


class BossAssetNotFound(LookupError):
    """Raised internally when an asset or artifact is not present."""


def is_asset_id(value: Any) -> bool:
    """Return whether ``value`` is a canonical lowercase UUID string."""

    return isinstance(value, str) and ASSET_ID_PATTERN.fullmatch(value) is not None


def new_asset_id() -> str:
    return str(uuid.uuid4())


def new_artifact_id() -> str:
    return str(uuid.uuid4())


def is_safe_storage_key(value: Any) -> bool:
    """Validate a root-relative POSIX storage key without touching the disk."""

    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if value.startswith("/") or value.startswith("~"):
        return False
    parts = value.split("/")
    return all(part not in {"", ".", ".."} for part in parts)


@dataclass(frozen=True)
class BossAsset:
    """Small typed wrapper for a persisted, JSON-safe asset record."""

    record: dict[str, Any]

    @property
    def asset_id(self) -> str:
        return self.record["asset_id"]

    def to_dict(self) -> dict[str, Any]:
        """Return a copy so callers cannot mutate the stored representation."""

        return copy.deepcopy(self.record)


__all__ = [
    "ARTIFACT_KINDS",
    "ARTIFACT_SCHEMA_VERSION",
    "ASSET_ID_PATTERN",
    "ASSET_KINDS",
    "ASSET_SCHEMA_VERSION",
    "BossAsset",
    "BossAssetNotFound",
    "BossAssetValidationError",
    "is_asset_id",
    "is_safe_storage_key",
    "new_artifact_id",
    "new_asset_id",
]
