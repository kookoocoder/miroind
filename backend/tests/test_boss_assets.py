import hashlib
import io
import json
import struct
import subprocess
from pathlib import Path

import pytest

from app import create_app
from app.config import Config


@pytest.fixture
def assets_root(tmp_path, monkeypatch):
    root = tmp_path / "boss-assets"
    monkeypatch.setattr(Config, "BOSS_ASSETS_DIR", str(root))
    monkeypatch.setattr(Config, "BOSS_MAX_ASSET_BYTES", 100 * 1024 * 1024)
    return root


@pytest.fixture
def client(assets_root):
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _upload(client, content, filename, *, mimetype=None, scenario_id=None):
    file_value = (io.BytesIO(content), filename, mimetype) if mimetype else (io.BytesIO(content), filename)
    data = {"file": file_value}
    if scenario_id is not None:
        data["scenario_id"] = scenario_id
    return client.post("/api/boss/assets", data=data, content_type="multipart/form-data")


def _png_bytes(width=3, height=2):
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x02\x00\x00\x00"
    )


def _mock_successful_probe(monkeypatch, duration="2.5"):
    facts = {
        "status": "technical_parsed",
        "probe_tool": "ffprobe",
        "has_video": True,
        "has_audio": True,
        "duration_seconds": float(duration),
        "width": 320,
        "height": 240,
        "video_codec": "h264",
        "audio_codec": "aac",
        "frame_rate": 30.0,
    }
    monkeypatch.setattr(
        "app.services.boss_assets.probe_local_media", lambda _path: dict(facts)
    )


def _mock_ffmpeg(
    monkeypatch,
    *,
    write_output=True,
    returncode=0,
    keyframe_bytes=b"\xff\xd8\xff\xe0BINARY-MARKER\xff\xd9",
    audio_bytes=b"\x00\x00\x00\x18ftypM4A \x00\x00\x00\x00BINARY-MARKER",
):
    monkeypatch.setattr(
        "app.services.boss_media_derivatives.shutil.which",
        lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None,
    )

    def runner(command, **_kwargs):
        if write_output and returncode == 0:
            target = Path(command[-1])
            payload = keyframe_bytes if "-frames:v" in command else audio_bytes
            target.write_bytes(payload)
        return subprocess.CompletedProcess(
            args=command, returncode=returncode, stdout="", stderr=""
        )

    monkeypatch.setattr("app.services.boss_media_derivatives.subprocess.run", runner)


def test_upload_read_status_download_delete_and_checksum(client, assets_root):
    content = "Nayi Disha: take the next step.\n".encode("utf-8")
    response = _upload(
        client,
        content,
        "message.txt",
        mimetype="text/plain",
        scenario_id="scenario_0123456789abcdef01234567",
    )

    assert response.status_code == 201
    record = response.json["data"]
    asset_id = record["asset_id"]
    assert record["scenario_id"] == "scenario_0123456789abcdef01234567"
    assert record["workspace_id"] is None
    assert record["created_by"] is None
    assert record["kind"] == "text"
    assert record["extension"] == "txt"
    assert record["mime_type"] == "text/plain"
    assert record["size_bytes"] == len(content)
    assert record["sha256"] == hashlib.sha256(content).hexdigest()
    assert record["status"] == "uploaded"
    assert record["storage_key"] == f"{asset_id}/content.txt"
    assert not record["storage_key"].startswith("/")
    assert "content" not in record

    metadata_text = json.dumps(record, ensure_ascii=False)
    assert str(assets_root) not in metadata_text
    assert "SECRET" not in metadata_text
    metadata_path = assets_root / asset_id / "metadata.json"
    assert metadata_path.is_file()
    assert json.loads(metadata_path.read_text(encoding="utf-8")) == record

    read_response = client.get(f"/api/boss/assets/{asset_id}")
    status_response = client.get(f"/api/boss/assets/{asset_id}/status")
    assert read_response.status_code == 200
    assert status_response.status_code == 200
    assert read_response.json["data"] == record
    assert status_response.json["data"]["status"] == "uploaded"
    assert "content" not in read_response.json["data"]

    download_response = client.get(f"/api/boss/assets/{asset_id}/download")
    assert download_response.status_code == 200
    assert download_response.data == content
    assert download_response.mimetype == "text/plain"

    delete_response = client.delete(f"/api/boss/assets/{asset_id}")
    assert delete_response.status_code == 200
    assert delete_response.json["data"] == {"asset_id": asset_id, "deleted": True}
    assert not (assets_root / asset_id).exists()
    assert client.get(f"/api/boss/assets/{asset_id}").status_code == 404
    assert client.get(f"/api/boss/assets/{asset_id}/download").status_code == 404


