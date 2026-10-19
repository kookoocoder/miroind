# MiroInd Implementation Plan

**Status:** MVP slice implemented and verified
**Source:** `MiroInd_Project_Alignment_Document.docx` v0.1 and the repository roadmap in `README.md`  
**Current repository state:** Upstream MiroFish frontend, Flask backend, simulation engine, and tests are present. India-specific personas, Hindi-first flows, local graph memory, and brand/image reporting are not yet implemented.

## 1. Product outcome

Build MiroInd into an India-focused **brand and message image stress-tester**.

Given a brand profile, an asset, and a defined Indian audience segment, the product should:

1. Create an inspectable set of synthetic audience personas.
2. Simulate how those personas may interpret and discuss the asset.
3. Produce a structured report about image risks, misunderstandings, and improvements.
4. Clearly communicate assumptions, uncertainty, model configuration, and limitations.

The product is for exploration and pre-publish review. It must never present synthetic reactions as polling, market truth, or a guaranteed prediction.

## 2. Recommended first release (MVP)

The first release should be deliberately narrow so that quality can be evaluated before adding more platforms, languages, and media types.

### Included

- Text-based assets: post copy, announcement, product message, landing-page copy, or script.
- One brand or creator profile per simulation.
- One audience segment per simulation, with:
  - Region or state
  - Preferred language
  - Age band
  - Occupation
  - City tier
  - Income band where relevant
- Eight to ten editable Indian persona templates for the initial audience families.
- English and Hindi UI/report support.
- Hindi–English code-mixed output where model quality is acceptable, clearly labelled as experimental.
- One platform-style interaction format for the first evaluation loop: short-form post plus reactions/discussion.
- A structured report containing:
  - Overall image impact direction and explanation
  - Positive, negative, and mixed reactions
  - Specific wording or asset risk points
  - Likely misunderstandings
  - Audience disagreements and minority reactions
  - Concrete adjustments
  - Optional constrained rewrites
  - Assumptions, uncertainty, model settings, and estimated usage
- A quick-simulation configuration with an explicit agent-count and budget limit.
- Reproducible example scenarios using fictional or clearly hypothetical inputs.

### Explicitly not included in the MVP

- Video understanding or video upload workflows.
- Real Instagram, WhatsApp, ShareChat, Moj, X, or Reddit integrations.
- Automatic publishing, account access, or social-media automation.
- Representative polling, campaign optimisation claims, or real-world outcome prediction.
- Sensitive-attribute targeting or inference without an explicit, reviewed research justification.
- Tamil, Telugu, Marathi, and Bengali support beyond future-ready data structures.
- Team collaboration, saved workspaces, PDF export, and advanced comparison mode.

## 3. Implementation work packages

### Work package 0 — Reproducible project baseline

**Purpose:** Make the existing foundation safe to extend and easy to rebuild.

Tasks:

- Confirm the supported Node.js and Python versions and pin them in repository files.
- Keep the existing Vue, Flask, and simulation-engine architecture unless an evaluated limitation requires a change.
- Add or verify a repository Dockerfile that can install dependencies and run the project.
- Define one offline-capable test entry point, such as `make test`, which runs the relevant unit and integration tests without requiring hosted credentials.
- Keep lockfiles current: root/frontend npm lockfiles and the backend Python lockfile.
- Update setup documentation with exact install, run, test, and deployment instructions.
- Preserve AGPL and upstream attribution.

**Exit criteria:** A clean checkout can build and run the documented checks without machine-specific absolute paths or committed secrets.

### Work package 1 — Domain model and input contract

**Purpose:** Establish stable data structures before changing prompts or UI.

Define validated schemas for:

- `BrandProfile`: positioning, audience relationship, tone, red lines, preferred vocabulary, and claims that must not be invented.
- `Asset`: type, text content, optional title/context, language, and source metadata.
- `AudienceDefinition`: geography, language, age, occupation, city tier, income, and exclusions.
- `SimulationConfig`: persona count, interaction format, model/provider, token or cost budget, seed if supported, and language mode.
- `SimulationReport`: reactions, themes, risks, image impact, suggestions, assumptions, uncertainty, and run metadata.

Add validation for incomplete or contradictory inputs. Make it clear which fields are required for the MVP and which are optional.

**Exit criteria:** The backend can accept a valid scenario, reject invalid scenarios with useful errors, and serialise a stable report shape for the frontend.

### Work package 2 — Indian persona pack

**Purpose:** Create useful, editable audience representations without turning demographic labels into stereotypes.

Tasks:

- Define a persona template format with background, goals, constraints, media habits, language style, likely concerns, and uncertainty notes.
- Create eight to ten initial personas spanning the first target segment, not a generic “average Indian” audience.
- Include regional, language, age, occupation, and city-tier context only when it changes the research question.
- Add an editorial review checklist for cultural plausibility, respectful representation, and unsupported assumptions.
- Keep persona data inspectable and editable by users or maintainers.
- Separate persona attributes from sensitive-attribute inference; do not imply that a persona represents an entire community.

**Exit criteria:** A maintainer can inspect, edit, version, and select the persona pack used in a run, and the report identifies which personas contributed to each theme.

### Work package 3 — Simulation and provider layer

**Purpose:** Adapt the existing simulation engine to MiroInd’s research workflow.

Tasks:

- Add a MiroInd scenario adapter around the existing simulation pipeline rather than duplicating the engine.
- Implement the first platform-style interaction as a simulation format, not a connection to a real platform.
- Add prompt templates for English and Hindi analysis, with explicit instructions to distinguish observation, interpretation, and speculation.
- Preserve model/provider configurability for OpenAI-compatible endpoints and future local Ollama use.
- Record provider, model, prompt/template version, persona set, configuration, and budget in each run.
- Evaluate local graph-memory options before committing to one implementation; compare operational complexity, persistence, inspection, and offline behaviour.
- Keep Zep Cloud support available only as an explicit optional dependency while a local-first path is evaluated.

**Exit criteria:** A fictional scenario can run with a configured provider, produce inspectable interactions, stop at its budget limit, and fail safely when credentials or dependencies are missing.

### Work package 4 — Report synthesis

**Purpose:** Turn simulated discussion into actionable but appropriately cautious feedback.

The report should use sections aligned with the project document:

1. Scenario and audience summary
2. Short overall assessment
3. Likely image impact and reasoning
4. What may work well
5. Risk points and possible misreadings
6. Reactions by persona or audience subgroup
7. Areas of agreement and disagreement
8. Recommended changes, prioritised by impact and effort
9. Optional rewrites constrained by the brand profile
10. Assumptions, uncertainty, limitations, and validation questions
11. Run metadata and usage/cost information

Avoid reducing the output to a single sentiment score. If directional labels or confidence indicators are used, define them as simulation signals rather than measured audience facts.

**Exit criteria:** A user can understand what the system observed, what it inferred, why it made each recommendation, and what should be checked with real people.

### Work package 5 — Frontend workflow

**Purpose:** Make the MVP usable from the existing Vue application.

Screens or states:

1. Create or select a brand profile.
2. Enter or paste a text asset.
3. Define the target Indian audience.
4. Choose language, interaction format, and budget.
5. Review assumptions before running.
6. Show progress and recoverable errors.
7. Display the structured report with expandable evidence and metadata.
8. Allow the user to copy or export the report in a simple text/Markdown format.

Add English/Hindi switching for user-facing labels and report headings. Keep provider credentials and private configuration out of the browser and out of persisted client-side data.

**Exit criteria:** A user can complete one end-to-end fictional scenario from the browser and understand that the result is a stress test, not a prediction.

### Work package 6 — Evaluation, safety, and documentation

**Purpose:** Measure usefulness without claiming more validity than the system has.

