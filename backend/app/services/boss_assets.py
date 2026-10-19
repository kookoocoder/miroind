"""Safe local storage and technical parsing for BOSS media assets.

This service does not call a model, OCR engine, or document understanding
library.  Audio and video may be probed with local ffprobe for duration and
codec facts, then locally reduced with ffmpeg to keyframes and one audio
extract.  If either tool fails, the file stays uploaded_unparsed or
technical_parsed with a warning.  User supplied text artifacts stay separate
from JSON metadata.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import tempfile
import zipfile
from pathlib import Path
from typing import Any, BinaryIO

from werkzeug.datastructures import FileStorage

from ..config import Config
from .boss_media_derivatives import generate_media_derivatives
from .boss_media_probe import probe_local_media
from ..models.boss_asset import (
    ARTIFACT_KINDS,
    ARTIFACT_SCHEMA_VERSION,
    ASSET_KINDS,
    ASSET_SCHEMA_VERSION,
    BossAssetNotFound,
    BossAssetValidationError,
    is_asset_id,
    is_safe_storage_key,
    new_artifact_id,
    new_asset_id,
)
from ..models.boss_scenario import SCENARIO_ID_PATTERN


MAX_FILENAME_BYTES = 255
MAX_ARTIFACT_TEXT_BYTES = 10 * 1024 * 1024
MAX_SOURCE_METADATA_BYTES = 32 * 1024
TEXT_EXTENSIONS = {
    "txt": "text/plain",
    "text": "text/plain",
    "md": "text/markdown",
    "markdown": "text/markdown",
    "csv": "text/csv",
    "tsv": "text/tab-separated-values",
    "html": "text/html",
    "htm": "text/html",
    "xml": "application/xml",
    "json": "application/json",
    "yaml": "application/yaml",
    "yml": "application/yaml",
    "log": "text/plain",
}
DOCUMENT_EXTENSIONS = {
    "pdf": ("application/pdf", "document"),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "document",
    ),
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "document",
    ),
    "pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "document",
    ),
}
MIME_ALIASES = {
    "image/jpg": "image/jpeg",
    "audio/x-wav": "audio/wav",
    "audio/wave": "audio/wav",
    "application/x-pdf": "application/pdf",
}
GENERIC_MIMES = {"", "application/octet-stream", "binary/octet-stream"}
SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


class BossAssetTooLarge(BossAssetValidationError):
    """Raised when the streamed upload exceeds the configured byte limit."""


class BossAssetUnsupportedMedia(BossAssetValidationError):
    """Raised when bytes and declared upload metadata do not identify a safe type."""


def _canonical_mime(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    mime = value.split(";", 1)[0].strip().lower()
    return MIME_ALIASES.get(mime, mime)


def _extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix if re.fullmatch(r"[a-z0-9]{1,16}", suffix or "") else ""


def _kind_for_mime(mime: str) -> str | None:
    if mime.startswith("text/") or mime in {
        "application/json",
        "application/xml",
        "application/yaml",
        "application/rtf",
    }:
        return "text"
    if mime == "application/pdf" or mime.startswith(
        "application/vnd.openxmlformats-officedocument."
    ):
        return "document"
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("audio/"):
        return "audio"
    if mime.startswith("video/"):
        return "video"
    return None


def _is_text_bytes(data: bytes) -> bool:
    """Accept UTF text while rejecting binary bytes masquerading as text."""

    if not data:
        return True
    encodings = ("utf-8-sig", "utf-16", "utf-32")
    for encoding in encodings:
        try:
            decoded = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if any(ord(char) < 32 and char not in "\t\n\r\f\b" for char in decoded):
            return False
        return True
    return False


def _encoding_hint(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if data.startswith(b"\xff\xfe\x00\x00"):
        return "utf-32-le"
    if data.startswith(b"\x00\x00\xfe\xff"):
        return "utf-32-be"
    if data.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if data.startswith(b"\xfe\xff"):
        return "utf-16-be"
    try:
        data.decode("ascii")
    except UnicodeDecodeError:
        return "utf-8"
    return "ascii"


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    if not width or not height:
        return None
    return width, height


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    index = 2
    while index + 4 <= len(data):
        while index < len(data) and data[index] != 0xFF:
            index += 1
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            break
        marker = data[index]
        index += 1
        if marker in {0xD8, 0xD9}:
            continue
        if marker == 0xDA:
            break
        if index + 2 > len(data):
            break
        segment_length = struct.unpack(">H", data[index : index + 2])[0]
        if segment_length < 2 or index + segment_length > len(data):
            break
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        } and segment_length >= 7:
            height, width = struct.unpack(">HH", data[index + 3 : index + 7])
            if width and height:
                return width, height
        index += segment_length
    return None


def _safe_filename(filename: Any) -> str:
    if not isinstance(filename, str):
        raise BossAssetValidationError({"file": "filename is required"})
    filename = filename.strip()
    if (
        not filename
        or filename in {".", ".."}
        or "\x00" in filename
        or "/" in filename
        or "\\" in filename
        or any(ord(char) < 32 or ord(char) == 127 for char in filename)
        or len(filename.encode("utf-8")) > MAX_FILENAME_BYTES
    ):
        raise BossAssetValidationError({"file": "filename must be a safe basename"})
    return filename


def _safe_scenario_id(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or SCENARIO_ID_PATTERN.fullmatch(value) is None:
        raise BossAssetValidationError(
            {"scenario_id": "must match scenario_<24 lowercase hex characters>"}
        )
    return value


def _declared_type_is_compatible(declared: str, detected: str) -> bool:
    if declared in GENERIC_MIMES:
        return True
    if declared == detected:
        return True
    # Browsers and clients sometimes use a broad media MIME.  It is safe to
    # retain it as a declaration when the inspected bytes stay in that family.
    return declared.split("/", 1)[0] == detected.split("/", 1)[0] and declared in {
        "text/plain",
        "image/*",
        "audio/*",
        "video/*",
    }


def _magic_type(data: bytes, filename: str, path: Path | None = None) -> dict[str, Any] | None:
    """Identify common formats from signatures, never from a suffix alone."""

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        dimensions = _png_dimensions(data)
        result: dict[str, Any] = {
            "mime_type": "image/png",
            "extension": "png",
            "kind": "image",
            "technical_metadata": {},
        }
        if dimensions is not None:
            result["technical_metadata"] = {"width": dimensions[0], "height": dimensions[1]}
        else:
            result["warnings"] = ["PNG dimensions could not be read from the available header."]
        return result
    if data.startswith(b"\xff\xd8\xff"):
        dimensions = _jpeg_dimensions(data)
        result: dict[str, Any] = {
            "mime_type": "image/jpeg",
            "extension": "jpg",
            "kind": "image",
            "technical_metadata": {},
        }
        if dimensions is not None:
            result["technical_metadata"] = {"width": dimensions[0], "height": dimensions[1]}
        else:
            result["warnings"] = ["JPEG dimensions could not be read from the available markers."]
        return result
    if data.startswith((b"GIF87a", b"GIF89a")) and len(data) >= 10:
        width, height = struct.unpack("<HH", data[6:10])
        if width and height:
            return {
                "mime_type": "image/gif",
                "extension": "gif",
                "kind": "image",
                "technical_metadata": {"width": width, "height": height},
            }
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return {
            "mime_type": "image/webp",
            "extension": "webp",
            "kind": "image",
            "technical_metadata": {},
            "warnings": ["WEBP dimensions were not parsed by the stdlib boundary."],
        }
    if data.startswith(b"%PDF-"):
        return {
            "mime_type": "application/pdf",
            "extension": "pdf",
            "kind": "document",
            "technical_metadata": {},
        }
    if data.startswith(b"PK\x03\x04"):
        extension = _extension(filename)
        office_type = DOCUMENT_EXTENSIONS.get(extension)
        if office_type and path is not None and zipfile.is_zipfile(path):
            return {
                "mime_type": office_type[0],
                "extension": extension,
                "kind": "document",
                "technical_metadata": {"container": "zip"},
            }
    if data.startswith(b"ID3") or data[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}:
        return {
            "mime_type": "audio/mpeg",
            "extension": "mp3",
            "kind": "audio",
            "technical_metadata": {"status": "uploaded_unparsed"},
            "warnings": [
                "ffprobe/semantic parsing is not installed; audio was stored uploaded_unparsed."
            ],
        }
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WAVE":
        return {
            "mime_type": "audio/wav",
            "extension": "wav",
            "kind": "audio",
            "technical_metadata": {"status": "uploaded_unparsed"},
            "warnings": [
                "ffprobe/semantic parsing is not installed; audio was stored uploaded_unparsed."
            ],
        }
    if data.startswith(b"OggS"):
        return {
            "mime_type": "audio/ogg",
            "extension": "ogg",
            "kind": "audio",
            "technical_metadata": {"status": "uploaded_unparsed"},
            "warnings": [
                "ffprobe/semantic parsing is not installed; audio was stored uploaded_unparsed."
            ],
        }
    if data.startswith(b"fLaC"):
        return {
            "mime_type": "audio/flac",
            "extension": "flac",
            "kind": "audio",
            "technical_metadata": {"status": "uploaded_unparsed"},
            "warnings": [
                "ffprobe/semantic parsing is not installed; audio was stored uploaded_unparsed."
            ],
        }
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in {b"qt  ", b"mjp2"}:
            mime = "video/quicktime"
            extension = "mov"
            kind = "video"
        elif brand in {b"M4A ", b"M4B ", b"M4P "}:
            mime = "audio/mp4"
            extension = "m4a"
            kind = "audio"
        elif brand in {b"isom", b"iso2", b"mp41", b"mp42"}:
            mime = "video/mp4"
            extension = "mp4"
            kind = "video"
        else:
            mime = "video/mp4"
            extension = "mp4"
            kind = "video"
        return {
            "mime_type": mime,
            "extension": extension,
            "kind": kind,
            "technical_metadata": {"status": "uploaded_unparsed"},
            "warnings": [
                f"ffprobe/semantic parsing is not installed; {kind} was stored uploaded_unparsed."
            ],
        }
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return {
            "mime_type": "video/webm",
            "extension": "webm",
            "kind": "video",
            "technical_metadata": {"status": "uploaded_unparsed"},
            "warnings": [
                "ffprobe/semantic parsing is not installed; video was stored uploaded_unparsed."
            ],
        }
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"AVI ":
        return {
            "mime_type": "video/x-msvideo",
            "extension": "avi",
            "kind": "video",
            "technical_metadata": {"status": "uploaded_unparsed"},
            "warnings": [
                "ffprobe/semantic parsing is not installed; video was stored uploaded_unparsed."
            ],
        }
    return None


def _technical_for_unparsed(kind: str) -> tuple[str, list[str]]:
    if kind in {"audio", "video"}:
        return "uploaded_unparsed", [
            f"ffprobe/semantic parsing is not installed; {kind} was stored uploaded_unparsed."
        ]
    return "uploaded", []


def _validated_source_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise BossAssetValidationError({"source_metadata": "must be a JSON object"})

    def visit(item: Any, path: str, depth: int = 0) -> Any:
        if depth > 4:
            raise BossAssetValidationError({path: "is nested too deeply"})
        if isinstance(item, dict):
            result: dict[str, Any] = {}
            for key, child in item.items():
                if not isinstance(key, str) or not key or len(key) > 80:
                    raise BossAssetValidationError({path: "contains an invalid key"})
                folded = key.casefold().replace("-", "_")
                child_path = f"{path}.{key}" if path else key
                if any(part in folded for part in SENSITIVE_KEY_PARTS):
                    raise BossAssetValidationError(
                        {child_path: "must not contain credentials or secrets"}
                    )
                result[key] = visit(child, child_path, depth + 1)
            return result
        if isinstance(item, list):
            if len(item) > 50:
                raise BossAssetValidationError({path: "must contain at most 50 items"})
            return [visit(child, f"{path}[{index}]", depth + 1) for index, child in enumerate(item)]
        if isinstance(item, (str, int, float, bool)) or item is None:
            if isinstance(item, str):
                if len(item) > 1000 or "\x00" in item:
                    raise BossAssetValidationError({path: "contains an invalid string"})
                if item.startswith(("/", "~")) or re.match(r"^[A-Za-z]:[\\/]", item):
                    raise BossAssetValidationError({path: "must not contain an absolute path"})
            return item
        raise BossAssetValidationError({path: "must contain JSON-safe values"})

    result = visit(value, "source_metadata")
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > MAX_SOURCE_METADATA_BYTES:
        raise BossAssetValidationError({"source_metadata": "is too large"})
    return result


class BossAssetStore:
    """Filesystem repository for BOSS assets and user-supplied artifacts."""

    def __init__(self, root: str | os.PathLike[str] | None = None):
        self.root = Path(root) if root is not None else Path(Config.BOSS_ASSETS_DIR)

    def _root_path(self, *, create: bool = False) -> Path:
        root = self.root.expanduser().resolve()
        if create:
            root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _asset_dir_name(asset_id: str) -> str:
        if not is_asset_id(asset_id):
            raise BossAssetNotFound("asset not found")
        return asset_id

    def _asset_dir(self, asset_id: str) -> Path:
        root = self._root_path()
        asset_dir = root / self._asset_dir_name(asset_id)
        if asset_dir.is_symlink():
            raise BossAssetNotFound("asset not found")
        try:
            asset_dir.resolve(strict=False).relative_to(root)
        except ValueError as error:
            raise BossAssetNotFound("asset not found") from error
        return asset_dir

    def _safe_record_path(self, storage_key: str) -> Path:
        if not is_safe_storage_key(storage_key):
            raise BossAssetNotFound("asset not found")
        root = self._root_path()
        candidate = (root / Path(storage_key)).resolve(strict=False)
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise BossAssetNotFound("asset not found") from error
        return candidate

    @staticmethod
    def _atomic_write_json(destination: Path, value: dict[str, Any]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
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

    @staticmethod
    def _atomic_write_text(destination: Path, text: str) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent)
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _read_asset_record(self, asset_id: str) -> dict[str, Any] | None:
        if not is_asset_id(asset_id):
            return None
        try:
            asset_dir = self._asset_dir(asset_id)
        except BossAssetNotFound:
            return None
        metadata_path = asset_dir / "metadata.json"
        if metadata_path.is_symlink():
            return None
        try:
            metadata_path.resolve(strict=False).relative_to(asset_dir.resolve(strict=False))
        except ValueError:
            return None
        record = self._read_json(metadata_path)
        if record is None or record.get("asset_id") != asset_id:
            return None
        if record.get("schema_version") != ASSET_SCHEMA_VERSION:
            return None
        if not is_safe_storage_key(record.get("storage_key")):
            return None
        artifacts = record.get("artifacts", [])
        if not isinstance(artifacts, list):
            record["artifacts"] = []
        return record

    def get(self, asset_id: str) -> dict[str, Any] | None:
        """Return metadata only; binary and artifact text never come from this method."""

        return self._read_asset_record(asset_id)

    def upload(self, uploaded: FileStorage, *, scenario_id: str | None = None) -> dict[str, Any]:
        filename = _safe_filename(uploaded.filename if uploaded is not None else None)
        selected_scenario_id = _safe_scenario_id(scenario_id)
        maximum = Config.BOSS_MAX_ASSET_BYTES
        if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 0:
            raise RuntimeError("BOSS_MAX_ASSET_BYTES must be a non-negative integer")

        root = self._root_path(create=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".boss-upload-", suffix=".tmp", dir=str(root))
        temporary_path = Path(temporary_name)
        total = 0
        digest = hashlib.sha256()
        sample = bytearray()
        stream: BinaryIO = uploaded.stream
        try:
            with os.fdopen(descriptor, "wb") as handle:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > maximum:
                        raise BossAssetTooLarge(
                            {"file": f"must be at most {maximum} bytes"}
                        )
                    digest.update(chunk)
                    if len(sample) < 1024 * 1024:
                        sample.extend(chunk[: 1024 * 1024 - len(sample)])
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())

            declared_mime = _canonical_mime(uploaded.mimetype or uploaded.content_type)
            detected = _magic_type(bytes(sample), filename, temporary_path)
            if detected is None:
                ext = _extension(filename)
                extension_mime = TEXT_EXTENSIONS.get(ext)
                if extension_mime and _is_text_bytes(bytes(sample)):
                    detected = {
                        "mime_type": extension_mime,
                        "extension": ext,
                        "kind": "text",
                        "technical_metadata": {
                            "byte_count": total,
                            "encoding_hint": _encoding_hint(bytes(sample)),
                        },
                    }
                elif (
                    declared_mime in Config.BOSS_ALLOWED_MEDIA_MIMES
                    and _kind_for_mime(declared_mime) == "text"
                    and _is_text_bytes(bytes(sample))
                ):
                    detected = {
                        "mime_type": declared_mime,
                        "extension": next(
                            (suffix for suffix, mime in TEXT_EXTENSIONS.items() if mime == declared_mime),
                            "txt",
                        ),
                        "kind": "text",
                        "technical_metadata": {
                            "byte_count": total,
                            "encoding_hint": _encoding_hint(bytes(sample)),
                        },
                    }
                else:
                    if DOCUMENT_EXTENSIONS.get(ext) and not _is_text_bytes(bytes(sample)):
                        detected = None

            if detected is None:
                raise BossAssetUnsupportedMedia(
                    {"file": "content does not match a supported text, document, image, audio, or video type"}
                )
            detected_mime = detected["mime_type"]
            detected_kind = detected["kind"]
            if detected_kind not in ASSET_KINDS or detected_mime not in Config.BOSS_ALLOWED_MEDIA_MIMES:
                raise BossAssetUnsupportedMedia({"file": "MIME type is not supported"})
            if declared_mime not in GENERIC_MIMES and not _declared_type_is_compatible(
                declared_mime, detected_mime
            ):
                raise BossAssetUnsupportedMedia(
                    {"file": "declared MIME type does not match the file signature"}
                )
            if declared_mime not in GENERIC_MIMES and declared_mime not in Config.BOSS_ALLOWED_MEDIA_MIMES:
                raise BossAssetUnsupportedMedia({"file": "MIME type is not supported"})

            status, status_warnings = _technical_for_unparsed(detected_kind)
            warnings = list(detected.get("warnings", [])) + status_warnings
            technical_metadata = dict(detected.get("technical_metadata", {}))
            if detected_kind in {"image", "document"}:
                technical_metadata.setdefault("byte_count", total)
            asset_id = new_asset_id()
            asset_dir = root / asset_id
            asset_dir.mkdir(mode=0o750)
            content_path = asset_dir / f"content.{detected['extension']}"
            os.replace(temporary_path, content_path)
            storage_key = content_path.relative_to(root).as_posix()
            artifacts: list[dict[str, Any]] = []
            if detected_kind in {"audio", "video"}:
                probed = probe_local_media(content_path)
                if probed:
                    status = "technical_parsed"
                    warnings = [
                        warning
                        for warning in warnings
                        if "ffprobe" not in warning.casefold() and "semantic parsing" not in warning.casefold()
                    ]
                    technical_metadata = dict(probed)
                    technical_metadata["byte_count"] = total
                    try:
                        artifacts, derivative_warnings = generate_media_derivatives(
                            content_path,
                            asset_dir,
                            root,
                            asset_id=asset_id,
                            facts=technical_metadata,
                        )
                    except Exception:
                        derivative_warnings = [
                            "ffmpeg derivatives could not be generated; "
                            "technical facts were kept."
                        ]
                    warnings.extend(derivative_warnings)
            metadata = {
                "schema_version": ASSET_SCHEMA_VERSION,
                "asset_id": asset_id,
                "scenario_id": selected_scenario_id,
                "workspace_id": None,
                "created_by": None,
                "original_filename": filename,
                "extension": detected["extension"],
                "mime_type": detected_mime,
                "kind": detected_kind,
                "size_bytes": total,
                "sha256": digest.hexdigest(),
                "status": status,
                "warnings": warnings,
                "technical_metadata": technical_metadata,
                "storage_key": storage_key,
                "artifacts": artifacts,
            }
            self._atomic_write_json(asset_dir / "metadata.json", metadata)
            return metadata
        except Exception:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
            # A directory is created only after all validation.  If persistence
            # fails after that point, remove only this generated UUID directory.
            if "asset_dir" in locals():
                shutil.rmtree(asset_dir, ignore_errors=True)
            raise

    def download_path(self, asset_id: str) -> tuple[dict[str, Any], Path]:
        record = self.get(asset_id)
        if record is None:
            raise BossAssetNotFound("asset not found")
        path = self._safe_record_path(record["storage_key"])
        if not path.is_file():
            raise BossAssetNotFound("asset not found")
        return record, path

    def delete(self, asset_id: str) -> bool:
        if not is_asset_id(asset_id):
            return False
        try:
            asset_dir = self._asset_dir(asset_id)
        except BossAssetNotFound:
            return False
        if not asset_dir.exists() and not asset_dir.is_symlink():
            return False
        root = self._root_path()
        try:
            resolved = asset_dir.resolve(strict=False)
            resolved.relative_to(root)
        except ValueError:
            return False
        if asset_dir.is_symlink():
            asset_dir.unlink()
        elif asset_dir.is_dir():
            shutil.rmtree(asset_dir)
        else:
            asset_dir.unlink()
        return True

    def add_artifact(self, asset_id: str, payload: Any) -> dict[str, Any]:
        asset = self.get(asset_id)
        if asset is None:
            raise BossAssetNotFound("asset not found")
        if not isinstance(payload, dict):
            raise BossAssetValidationError({"payload": "must be a JSON object"})
        fields: dict[str, str] = {}
        kind = payload.get("kind")
        if not isinstance(kind, str) or kind not in ARTIFACT_KINDS:
            fields["kind"] = f"must be one of: {', '.join(sorted(ARTIFACT_KINDS))}"
        text = payload.get("text")
        if not isinstance(text, str):
            fields["text"] = "is required and must be a string"
        elif len(text.encode("utf-8")) > MAX_ARTIFACT_TEXT_BYTES:
            fields["text"] = f"must be at most {MAX_ARTIFACT_TEXT_BYTES} UTF-8 bytes"
        processor_version = payload.get("processor_version")
        if (
            not isinstance(processor_version, str)
            or not processor_version.strip()
            or len(processor_version.strip()) > 120
            or "/" in processor_version
            or "\\" in processor_version
        ):
            fields["processor_version"] = "must be a safe non-empty version string"
        source_value = payload.get("source_metadata", payload.get("source"))
        try:
            source_metadata = _validated_source_metadata(source_value)
        except BossAssetValidationError as error:
            fields.update(error.fields)
            source_metadata = {}
        if fields:
            raise BossAssetValidationError(fields)

        artifact_id = new_artifact_id()
        asset_dir = self._asset_dir(asset_id)
        artifacts_dir = asset_dir / "artifacts"
        artifacts_dir.mkdir(mode=0o750, exist_ok=True)
        text_path = artifacts_dir / f"{artifact_id}.txt"
        metadata_path = artifacts_dir / f"{artifact_id}.json"
        text_storage_key = text_path.relative_to(self._root_path()).as_posix()
        artifact = {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "artifact_id": artifact_id,
            "source_asset_id": asset_id,
            "kind": kind,
            "processor_version": processor_version.strip(),
            "status": "provided",
            "warnings": [
                "User-supplied text artifact; no automatic semantic extraction was performed."
            ],
            "storage_key": text_storage_key,
            "source_metadata": source_metadata,
            "size_bytes": len(text.encode("utf-8")),
            "encoding_hint": _encoding_hint(text.encode("utf-8")),
        }
        try:
            self._atomic_write_text(text_path, text)
            self._atomic_write_json(metadata_path, artifact)
            updated_asset = dict(asset)
            references = list(updated_asset.get("artifacts", []))
            references.append(artifact)
            updated_asset["artifacts"] = references
            self._atomic_write_json(asset_dir / "metadata.json", updated_asset)
        except Exception:
            for path in (text_path, metadata_path):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            raise
        return artifact

    def list_artifacts(self, asset_id: str) -> list[dict[str, Any]]:
        asset = self.get(asset_id)
        if asset is None:
            raise BossAssetNotFound("asset not found")
        artifacts = asset.get("artifacts", [])
        return [item for item in artifacts if isinstance(item, dict)]

    def get_artifact(self, asset_id: str, artifact_id: str) -> tuple[dict[str, Any], str]:
        if not is_asset_id(asset_id) or not is_asset_id(artifact_id):
            raise BossAssetNotFound("artifact not found")
        asset = self.get(asset_id)
        if asset is None:
            raise BossAssetNotFound("artifact not found")
        artifact = next(
            (
                item
                for item in asset.get("artifacts", [])
                if isinstance(item, dict) and item.get("artifact_id") == artifact_id
            ),
            None,
        )
        if artifact is None or artifact.get("source_asset_id") != asset_id:
            raise BossAssetNotFound("artifact not found")
        text_path = self._safe_record_path(artifact.get("storage_key"))
        try:
            text = text_path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError, UnicodeDecodeError) as error:
            raise BossAssetNotFound("artifact not found") from error
        return artifact, text


BossAssetService = BossAssetStore


__all__ = [
    "BossAssetService",
    "BossAssetStore",
    "BossAssetTooLarge",
    "BossAssetUnsupportedMedia",
]