def test_png_signature_is_checked_and_dimensions_are_extracted(client):
    content = _png_bytes(17, 11)
    response = _upload(client, content, "renamed.txt", mimetype="image/png")

    assert response.status_code == 201
    record = response.json["data"]
    assert record["kind"] == "image"
    assert record["extension"] == "png"
    assert record["mime_type"] == "image/png"
    assert record["technical_metadata"]["width"] == 17
    assert record["technical_metadata"]["height"] == 11


def test_text_mime_cannot_claim_png_bytes(client):
    response = _upload(client, _png_bytes(), "not-really-text.txt", mimetype="text/plain")

    assert response.status_code == 400
    assert "does not match" in response.json["fields"]["file"]


def test_ffprobe_json_records_technical_facts_without_scene_claims(client, monkeypatch):
    document = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 320,
                "height": 240,
                "avg_frame_rate": "30/1",
                "duration": "2.5",
            },
            {"codec_type": "audio", "codec_name": "aac"},
        ],
        "format": {"duration": "2.5", "filename": "/secret/path/clip.mp4"},
    }

    def runner(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(document), stderr="")

    monkeypatch.setattr(
        "app.services.boss_media_probe.shutil.which",
        lambda name: "/usr/bin/ffprobe" if name == "ffprobe" else None,
    )
    monkeypatch.setattr("app.services.boss_media_probe.subprocess.run", runner)

    response = _upload(
        client,
        b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00",
        "clip.mp4",
        mimetype="video/mp4",
    )

    assert response.status_code == 201
    record = response.json["data"]
    metadata = record["technical_metadata"]
    assert record["status"] == "technical_parsed"
    assert metadata["status"] == "technical_parsed"
    assert metadata["probe_tool"] == "ffprobe"
    assert metadata["duration_seconds"] == 2.5
    assert metadata["width"] == 320
    assert metadata["height"] == 240
    assert metadata["video_codec"] == "h264"
    assert metadata["audio_codec"] == "aac"
    assert metadata["frame_rate"] == 30.0
    assert metadata["has_video"] is True
    assert metadata["has_audio"] is True
    serialized = json.dumps(record, ensure_ascii=False)
    assert "/secret" not in serialized
    folded = serialized.casefold()
    assert "transcript" not in folded
    assert "ocr" not in folded
    assert "scene" not in folded


def test_ffmpeg_derivatives_are_files_with_hashes_and_reload_same_ids(
    client, assets_root, monkeypatch
):
    monkeypatch.setattr(Config, "BOSS_MAX_KEYFRAME_BYTES", 512)
    monkeypatch.setattr(Config, "BOSS_MAX_AUDIO_EXTRACT_BYTES", 512)
    _mock_successful_probe(monkeypatch, duration="2.5")
    _mock_ffmpeg(monkeypatch)

    response = _upload(
        client,
        b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00",
        "clip.mp4",
        mimetype="video/mp4",
    )

    assert response.status_code == 201
    record = response.json["data"]
    assert record["status"] == "technical_parsed"
    assert record["warnings"] == []
    keyframes = [item for item in record["artifacts"] if item["kind"] == "keyframe"]
    audio = [item for item in record["artifacts"] if item["kind"] == "audio_extract"]
    assert 1 <= len(keyframes) <= 6
    assert len(audio) == 1
    assert len(record["artifacts"]) == len(keyframes) + 1

    for artifact in record["artifacts"]:
        assert artifact["processor"] == "ffmpeg"
        assert artifact["processor_version"] == "ffmpeg"
        assert artifact["status"] == "derived"
        assert artifact["source_asset_id"] == record["asset_id"]
        assert isinstance(artifact["timestamp_seconds"], float)
        assert artifact["storage_key"].startswith(
            f"{record['asset_id']}/artifacts/{artifact['artifact_id']}"
        )
        stored = assets_root / artifact["storage_key"]
        assert stored.is_file()
        assert stored.stat().st_size == artifact["size_bytes"]
        assert stored.stat().st_size <= 512
        assert hashlib.sha256(stored.read_bytes()).hexdigest() == artifact["sha256"]
        sidecar = stored.with_suffix(".json")
        assert json.loads(sidecar.read_text(encoding="utf-8")) == artifact

    assert all(item["timestamp_seconds"] >= 0 for item in keyframes)
    assert [item["timestamp_seconds"] for item in keyframes] == sorted(
        item["timestamp_seconds"] for item in keyframes
    )
    assert audio[0]["timestamp_seconds"] == 0.0

    metadata_path = assets_root / record["asset_id"] / "metadata.json"
    assert b"BINARY-MARKER" not in metadata_path.read_bytes()
    assert "BINARY-MARKER" not in json.dumps(record)
    assert record["artifacts"][0]["sha256"] != record["sha256"]

    reloaded = client.get(f"/api/boss/assets/{record['asset_id']}").json["data"]
    assert [item["artifact_id"] for item in reloaded["artifacts"]] == [
        item["artifact_id"] for item in record["artifacts"]
    ]


