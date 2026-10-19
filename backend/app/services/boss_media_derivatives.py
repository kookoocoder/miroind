"""Local ffmpeg derivatives for BOSS audio and video assets.

This module turns a technically parsed media file into a small set of JPEG
keyframes and one audio extract.  Files stay on disk; the returned artifact
records contain only hashes and storage keys.  Missing tools and failed
extractions return warnings instead of inventing derivative records.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

from ..config import Config
from ..models.boss_asset import ARTIFACT_SCHEMA_VERSION, new_artifact_id


DERIVATIVE_PROCESSOR = "ffmpeg"
DERIVATIVE_TIMEOUT_SECONDS = 30
DEFAULT_MAX_KEYFRAMES = 6
DEFAULT_MAX_KEYFRAME_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_AUDIO_EXTRACT_BYTES = 25 * 1024 * 1024
KEYFRAME_MAX_WIDTH = 1280


def keyframe_timestamps(facts: Any) -> list[float]:
    """Return evenly spaced timestamps for a parsed video, at most the cap."""

    if not isinstance(facts, dict) or not facts.get("has_video"):
        return []
    maximum = _config_positive_int("BOSS_MAX_KEYFRAMES", DEFAULT_MAX_KEYFRAMES)
    duration = facts.get("duration_seconds")
    if (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(duration)
        or duration <= 0
    ):
        return [0.0]
    count = min(maximum, max(1, math.ceil(duration)))
    return [round((index + 0.5) * duration / count, 3) for index in range(count)]


def generate_media_derivatives(
    content_path: Path,
    asset_dir: Path,
    root: Path,
    *,
    asset_id: str,
    facts: dict[str, Any],
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    executable: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Extract keyframes and audio, returning records and safe warnings.

    The function never raises for a missing or failing ffmpeg.  Callers keep
    the existing ``technical_parsed`` asset record and surface the warnings.
    """

    timestamps = keyframe_timestamps(facts)
    wants_audio = bool(isinstance(facts, dict) and facts.get("has_audio"))
    if not timestamps and not wants_audio:
        return [], []

    binary = executable if executable is not None else shutil.which("ffmpeg")
    if not binary:
        return [], [
            "ffmpeg is not installed; keyframes and audio extract were not generated."
        ]

    artifacts_dir = asset_dir / "artifacts"
    artifacts_dir.mkdir(mode=0o750, exist_ok=True)
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    keyframe_limit = _config_positive_int(
        "BOSS_MAX_KEYFRAME_BYTES", DEFAULT_MAX_KEYFRAME_BYTES
    )
    audio_limit = _config_positive_int(
        "BOSS_MAX_AUDIO_EXTRACT_BYTES", DEFAULT_MAX_AUDIO_EXTRACT_BYTES
    )

    for timestamp in timestamps:
        artifact_id = new_artifact_id()
        target = artifacts_dir / f"{artifact_id}.jpg"
        command = _keyframe_command(binary, content_path, target, timestamp, keyframe_limit)
        if not _run_ffmpeg(command, runner):
            _discard(target)
            warnings.append(
                f"ffmpeg could not extract a keyframe at {timestamp:.3f}s; "
                "no keyframe artifact was stored."
            )
            continue
        record = _record_for_file(
            target,
            root=root,
            asset_id=asset_id,
            artifact_id=artifact_id,
            kind="keyframe",
            timestamp=timestamp,
            mime_type="image/jpeg",
            maximum_bytes=keyframe_limit,
        )
        if record is None:
            _discard(target)
            warnings.append(
                f"ffmpeg keyframe at {timestamp:.3f}s exceeded the file-size cap; "
                "no keyframe artifact was stored."
            )
            continue
        try:
            _atomic_write_json(artifacts_dir / f"{artifact_id}.json", record)
        except Exception:
            _discard(target)
            warnings.append("A keyframe could not be recorded; no artifact was stored.")
            continue
        records.append(record)

    if wants_audio:
        artifact_id = new_artifact_id()
        target = artifacts_dir / f"{artifact_id}.m4a"
        command = _audio_command(binary, content_path, target, audio_limit)
        if not _run_ffmpeg(command, runner):
            _discard(target)
            warnings.append(
                "ffmpeg could not extract audio; no audio_extract artifact was stored."
            )
        else:
            record = _record_for_file(
                target,
                root=root,
                asset_id=asset_id,
                artifact_id=artifact_id,
                kind="audio_extract",
                timestamp=0.0,
                mime_type="audio/mp4",
                maximum_bytes=audio_limit,
            )
            if record is None:
                _discard(target)
                warnings.append(
                    "the audio extract exceeded the file-size cap; "
                    "no audio_extract artifact was stored."
                )
            else:
                try:
                    _atomic_write_json(artifacts_dir / f"{artifact_id}.json", record)
                except Exception:
                    _discard(target)
                    warnings.append(
                        "An audio extract could not be recorded; no artifact was stored."
                    )
                else:
                    records.append(record)

    return records, warnings


def _keyframe_command(
    binary: str,
    source: Path,
    target: Path,
    timestamp: float,
    maximum_bytes: int,
) -> list[str]:
    return [
        binary,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        f"scale='min({KEYFRAME_MAX_WIDTH},iw)':-2",
        "-q:v",
        "5",
        "-fs",
        str(maximum_bytes),
        str(target),
    ]


def _audio_command(
    binary: str,
    source: Path,
    target: Path,
    maximum_bytes: int,
) -> list[str]:
    return [
        binary,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-map",
        "0:a:0",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        "-fs",
        str(maximum_bytes),
        str(target),
    ]


def _run_ffmpeg(
    command: list[str],
    runner: Callable[..., subprocess.CompletedProcess[str]] | None,
) -> bool:
    run = runner or subprocess.run
    try:
        completed = run(
            command,
            capture_output=True,
            text=True,
            timeout=DERIVATIVE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return getattr(completed, "returncode", 1) == 0


def _record_for_file(
    path: Path,
    *,
    root: Path,
    asset_id: str,
    artifact_id: str,
    kind: str,
    timestamp: float,
    mime_type: str,
    maximum_bytes: int,
) -> dict[str, Any] | None:
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size <= 0 or size > maximum_bytes:
        return None
    try:
        storage_key = path.relative_to(root).as_posix()
    except ValueError:
        return None
    digest = _sha256_file(path)
    if digest is None:
        return None
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "source_asset_id": asset_id,
        "kind": kind,
        "processor": DERIVATIVE_PROCESSOR,
        "processor_version": DERIVATIVE_PROCESSOR,
        "status": "derived",
        "warnings": [],
        "storage_key": storage_key,
        "mime_type": mime_type,
        "timestamp": timestamp,
        "timestamp_seconds": timestamp,
        "sha256": digest,
        "size_bytes": size,
    }


def _sha256_file(path: Path) -> str | None:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _discard(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _config_positive_int(name: str, default: int) -> int:
    value = getattr(Config, name, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return default
    return value


def _atomic_write_json(destination: Path, value: dict[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
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


__all__ = [
    "DERIVATIVE_PROCESSOR",
    "generate_media_derivatives",
    "keyframe_timestamps",
]
