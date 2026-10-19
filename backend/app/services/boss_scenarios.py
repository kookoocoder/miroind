"""Safe filesystem persistence for versioned BOSS scenario manifests."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ..config import Config
from ..models.boss_scenario import SCENARIO_ID_PATTERN, normalize_manifest


class BossScenarioNotFound(LookupError):
    """Raised when a scenario or revision target does not exist."""


class BossScenarioAlreadyExists(FileExistsError):
    """Raised when creation would replace an existing scenario."""


class BossScenarioStore:
    """Repository for scenario manifests and immutable revision snapshots."""

    def __init__(self, root: str | os.PathLike[str] | None = None):
        self.root = Path(root) if root is not None else Path(Config.BOSS_SCENARIOS_DIR)

    @staticmethod
    def _validate_scenario_id(scenario_id: str) -> bool:
        return isinstance(scenario_id, str) and SCENARIO_ID_PATTERN.fullmatch(scenario_id) is not None

    def _scenario_dir(self, scenario_id: str) -> Path:
        if not self._validate_scenario_id(scenario_id):
            raise BossScenarioNotFound("scenario not found")
        return self.root / scenario_id

    def create(self, payload: Any) -> dict[str, Any]:
        """Normalize and atomically create revision one."""

        manifest = normalize_manifest(payload, revision=1)
        scenario_dir = self._scenario_dir(manifest["scenario_id"])
        if scenario_dir.exists():
            raise BossScenarioAlreadyExists("scenario already exists")
        revisions_dir = scenario_dir / "revisions"
        try:
            revisions_dir.mkdir(parents=True, exist_ok=False)
            self._atomic_write_json(scenario_dir / "manifest.json", manifest)
            self._atomic_write_json(revisions_dir / "1.json", manifest)
        except Exception:
            shutil.rmtree(scenario_dir, ignore_errors=True)
            raise
        return manifest

    def get(self, scenario_id: str) -> dict[str, Any] | None:
        """Read the current manifest, returning ``None`` for unsafe/missing IDs."""

        if not self._validate_scenario_id(scenario_id):
            return None
        return self._read_json(self.root / scenario_id / "manifest.json", scenario_id)

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent valid scenario manifests without exposing filesystem paths."""

        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if not self.root.exists():
            return []
        candidates: list[tuple[int, dict[str, Any]]] = []
        for scenario_dir in self.root.iterdir():
            if not scenario_dir.is_dir() or not self._validate_scenario_id(scenario_dir.name):
                continue
            manifest = self.get(scenario_dir.name)
            if manifest is None:
                continue
            try:
                sort_key = (scenario_dir / "manifest.json").stat().st_mtime_ns
            except OSError:
                sort_key = 0
            candidates.append((sort_key, manifest))
        candidates.sort(key=lambda item: item[0], reverse=True)
        return [manifest for _, manifest in candidates[:limit]]

    def create_revision(self, scenario_id: str, payload: Any) -> dict[str, Any]:
        """Create the next revision and atomically replace the current pointer."""

        if not self._validate_scenario_id(scenario_id):
            raise BossScenarioNotFound("scenario not found")
        scenario_dir = self._scenario_dir(scenario_id)
        current = self.get(scenario_id)
        if current is None or not scenario_dir.is_dir():
            raise BossScenarioNotFound("scenario not found")
        next_revision = current.get("revision", 0) + 1
        manifest = normalize_manifest(payload, scenario_id=scenario_id, revision=next_revision)
        revisions_dir = scenario_dir / "revisions"
        revisions_dir.mkdir(parents=True, exist_ok=True)
        self._atomic_write_json(revisions_dir / f"{next_revision}.json", manifest)
        self._atomic_write_json(scenario_dir / "manifest.json", manifest)
        return manifest

    def get_revision(self, scenario_id: str, revision: int) -> dict[str, Any] | None:
        if not self._validate_scenario_id(scenario_id):
            return None
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            return None
        return self._read_json(
            self.root / scenario_id / "revisions" / f"{revision}.json",
            scenario_id,
        )

    def get_graph_record(self, scenario_id: str) -> dict[str, Any] | None:
        """Read the derived graph record without exposing its filesystem path."""

        if not self._validate_scenario_id(scenario_id):
            return None
        record = self._read_json(
            self.root / scenario_id / "graph.json",
            scenario_id,
            require_schema=False,
        )
        if record is None or record.get("source_kind") != "boss_scenario":
            return None
        return record

    def save_graph_record(self, scenario_id: str, record: Any) -> dict[str, Any]:
        """Atomically persist a safe, derived graph record under a scenario."""

        if not self._validate_scenario_id(scenario_id):
            raise BossScenarioNotFound("scenario not found")
        if not isinstance(record, dict) or record.get("scenario_id") != scenario_id:
            raise ValueError("invalid BOSS graph record")
        if record.get("source_kind") != "boss_scenario":
            raise ValueError("invalid BOSS graph record source")
        if not (self.root / scenario_id / "manifest.json").is_file():
            raise BossScenarioNotFound("scenario not found")
        self._atomic_write_json(self.root / scenario_id / "graph.json", record)
        return record

    def _read_json(
        self,
        path: Path,
        scenario_id: str,
        *,
        require_schema: bool = True,
    ) -> dict[str, Any] | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        if not isinstance(value, dict):
            return None
        if value.get("scenario_id") != scenario_id:
            return None
        if require_schema and value.get("schema_version") != "boss.scenario.v1":
            return None
        return value

    @staticmethod
    def _atomic_write_json(destination: Path, value: dict[str, Any]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=str(destination.parent),
        )
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise


# Service naming keeps the repository easy to discover for API callers and
# leaves a concise alias for code that prefers the repository terminology.
BossScenarioService = BossScenarioStore


__all__ = [
    "BossScenarioAlreadyExists",
    "BossScenarioNotFound",
    "BossScenarioService",
    "BossScenarioStore",
]