def test_missing_ffmpeg_keeps_technical_record_with_warning(
    client, assets_root, monkeypatch
):
    _mock_successful_probe(monkeypatch)
    monkeypatch.setattr("app.services.boss_media_derivatives.shutil.which", lambda _name: None)

    response = _upload(
        client,
        b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00",
        "clip.mp4",
        mimetype="video/mp4",
    )

    assert response.status_code == 201
    record = response.json["data"]
    assert record["status"] == "technical_parsed"
    assert record["technical_metadata"]["probe_tool"] == "ffprobe"
    assert record["artifacts"] == []
    assert any("ffmpeg is not installed" in warning for warning in record["warnings"])
    assert not (assets_root / record["asset_id"] / "artifacts").exists()


def test_failed_ffmpeg_does_not_invent_derivative_records(client, assets_root, monkeypatch):
    _mock_successful_probe(monkeypatch)
    _mock_ffmpeg(monkeypatch, write_output=False, returncode=1)

    response = _upload(
        client,
        b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00",
        "clip.mp4",
        mimetype="video/mp4",
    )

    assert response.status_code == 201
    record = response.json["data"]
    assert record["status"] == "technical_parsed"
    assert record["artifacts"] == []
    assert any("ffmpeg could not extract" in warning for warning in record["warnings"])
    artifact_dir = assets_root / record["asset_id"] / "artifacts"
    assert not artifact_dir.exists() or list(artifact_dir.iterdir()) == []


def test_oversized_ffmpeg_output_is_discarded(
    client, assets_root, monkeypatch
):
    monkeypatch.setattr(Config, "BOSS_MAX_KEYFRAME_BYTES", 10)
    monkeypatch.setattr(Config, "BOSS_MAX_AUDIO_EXTRACT_BYTES", 10)
    _mock_successful_probe(monkeypatch)
    _mock_ffmpeg(
        monkeypatch,
        keyframe_bytes=b"\xff\xd8" + b"x" * 100,
        audio_bytes=b"x" * 100,
    )

    response = _upload(
        client,
        b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00",
        "clip.mp4",
        mimetype="video/mp4",
    )

    assert response.status_code == 201
    record = response.json["data"]
    assert record["status"] == "technical_parsed"
    assert record["artifacts"] == []
    assert any("file-size cap" in warning for warning in record["warnings"])
    artifact_dir = assets_root / record["asset_id"] / "artifacts"
    assert not artifact_dir.exists() or list(artifact_dir.iterdir()) == []


def test_audio_and_video_are_marked_unparsed_without_semantic_claims(client):
    audio = _upload(client, b"ID3\x04\x00\x00\x00", "voice.mp3", mimetype="audio/mpeg")
    video = _upload(
        client,
        b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00",
        "clip.mp4",
        mimetype="video/mp4",
    )

    assert audio.status_code == 201
    assert audio.json["data"]["kind"] == "audio"
    assert audio.json["data"]["status"] == "uploaded_unparsed"
    assert audio.json["data"]["artifacts"] == []
    assert "ffprobe" in audio.json["data"]["warnings"][0]
    assert video.status_code == 201
    assert video.json["data"]["kind"] == "video"
    assert video.json["data"]["status"] == "uploaded_unparsed"
    assert video.json["data"]["artifacts"] == []
    assert "semantic parsing" in video.json["data"]["warnings"][0]


