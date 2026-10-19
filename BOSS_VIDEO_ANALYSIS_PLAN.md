# BOSS video analysis execution plan

**Status:** Slices 1 and 2 are implemented. Omnirush models have no tokens left this week. OpenCode Console is connected; paid OpenCode models have no funds, so slice 2 ran on `opencode/deepseek-v4.1-flash-free`.  
**Depends on:** `BOSS_FULL_PRODUCT_PLAN.md` phases 1, 2, and 5  
**Model runner:** project-local OpenCode (`opencode run --standalone`), not the stuck interactive session

A video upload is stored and identified by magic bytes. It is marked `uploaded_unparsed`. This plan turns that file into evidence in four slices. Later slices must not start until the earlier slice’s tests pass.

## Rules for every slice

- A report may describe only text, transcript, OCR, or a model reading that names its artifact id and processor.
- A filename, MIME type, duration, or codec is not scene understanding.
- Binary media stays on disk. JSON records store hashes, storage keys, and technical facts.
- If ffprobe, ffmpeg, OCR, or a model is missing, keep the file and say what was not done.
- Do not change legacy `/api/graph`, `/api/simulation`, or `/api/report` behavior.
- Do not start OASIS or Zep from the media path.
- Provider keys must not appear in records, logs, or prompts stored on disk.

## Slice 1 — Technical probe

**Goal:** When ffprobe can read a real audio or video file, store duration, picture size, codecs, and frame rate. Stub bytes that ffprobe cannot read stay `uploaded_unparsed`.

1. Add `backend/app/services/boss_media_probe.py`.
2. Call `ffprobe -v error -print_format json -show_format -show_streams` with a short timeout. Do not pass any network URL.
3. On success, set `technical_metadata.status` to `technical_parsed` and keep only numeric or short string facts: `duration_seconds`, `width`, `height`, `video_codec`, `audio_codec`, `frame_rate`, `has_audio`, `has_video`, `probe_tool`.
4. On a missing binary, timeout, or unreadable file, keep today’s `uploaded_unparsed` warning. `backend/tests/test_boss_assets.py` uses fake MP4 and MP3 headers and must keep passing without a model.
5. Add a test that feeds a fake ffprobe JSON result and checks that the record has technical facts and no transcript, OCR, or scene claim.

**Exit:** `backend/tests/test_boss_assets.py` passes. A real file can be probed; a fake header cannot.

## Slice 2 — Keyframes and audio derivative

**Goal:** Store a few JPEG keyframes and one audio extract as artifact files, referenced by storage key.

1. Extend artifact kinds with `thumbnail`, `keyframe`, and `audio_extract`.
2. Use ffmpeg only after slice 1 parsed the file. Cap keyframes (for example 6) and output size.
3. Record timestamp, sha256, and processor `ffmpeg` on each artifact. Do not put image bytes in JSON.
4. If ffmpeg fails, leave the technical record and add a warning. Do not invent frames.

**Exit:** A short fixture video produces readable derivative files and a reload shows the same artifact ids.

## Slice 3 — Transcript and sampled OCR

**Goal:** Produce text evidence, or fail with a clear gap.

1. Add a transcription provider interface. The first adapter may be local and optional.
2. Add sampled-frame OCR behind the same artifact record (`kind: ocr` already exists).
3. A video simulation may use this text only through the existing derived-text path in `boss_personas.resolve_boss_asset_text`.
4. With no transcript and no OCR text, preparation stays rejected. Do not describe the picture from the filename.

**Exit:** Media with user-supplied or processor-supplied text prepares. Media without text does not.

## Slice 4 — Scene reading

**Goal:** One bounded model reading over keyframes plus transcript and OCR, citing each artifact.

1. Call the existing OpenCode review path only when `BOSS_MODEL_ENABLED=true`.
2. The model input is artifact ids and extracted text, plus at most the capped keyframe set.
3. The stored result is an artifact of kind `description` with `processor`, `model`, and source artifact ids.
4. Offline mode never calls the model.

**Exit:** The description names its sources. Offline runs still complete the technical and text path with no model call.

## How to run a slice

Use a new standalone OpenCode process. Do not continue the interactive session that stopped at `0 tok left`.

```sh
env -u OPENCODE -u OPENCODE_PID -u OPENCODE_SERVER \
  ./node_modules/.bin/opencode run --standalone --auto \
  --model omnirush/gpt-6.1-sol \
  --title "BOSS video slice" \
  "<slice instructions>"
```

Configured OpenCode models here are `omnirush/gpt-6-astra`, `omnirush/gpt-6-sol`, and `omnirush/gpt-6.1-sol`. Slice 1 uses `omnirush/gpt-6.1-sol` so it does not resume the full Astra session.
