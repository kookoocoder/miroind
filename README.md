# BOSS 🇮🇳

### Brand Outcome Signal System — understand India before you launch.

**An open-source, India-focused multi-agent simulation project for exploring how different communities might respond to a product, policy, or campaign.**

India-first experiences. Regional perspectives. Local-first memory. Built with Indian founders, researchers, and developers in mind.

[Vision](#why-miroind) · [Use cases](#what-could-you-explore) · [Roadmap](#roadmap) · [Contribute](#contribute)

> **Status: MiroInd MVP slice available.** This repository includes the upstream MiroFish Vue frontend, Flask backend, simulation engine, and a credential-free MiroInd text stress-test workflow. The MVP accepts a brand profile, text asset, and Indian audience lens at `/miroind`, then returns a deterministic structured report. The upstream graph/simulation workflow still requires an LLM provider and Zep Cloud credentials.

---

## Why MiroInd?

India is not one audience.

A pricing change can land differently with a student in Pune, a shop owner in Jaipur, a commuter in Chennai, and a creator in Lucknow. Region, local context, affordability, occupation, city tier, and the platform where a conversation starts all matter. Language can be one signal; it is not the product boundary.

MiroInd aims to make those differences easier to explore through transparent, configurable agent-based simulations—without making cloud-only infrastructure the default.

**The idea:** provide a scenario, configure a synthetic audience, simulate conversations, and inspect the assumptions and possible outcomes.

**The goal is exploration, not prediction.** Simulated agents are not real people, a representative survey, or evidence of what India actually thinks.

## What we're building

| Focus | Planned direction |
| --- | --- |
| **India-native personas** | Editable synthetic persona packs organized by state or region, age, occupation, income band, city tier, and local context. |
| **India context first** | Model regional, economic, occupational, cultural, and platform context together instead of reducing an audience to a language label. |
| **Optional local expression** | Capture language, phrasing, and code-mixing when they materially affect the research question—not as a requirement for every scenario. |
| **Platform-aware conversations** | Simulated Instagram-style posts and Reels discussions, WhatsApp-style groups and forwarding, ShareChat/Moj-style interactions, plus X and Reddit. |
| **Local-first graph memory** | Evaluate Neo4j with Graphiti or Kuzu as local memory options, rather than requiring a hosted memory service. |
| **Flexible model providers** | Plan for OpenAI-compatible endpoints such as Groq, Together, and Fireworks, alongside local Ollama models. India-specific context quality will need evaluation. |
| **Inspectable results** | Reports that expose persona assumptions, model choices, simulation settings, and uncertainty—not just a single sentiment score. |
| **Affordable experimentation** | A lightweight quick-simulation mode, configurable agent counts, and explicit usage budgets. |

These are design targets, not current capabilities. Platform names describe intended simulation formats; no official platform integration or affiliation is implied.

## What could you explore?

### Product and pricing

How might a subscription price change affect students, gig workers, and small businesses across city tiers? What objections should a team investigate with real users?

### Public policy research

What questions, misunderstandings, or accessibility concerns might arise around a proposed scheme? Compare clearly documented scenarios without treating the output as polling or an election forecast.

### Brand and crisis communication

How could the same announcement be interpreted in a short-form video discussion versus a private group conversation? Which wording deserves further human review?

### Creator and content research

How might state, city tier, occupation, affordability, and local context change the interpretation of a creator's message? Explore alternative explanations before testing content with real audiences.

### Early-stage market research

Use synthetic conversations to generate interview questions and product hypotheses—not to replace focus groups, representative research, or community consultation.

## Planned starter scenarios

| Scenario | Example research question |
| --- | --- |
| **Hypothetical UPI merchant fee** | What concerns might small merchants and customers raise about a proposed fee? |
| **Free bus travel scheme for women** | How might commuters discuss affordability, access, safety, and implementation? |
| **Ride-hailing price competition** | How might riders and drivers weigh lower fares against reliability and earnings? |
| **Regional service launch** | What onboarding, trust, access, and local-fit questions could arise for first-time users? |
| **GST-related pricing update** | How might customers interpret a price change, and what explanation would be clearer? |
| **Cricket sponsorship controversy** | How might different fan communities interpret a fictional brand response? |

All starter scenarios should use fictional or clearly labeled hypothetical inputs. They must not imply that a proposed charge, rule, or controversy is a real event.

## Proposed workflow

```mermaid
flowchart TD
    A[Define a scenario and research question] --> B[Define Indian audience context]
    B --> C[Choose model provider and usage budget]
    C --> D[Run platform-style agent conversations]
    D --> E[Store interactions in local graph memory]
    E --> F[Inspect themes, disagreements, and uncertainty]
    F --> G[Export findings and validate with real research]
```

### Design principles

- **Local-first, not local-only.** Aim to keep scenario data and memory on your machine by default, with optional hosted providers.
- **Transparent assumptions.** Persona templates and model configuration should be inspectable and editable.
- **Context quality over checkbox support.** Evaluate regional, economic, occupational, and cultural assumptions with people who know the audience.
- **Reproducible where possible.** Record configuration, prompts, and seeds while acknowledging model nondeterminism.
- **Cost visibility.** Make agent counts, model usage, and budget limits explicit.

Using a hosted model sends submitted prompts and context to that provider and may incur charges. Local graph storage alone does not make a workflow fully offline or private; fully local operation would also require a local model and local supporting services.

## Roadmap

### Phase 1 — Establish the foundation

- [x] Import the MiroFish foundation with its AGPL-3.0 license and upstream attribution.
- [x] Evaluate the architecture for India-specific adaptations.
- [x] Document the implementation stack and a minimal runnable simulation.
- [x] Add baseline deterministic report templates with optional Hindi output.
- [x] Create 8–10 editable Indian synthetic research-lens templates.
- [x] Prototype a short-form post/discussion interaction format.
- [ ] Select and implement a local graph-memory backend.
- [x] Add 3 documented fictional Indian demo scenarios.

### Phase 2 — Build India-specific depth

- [ ] Support Hindi–English code-mixed agent conversations.
- [ ] Add state-level and regional audience comparisons.
- [ ] Model group participation, forwarding, and status-style sharing.
- [ ] Build a web UI with Hindi/English switching.
- [ ] Evaluate Tamil, Telugu, Marathi, and Bengali support.
- [ ] Publish evaluation methods and known simulation limitations.

### Phase 3 — Make it easy to run and inspect

- [ ] Provide Docker-based setup with a local-model option.
- [x] Add a smaller, budget-friendly deterministic quick-simulation mode.
- [ ] Export Hindi and English reports, including PDF.
- [ ] Add configuration capture and experiment comparisons.
- [x] Publish contributor documentation and reproducible examples.

Milestones are directional; no release dates or performance claims are promised yet.

## Responsible use

MiroInd is intended for research, learning, and testing hypotheses—not manufacturing public opinion.

- **Do not treat synthetic output as public sentiment, polling, or a forecast.** Validate findings through appropriate real-world research.
- **Do not stereotype communities.** Avoid inferring beliefs or behavior from caste, religion, language, or other sensitive characteristics. Any research involving sensitive attributes needs explicit justification, safeguards, and review.
- **Do not use it for deceptive influence.** The project is not intended for impersonation, astroturfing, harassment, voter suppression, or targeted political manipulation.
- **Use synthetic or appropriately consented inputs.** Do not upload private WhatsApp conversations or personal data without a lawful basis and informed permission.
- **Keep simulation separate from publishing.** Proposed platform adapters model interaction patterns; they are not tools for posting to real accounts.
- **Document limitations.** LLM bias, unrealistic personas, translation errors, and simplified social dynamics can all distort results.

## Getting started

### Prerequisites

- **Node.js 20.19+ or 22.12+** for the imported Vite 7 frontend.
- **Python 3.11 or 3.12** (Python 3.13 is not supported by the backend).
- **uv** for Python dependency management.
- An **OpenAI-compatible LLM endpoint** and a **Zep Cloud API key** for full simulations.

### Install

From the repository root:

```sh
npm ci
npm --prefix frontend ci
uv sync --project backend --python 3.12
cp .env.example .env
```

Edit the local `.env` file to configure `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL_NAME`, and `ZEP_API_KEY`. Never commit secrets or personal datasets. The example configuration retains upstream provider defaults; select your provider explicitly. Hosted models and Zep may incur costs and receive submitted scenario data.

### Run locally

For the credential-free MiroInd MVP:

```sh
npm run dev:miroind
```

Open **http://localhost:3000/miroind**. This mode starts the frontend and backend without LLM or Zep credentials. Runs are stored under `backend/uploads/miroind/runs/` and are ignored by git.

### Optional model-backed BOSS reviews

OpenCode is installed as a project-local CLI dependency. BOSS can use its
configured model account for a second review view. It can also call an
OpenAI-compatible endpoint directly when `BOSS_MODEL_PROVIDER=direct`.

```sh
npm run opencode:models
```

To enable model-backed reviews with the configured provider:

```sh
export BOSS_MODEL_ENABLED=true
export BOSS_MODEL_PROVIDER=opencode
export BOSS_MODEL_NAME=omnirush/gpt-6-astra
npm run dev:boss-model
```

The offline mode remains the default and never makes model calls. Do not commit
provider keys. Check the available OpenCode models with `npm run
opencode:models`. For a direct DeepSeek-compatible endpoint, use
`BOSS_MODEL_PROVIDER=direct`, `BOSS_MODEL_API_KEY`,
`BOSS_MODEL_BASE_URL=https://api.deepseek.com/v1`, and
`BOSS_MODEL_NAME=deepseek-chat`.

For the original graph/simulation workflow, configure valid credentials in `.env` and use:

```sh
npm run dev
```

This starts the backend and frontend together. Use the frontend URL printed by Vite; the backend defaults to port **5001**. The imported application uses upstream graph, prompts, and Twitter/X + Reddit simulation behavior.

The equivalent Make target is:

```sh
make run-miroind
```

### Docker

Build and run the local MiroInd image without provider credentials:

```sh
docker compose up --build
```

Open **http://localhost:3000/miroind**. Set `MIROIND_OFFLINE_ONLY=false` and provide provider credentials when running the upstream graph/simulation workflow.

### Validate

```sh
make test
```

This runs the production frontend build and the offline-capable backend test suite. The individual commands are `npm run build` and `uv run --project backend python -m pytest backend/tests tests`.

See [the original MiroFish README](./README.upstream.md) for upstream usage and Docker instructions. Its deployment links and container images refer to the upstream project, not an India-adapted release.

## Contribute

We welcome help from developers, native-language reviewers, researchers, designers, and maintainers.

High-value early contributions include:

- Reviewing the architecture and local-memory tradeoffs.
- Writing fictional, well-documented Indian starter scenarios.
- Designing persona templates that avoid demographic stereotypes.
- Evaluating India-context and local-expression model behavior.
- Defining tests for cost, reproducibility, and simulation limitations.
- Designing a clear bilingual research interface.

Please open an issue before starting substantial implementation so the scope and direction can be agreed on.

## Inspiration and licensing

MiroInd is based on [MiroFish by 666ghj and its contributors](https://github.com/666ghj/MiroFish). The source was imported from upstream `main` at commit [`7657031ac01184afe2cb220f5ee3545573b5e843`](https://github.com/666ghj/MiroFish/commit/7657031ac01184afe2cb220f5ee3545573b5e843). The original documentation is preserved in [README.upstream.md](./README.upstream.md) and [README-ZH.md](./README-ZH.md). MiroInd does not claim affiliation with or endorsement by the upstream maintainers.

The imported code is licensed under the **GNU Affero General Public License v3.0**; see [LICENSE](./LICENSE). Preserve upstream copyright, attribution, and license notices. Distribution and network deployment of modified versions must comply with the AGPL, including applicable corresponding-source requirements.

The import retains the upstream application unchanged; this README documents the MiroInd direction and local setup. The Git remote `origin` points to MiroInd, while `upstream` points to MiroFish for future reference. Source history remains available through the upstream remote; the files were imported as a snapshot, not a merge of Git histories.

---

**Built around India's regions, contexts, and questions—with assumptions you can inspect.**