def test_oversized_and_unsupported_mime_uploads_are_rejected(client, assets_root, monkeypatch):
    monkeypatch.setattr(Config, "BOSS_MAX_ASSET_BYTES", 3)
    oversized = _upload(client, b"four", "note.txt", mimetype="text/plain")
    assert oversized.status_code == 413
    assert oversized.json["fields"]["file"] == "must be at most 3 bytes"
    assert list(assets_root.glob("*")) == []

    monkeypatch.setattr(Config, "BOSS_MAX_ASSET_BYTES", 100)
    unsupported = _upload(client, b"MZ\x90\x00", "program.exe", mimetype="application/x-msdownload")
    assert unsupported.status_code == 400
    assert "supported" in unsupported.json["fields"]["file"]


def test_filename_scenario_and_identifier_path_traversal_are_rejected(client):
    unsafe_filename = _upload(client, b"safe", "../escape.txt", mimetype="text/plain")
    assert unsafe_filename.status_code == 400
    assert unsafe_filename.json["fields"]["file"] == "filename must be a safe basename"

    unsafe_scenario = _upload(
        client,
        b"safe",
        "safe.txt",
        mimetype="text/plain",
        scenario_id="../../etc/passwd",
    )
    assert unsafe_scenario.status_code == 400
    assert "scenario_id" in unsafe_scenario.json["fields"]

    assert client.get("/api/boss/assets/../../etc/passwd").status_code == 404
    assert client.get("/api/boss/assets/not-an-asset/status").status_code == 404
    assert client.delete("/api/boss/assets/../../etc/passwd").status_code == 404


def test_user_supplied_text_artifact_is_separate_and_readable(client, assets_root):
    upload = _upload(client, b"spoken source", "clip.txt", mimetype="text/plain")
    asset_id = upload.json["data"]["asset_id"]
    artifact_text = "User supplied transcript: नमस्ते India"
    response = client.post(
        f"/api/boss/assets/{asset_id}/artifacts",
        json={
            "kind": "transcript",
            "text": artifact_text,
            "processor_version": "user-provided-v1",
            "source_metadata": {"source": "interview notes", "language": "hi"},
        },
    )

    assert response.status_code == 201
    artifact = response.json["data"]
    artifact_id = artifact["artifact_id"]
    assert artifact["source_asset_id"] == asset_id
    assert artifact["kind"] == "transcript"
    assert artifact["processor_version"] == "user-provided-v1"
    assert artifact["status"] == "provided"
    assert artifact["storage_key"] == f"{asset_id}/artifacts/{artifact_id}.txt"
    assert "text" not in artifact
    assert "semantic extraction" in artifact["warnings"][0]

    asset = client.get(f"/api/boss/assets/{asset_id}").json["data"]
    assert asset["artifacts"] == [artifact]
    assert "text" not in asset["artifacts"][0]

    list_response = client.get(f"/api/boss/assets/{asset_id}/artifacts")
    read_response = client.get(f"/api/boss/assets/{asset_id}/artifacts/{artifact_id}")
    assert list_response.status_code == 200
    assert list_response.json["data"] == [artifact]
    assert read_response.status_code == 200
    assert read_response.json["data"] == {"artifact": artifact, "text": artifact_text}

    stored_text = assets_root / asset_id / "artifacts" / f"{artifact_id}.txt"
    stored_metadata = assets_root / asset_id / "artifacts" / f"{artifact_id}.json"
    assert stored_text.read_text(encoding="utf-8") == artifact_text
    assert json.loads(stored_metadata.read_text(encoding="utf-8")) == artifact
    persisted = json.dumps(asset, ensure_ascii=False)
    assert str(assets_root) not in persisted
    assert "SECRET" not in persisted


def test_artifact_metadata_rejects_secrets_and_invalid_kind(client):
    upload = _upload(client, b"source", "source.txt", mimetype="text/plain")
    asset_id = upload.json["data"]["asset_id"]
    response = client.post(
        f"/api/boss/assets/{asset_id}/artifacts",
        json={
            "kind": "summary",
            "text": "not accepted",
            "processor_version": "../unsafe",
            "source_metadata": {"api_key": "SECRET"},
        },
    )

    assert response.status_code == 400
    assert "kind" in response.json["fields"]
    assert "processor_version" in response.json["fields"]
    assert response.json["fields"]["source_metadata.api_key"] == "must not contain credentials or secrets"
