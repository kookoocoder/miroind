# BOSS Full Product Plan

**Status:** Active implementation plan  
**Scope:** Expand the current BOSS text review into a complete India-context media and multi-agent simulation product while preserving the original MiroFish workflow.  
**Baseline:** Upstream MiroFish at `7657031ac01184afe2cb220f5ee3545573b5e843` plus the current BOSS/MiroInd MVP and model integration.

## 1. Product direction

BOSS will become an India-context message and media review system with two
execution modes:

1. **Quick review** — fast, credential-free or model-backed review for text and
   derived media evidence.
2. **Graph simulation** — a full BOSS scenario that builds an isolated graph,
   creates inspectable audience agents, runs social-style interactions, updates
   run memory, and produces a BOSS report.

The original MiroFish graph, OASIS, Twitter/Reddit, report, and interaction
workflow remains available as a legacy/general-purpose workflow. BOSS-specific
execution must use new adapters and must not silently change legacy semantics.

## 2. Non-negotiable product rules

- BOSS output is synthetic exploration, not polling, market truth, or a forecast.
- Every run stores an immutable scenario snapshot and input hashes.
- Every media-derived statement identifies its source artifact and processor.
- Binary media is never embedded in JSON run records.
- Provider credentials never enter browser state, reports, manifests, or logs.
- No real-platform posting, account access, scraping, or automation by default.
- Sensitive-attribute inference and targeted political influence tooling remain out of scope.
- A shared graph is never reused across unrelated BOSS runs unless explicit,
  versioned provenance and isolation filters are implemented.
- Offline mode remains usable and remains the default for local development.

## 3. Requested capability map

| Capability | Planned implementation | Gate |
| --- | --- | --- |
| Graph construction from BOSS brand inputs | Versioned BOSS manifest, fixed ontology, graph adapter | Phase 2 |
| Zep memory for BOSS runs | Per-run graph, provenance metadata, lifecycle barriers | Phase 3 |
| OASIS simulation for BOSS | Deterministic BOSS persona materializer and config adapter | Phase 3 |
| Twitter/X simulation | Reuse legacy runner through BOSS adapter | Phase 3 |
| Reddit simulation | Reuse legacy runner through BOSS adapter | Phase 3 |
| Instagram/Reels simulation | New non-network interaction format | Phase 5 |
| WhatsApp-style groups | New group/forwarding interaction format | Phase 5 |
| ShareChat/Moj simulation | New short-form regional interaction format | Phase 5 |
| Real platform integrations | Explicitly gated, read-only research connectors first | Phase 8, optional |
| Multiple interacting BOSS agents | Stable brand and audience agent IDs | Phase 3 |
| Round-based social evolution | OASIS rounds and platform adapter contract | Phase 3 |
| Dynamic recommendation feeds | Platform-format recommendation adapter | Phase 5 |
| Simulation timelines | Run action/timeline projection | Phase 3 |
| Agent action histories | Existing runner action APIs plus BOSS provenance | Phase 3 |
| Persistent BOSS persona conversations | Run-scoped conversation store and interview API | Phase 4 |
| BOSS-specific graph memory | BOSS ontology and activity provenance | Phase 3 |
| BOSS agent interviews | BOSS report/interview adapter | Phase 4 |
| BOSS report-agent chat | BOSS report strategy over existing tools | Phase 4 |
| Video ingestion | Asset catalog, safe upload, technical parsing | Phase 1 |
| Audio transcription | Provider interface plus selected local/hosted adapter | Phase 2 |
| OCR | Image, scanned-PDF, and sampled-video artifacts | Phase 2 |
| Image understanding | Bounded multimodal provider adapter | Phase 5 |
| Video scene understanding | Keyframes + transcript + OCR + temporal synthesis | Phase 5 |
| PDF export | Shared report renderer and browser/server PDF path | Phase 4 |
| Side-by-side audience comparison | Multi-audience immutable run configuration | Phase 6 |
| Team workspaces | Auth, workspace membership, database, object storage | Phase 8 |
| Collaboration | Shared profiles, runs, comments, audit trail | Phase 8 |
| Saved brand profiles | Versioned local/profile catalog | Phase 1 |
| Saved audience presets | Versioned local/profile catalog | Phase 1 |

## 4. Architecture target

