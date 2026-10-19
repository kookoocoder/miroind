"""Local technical probe for BOSS audio and video files.

This module reads duration, size, and codec facts with ffprobe. It does not
transcribe, OCR, or describe scenes. A missing tool or unreadable file
returns no facts so the caller can keep the uploaded_unparsed state.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable


PROBE_TIMEOUT_SECONDS = 15
_CODEC_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._+-")


def parse_ffprobe_document(payload: Any) -> dict[str, Any] | None:
    """Return short technical facts from an ffprobe JSON document."""

    if not isinstance(payload, dict):
        return None
    streams = payload.get("streams")
    if not isinstance(streams, list):
        streams = []
    video = next((item for item in streams if isinstance(item, dict) and item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if isinstance(item, dict) and item.get("codec_type") == "audio"), None)
    container = payload.get("format") if isinstance(payload.get("format"), dict) else {}

    facts: dict[str, Any] = {
        "status": "technical_parsed",
        "probe_tool": "ffprobe",
        "has_video": video is not None,
        "has_audio": audio is not None,
    }
    duration = _duration(container.get("duration"))
    if duration is None and video is not None:
        duration = _duration(video.get("duration"))
    if duration is None and audio is not None:
        duration = _duration(audio.get("duration"))
    if duration is not None:
        facts["duration_seconds"] = duration
    if video is not None:
        width = _positive_int(video.get("width"))
        height = _positive_int(video.get("height"))
        codec = _codec(video.get("codec_name"))
        frame_rate = _frame_rate(video.get("avg_frame_rate")) or _frame_rate(video.get("r_frame_rate"))
        if width is not None:
            facts["width"] = width
        if height is not None:
            facts["height"] = height
        if codec is not None:
            facts["video_codec"] = codec
        if frame_rate is not None:
            facts["frame_rate"] = frame_rate
    if audio is not None:
        codec = _codec(audio.get("codec_name"))
        if codec is not None:
            facts["audio_codec"] = codec
    if not facts["has_video"] and not facts["has_audio"] and "duration_seconds" not in facts:
        return None
    return facts


def probe_local_media(
    path: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    executable: str | None = None,
) -> dict[str, Any] | None:
    """Probe one local file. URLs and missing binaries yield no facts."""

    if not isinstance(path, Path):
        return None
    location = path.as_posix()
    if "://" in location or location.startswith("~"):
        return None
    try:
        if not path.is_file():
            return None
    except OSError:
        return None

    binary = executable if executable is not None else shutil.which("ffprobe")
    if not binary:
        return None
    command = [
        binary,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    run = runner or subprocess.run
    try:
        completed = run(
            command,
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if getattr(completed, "returncode", 1) != 0:
        return None
    try:
        payload = json.loads(completed.stdout or "")
    except json.JSONDecodeError:
        return None
    return parse_ffprobe_document(payload)


def _duration(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0 or number > 60 * 60 * 24:
        return None
    return round(number, 3)


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        try:
            if isinstance(value, str) and value.isdigit():
                value = int(value)
            else:
                return None
        except (TypeError, ValueError):
            return None
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 100_000:
        return None
    return value


def _codec(value: Any) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 32:
        return None
    if any(character not in _CODEC_CHARS for character in value):
        return None
    return value


def _frame_rate(value: Any) -> float | None:
    if not isinstance(value, str) or "/" not in value:
        return _duration(value) if not isinstance(value, str) else None
    numerator, denominator = value.split("/", 1)
    try:
        rate = float(numerator) / float(denominator)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    if not math.isfinite(rate) or not 0 < rate <= 1000:
        return None
    return round(rate, 3)


__all__ = ["parse_ffprobe_document", "probe_local_media"]