Tasks:

- Add deterministic fixtures for schema validation, prompt construction, report parsing, budget enforcement, and failure handling.
- Add end-to-end tests using mocked model responses so the test suite works offline.
- Create three or four fictional Indian demo scenarios, such as a regional-language app launch or a hypothetical pricing update.
- Create a review rubric for specificity, non-obviousness, cultural plausibility, actionable suggestions, and transparency.
- Document known failure modes: hallucination, translation errors, persona flattening, model bias, overconfident synthesis, and unrealistic social dynamics.
- Add explicit data-handling guidance: do not upload private WhatsApp messages or personal data without a lawful basis and informed permission.
- Describe the boundary between simulation formats and real platform integrations.

**Exit criteria:** The repository has offline tests, safe example inputs, documented limitations, and a repeatable way to compare report quality over time.

## 4. Delivery sequence

The recommended order is:

1. Reproducible baseline and architecture review
2. Domain schemas and API contracts
3. Persona format and initial persona pack
4. Simulation adapter and first interaction format
5. Report synthesis and metadata
6. Frontend end-to-end flow
7. Offline tests, demo scenarios, safety review, and documentation
8. Small human review with native Hindi speakers and representative domain reviewers

Do not begin regional-language expansion, video support, or multiple platform formats until the first text-only workflow produces consistently understandable reports.

## 5. Success measures for the first release

The MVP is successful if:

- Users can complete a scenario without needing to understand the internal agent architecture.
- Reports identify specific, non-obvious risks rather than generic marketing advice.
- Suggestions remain within the stated brand constraints.
- Reports expose disagreement and uncertainty instead of presenting false consensus.
- Users can reproduce a run configuration and see its estimated usage.
- The product clearly separates synthetic exploration from real audience evidence.
- Native-language reviewers judge Hindi output as understandable and appropriately cautious for the tested scenarios.
- Offline automated tests cover core validation and report behaviour.

These measures evaluate product usefulness and transparency; they are not claims that the simulator predicts market behaviour.

## 6. Key risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Personas reinforce stereotypes | Use inspectable templates, editorial review, uncertainty notes, and narrow research questions. |
| Users treat output as truth | Use prominent framing, uncertainty, evidence, and validation questions throughout the product. |
| Hindi or code-mixed output is unnatural | Start with a small evaluated scope and use native-speaker review before expanding. |
| Hosted providers expose sensitive inputs or create unexpected cost | Make provider choice and budget explicit; warn before hosted runs; provide local-first evaluation. |
| Reports become generic or flattering | Require asset-specific evidence, disagreement, and actionable risk points in the report schema. |
| Upstream changes break adaptations | Keep MiroInd-specific adapters and tests separated from upstream-compatible components. |
| Simulation is mistaken for platform access | Use neutral interaction-format names and document that no real accounts or posts are involved. |

## 7. Decisions requested before implementation

Please approve or change these recommendations:

1. **Initial user segment:** Start with Indian creators and personal brands, then generalise to startup and brand teams.
2. **Initial asset type:** Text only; defer video until the report workflow is validated.
3. **Initial language scope:** English and Hindi, with Hindi–English code-mixing treated as experimental.
4. **Initial simulation format:** One short-form post and discussion format before adding WhatsApp-style groups or other formats.
5. **Memory direction:** Evaluate a local graph-memory backend first; retain hosted Zep as an explicit optional path during the transition.
6. **Safety boundary:** No real social-platform posting, private-message ingestion, political influence tooling, or sensitive-attribute inference.
7. **Quality gate:** Do not expand scope until fictional scenarios pass the report-quality, transparency, and offline-test checks above.

## 8. Implementation outcome

The approved MVP scope is implemented as a credential-free, deterministic text
stress-test workflow. The next expansion should remain behind the quality gate:
evaluate the report with native-language reviewers before adding more platform
formats, video support, or regional-language breadth.