```text
BOSS UI
  ├── Scenario editor
  ├── Asset/media workspace
  ├── Audience and comparison workspace
  ├── Run progress and timeline
  └── Structured report/export view
        │
        ▼
BOSS API / orchestration boundary
  ├── Scenario + revision catalog
  ├── Asset + artifact catalog
  ├── Profile/preset catalog
  ├── Quick review adapter
  ├── Graph/OASIS adapter
  ├── Media processor jobs
  ├── Report strategy
  └── Workspace authorization
        │
        ├── SQLite metadata catalog + local/object media storage
        ├── Zep graph provider
        ├── OASIS platform runners
        ├── Local media tools
        └── Optional model providers/OpenCode
```

The current JSON persistence is retained for backward compatibility with the
MVP, but new BOSS scenario, asset, run, and profile records should move behind
repository interfaces so SQLite/object storage can be introduced without
rewriting the UI or report contracts.

## 5. Canonical scenario manifest

All BOSS execution paths normalize into a versioned manifest. The existing
`POST /api/miroind/runs` payload remains supported and is normalized into this
shape.

```json
{
  "schema_version": "boss.scenario.v1",
  "scenario_id": "scenario_<id>",
  "revision": 1,
  "brand": {
    "name": "…",
    "positioning": "…",
    "tone": "…",
    "audience_relationship": "…",
    "red_lines": [],
    "preferred_vocabulary": [],
    "claims_must_not_invent": []
  },
  "audiences": [
    {
      "id": "audience_<id>",
      "country": "IN",
      "region": "…",
      "local_context": "…",
      "language_signal": "optional",
      "age_band": "…",
      "occupation": "…",
      "city_tier": "…",
      "income_band": "…",
      "exclusions": [],
      "persona_pack_id": "boss-india-v1"
    }
  ],
  "assets": [
    {
      "asset_id": "asset_<id>",
      "kind": "text|document|image|audio|video",
      "title": "…",
      "storage_key": null,
      "mime_type": "text/plain",
      "size_bytes": 0,
      "sha256": "…",
      "language": "optional",
      "derived_artifacts": []
    }
  ],
  "run_config": {
    "execution_mode": "offline|model|graph_oasis",
    "interaction_formats": ["short_post"],
    "report_language": "en",
    "persona_count": 6,
    "budget": 20,
    "timezone": "Asia/Kolkata",
    "seed": 1234,
    "graph_memory_update": false
  },
  "provenance": {
    "hypothetical": true,
    "input_source": "user",
    "manifest_sha256": "…"
  }
}
```

The manifest is authoritative. Zep graphs, OASIS configs, reports, transcripts,
OCR, keyframes, and model reviews are derived projections and must refer back to
the manifest revision and hashes.

## 6. Delivery phases

### Phase 0 — Stabilize and isolate

1. Freeze the current offline BOSS contract with compatibility tests.
2. Keep legacy `/api/graph/*`, `/api/simulation/*`, and `/api/report/*` behavior unchanged.
3. Introduce BOSS orchestration under `/api/boss/*` rather than branching legacy routes.
4. Add project-relative IDs, version fields, hashes, and structured warnings.
5. Add restart-safe job records rather than relying only on process-memory tasks.

**Exit gate:** Existing tests pass; old MiroFish workflows still build and route;
current offline BOSS runs still produce identical reports for identical inputs.

### Phase 1 — Scenario, profiles, presets, and media catalog

1. Add immutable scenario revisions.
2. Add saved brand profiles.
3. Add saved audience profiles and presets.
4. Add local SQLite metadata catalog behind repositories.
5. Add safe asset upload with MIME/magic-byte checks, size limits, checksums,
   storage keys, retention metadata, and ownership fields.
6. Add image/document/audio/video technical metadata extraction.
7. Add thumbnail, keyframe, and audio derivative artifacts.
8. Add BOSS asset upload UI with progress, retry, and processing status.

**Exit gate:** A media asset can be uploaded, hashed, inspected, reloaded after
restart, and referenced by an immutable scenario without binary data in JSON.

### Phase 2 — Derived media evidence

1. Add OCR artifact interface.
2. Add scanned-PDF OCR fallback.
3. Add image OCR and sampled-video OCR.
4. Add transcription provider interface with timestamps and confidence.
5. Select and integrate one transcription implementation after evaluating local
   Mac resource use, Indian English, code-mixing, privacy, and licensing.
6. Store transcript, OCR, warnings, processor versions, and source references.
7. Require explicit evidence provenance in reports.

**Exit gate:** Media runs fail safely when no usable derived text exists and never
claim visual/audio understanding from a filename or MIME type alone.

### Phase 3 — BOSS graph and OASIS vertical slice

1. Add a fixed BOSS ontology adapter.
2. Build one isolated graph per graph-backed BOSS run.
3. Materialize deterministic BOSS brand and audience profiles.
4. Add stable IDs across Reddit JSON and Twitter CSV.
5. Persist `Asia/Kolkata`, seed, manifest hash, asset hash, and source metadata.
6. Preserve exact submitted text/derived-text content as the initial brand post.
7. Reuse OASIS Twitter/Reddit runners through a BOSS simulation adapter.
8. Preserve Zep ingestion barriers and add BOSS provenance metadata.
9. Add BOSS run progress, timeline, actions, posts, comments, and agent stats.

**Exit gate:** A fictional BOSS scenario can create an isolated graph, prepare
stable profiles/config, run Twitter/Reddit simulation, and stop safely without
changing legacy MiroFish behavior.

### Phase 4 — BOSS reports and conversations

1. Add a BOSS report strategy on top of `ReportManager` and Zep tools.
2. Keep legacy prediction reports separate from BOSS stress-test reports.
3. Add BOSS-specific report metadata, evidence links, assumptions, disagreement,
   validation questions, and media provenance.
4. Add BOSS agent interviews.
5. Add persistent run-scoped persona conversations.
6. Add BOSS report-agent chat.
7. Add JSON, Markdown, HTML, CSV, and browser/server PDF export.

**Exit gate:** A BOSS graph run can produce a report that distinguishes observed
simulation evidence, model interpretation, and speculation.

### Phase 5 — Additional interaction formats and multimodal synthesis

1. Add a platform-format adapter interface.
2. Add Instagram/Reels-style short-form interactions without real platform access.
3. Add WhatsApp-style groups, forwarding, and status-style sharing.
4. Add ShareChat/Moj-style short-form interactions.
5. Add recommendation-feed simulation.
6. Add image understanding through a bounded multimodal provider adapter.
7. Add video scene understanding from transcript, OCR, keyframes, and temporal
   summaries.
8. Preserve clear evidence boundaries for each modality.

**Exit gate:** Each additional format is an inspectable simulation pattern, not a
real account integration, and the report identifies which evidence supports each
finding.

### Phase 6 — Audience comparison

1. Permit multiple immutable audience definitions per run.
2. Run the same asset and brand snapshot across audiences.
3. Show shared risks, audience-specific risks, and disagreement.
4. Add side-by-side UI and export.
5. Avoid statistical language that implies real population percentages.

**Exit gate:** Users can compare two or more Indian audience contexts without
duplicating or mutating the original asset/run snapshot.

### Phase 7 — Workspace collaboration foundations

1. Select authentication and workspace identity.
2. Add database-backed workspace membership and roles.
3. Add shared brand profiles, audience presets, assets, runs, reports, and comments.
4. Add audit log, sharing/revocation, retention, and deletion controls.
5. Add signed media/report downloads.

**Exit gate:** Every workspace-scoped object is authorization-checked and no
filesystem ID alone grants access.

### Phase 8 — Production and real integrations, optional

1. Add worker deployment for media and graph jobs.
2. Add object storage and queue infrastructure.
3. Replace development server startup with production serving.
4. Add read-only, explicit, provider-specific platform connectors only if there is
   a lawful, approved use case.
5. Never add automatic posting or account automation by default.

## 7. First implementation slice

The first build slice after this plan is Phase 0 plus the beginning of Phase 1:

1. Add canonical manifest normalization while preserving the current text API.
2. Add BOSS scenario creation/read endpoints under `/api/boss/scenarios`.
3. Persist immutable scenario manifests with SHA-256 hashes and atomic writes.
4. Add brand and audience profile/preset records using a small repository layer.
5. Add offline tests for backward compatibility, hashes, path safety, and read-back.

Only after this slice is tested should graph/OASIS integration be connected. This
prevents the existing synchronous MVP path from becoming a fragile mixture of
offline rules, Zep calls, subprocesses, and media processing.

## 8. Quality gates

- `make test` remains green after every phase.
- Every new asynchronous task has a persisted status and restart behavior.
- Every report includes input, model, processor, and provenance metadata.
- Every media feature has safe limits and a non-media fallback/error state.
- Every graph run is isolated or has an explicit, tested scope filter.
- Every user-facing claim distinguishes simulation from real audience evidence.
- No feature is marked complete until a user-facing flow, persistence/read-back,
  failure state, and meaningful test are verified.
