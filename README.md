# MiroInd 🇮🇳

### Simulate India's conversations. Before you launch.

**An open-source, India-focused multi-agent simulation project for exploring how different communities might respond to a product, policy, or campaign.**

Hindi-first experiences. Regional perspectives. Local-first memory. Built with Indian founders, researchers, and developers in mind.

[Vision](#why-miroind) · [Use cases](#what-could-you-explore) · [Roadmap](#roadmap) · [Contribute](#contribute)

> **Status: upstream foundation imported; India-specific adaptations planned.** This repository includes the MiroFish Vue frontend, Flask backend, simulation engine, and tests. The Hindi-first experience, Indian persona packs, additional platform simulations, and local graph memory described below are roadmap items—not implemented yet. The current engine requires an LLM provider and Zep Cloud credentials.

---

## Why MiroInd?

India is not one audience.

A pricing change can land differently with a student in Pune, a shop owner in Jaipur, a commuter in Chennai, and a creator in Lucknow. Language, local context, affordability, and the platform where a conversation starts all matter.

MiroInd aims to make those differences easier to explore through transparent, configurable agent-based simulations—without making cloud-only infrastructure the default.

**The idea:** provide a scenario, configure a synthetic audience, simulate conversations, and inspect the assumptions and possible outcomes.

**The goal is exploration, not prediction.** Simulated agents are not real people, a representative survey, or evidence of what India actually thinks.

## What we're building

| Focus | Planned direction |
| --- | --- |
| **India-native personas** | Editable synthetic persona packs organized by state, language, age, occupation, income band, and city tier. |
| **Hindi-first experience** | Hindi and English interfaces, prompts, and reports, followed by Tamil, Telugu, Marathi, and Bengali. |
| **Natural code-mixing** | Support for Hindi–English conversations and, later, additional regional language combinations. |
| **Platform-aware conversations** | Simulated Instagram-style posts and Reels discussions, WhatsApp-style groups and forwarding, ShareChat/Moj-style interactions, plus X and Reddit. |
| **Local-first graph memory** | Evaluate Neo4j with Graphiti or Kuzu as local memory options, rather than requiring a hosted memory service. |
| **Flexible model providers** | Plan for OpenAI-compatible endpoints such as Groq, Together, and Fireworks, alongside local Ollama models. Regional-language quality will need evaluation. |
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

How might language and local context change the interpretation of a creator's message? Explore alternative explanations before testing content with real audiences.

### Early-stage market research

Use synthetic conversations to generate interview questions and product hypotheses—not to replace focus groups, representative research, or community consultation.

## Planned starter scenarios

| Scenario | Example research question |
| --- | --- |
| **Hypothetical UPI merchant fee** | What concerns might small merchants and customers raise about a proposed fee? |
| **Free bus travel scheme for women** | How might commuters discuss affordability, access, safety, and implementation? |
| **Ride-hailing price competition** | How might riders and drivers weigh lower fares against reliability and earnings? |
| **Regional-language app launch** | What onboarding and trust questions could arise for first-time users? |
| **GST-related pricing update** | How might customers interpret a price change, and what explanation would be clearer? |
| **Cricket sponsorship controversy** | How might different fan communities interpret a fictional brand response? |

All starter scenarios should use fictional or clearly labeled hypothetical inputs. They must not imply that a proposed charge, rule, or controversy is a real event.

## Proposed workflow

```mermaid
flowchart TD
    A[Define a scenario and research question] --> B[Select synthetic audience and languages]
    B --> C[Choose model provider and usage budget]
    C --> D[Run platform-style agent conversations]
    D --> E[Store interactions in local graph memory]
    E --> F[Inspect themes, disagreements, and uncertainty]
    F --> G[Export findings and validate with real research]
```

### Design principles

- **Local-first, not local-only.** Aim to keep scenario data and memory on your machine by default, with optional hosted providers.
- **Transparent assumptions.** Persona templates and model configuration should be inspectable and editable.
- **Language quality over checkbox support.** Evaluate regional-language outputs with native speakers.
- **Reproducible where possible.** Record configuration, prompts, and seeds while acknowledging model nondeterminism.
- **Cost visibility.** Make agent counts, model usage, and budget limits explicit.

Using a hosted model sends submitted prompts and context to that provider and may incur charges. Local graph storage alone does not make a workflow fully offline or private; fully local operation would also require a local model and local supporting services.

## Roadmap

### Phase 1 — Establish the foundation

- [x] Import the MiroFish foundation with its AGPL-3.0 license and upstream attribution.
- [ ] Evaluate the architecture for India-specific adaptations.
- [ ] Document the implementation stack and a minimal runnable simulation.
- [ ] Add Hindi and English prompts and report templates.
- [ ] Create 8–10 editable Indian synthetic persona templates.
- [ ] Prototype Instagram-style, WhatsApp-style, and X-style interactions.
- [ ] Select and implement a local graph-memory backend.
- [ ] Add 3–4 documented Indian demo scenarios.

### Phase 2 — Build India-specific depth

- [ ] Support Hindi–English code-mixed agent conversations.
- [ ] Add state-level and regional audience comparisons.
- [ ] Model group participation, forwarding, and status-style sharing.
- [ ] Build a web UI with Hindi/English switching.
- [ ] Evaluate Tamil, Telugu, Marathi, and Bengali support.
- [ ] Publish evaluation methods and known simulation limitations.

### Phase 3 — Make it easy to run and inspect

- [ ] Provide Docker-based setup with a local-model option.
- [ ] Add a smaller, budget-friendly quick-simulation mode.
- [ ] Export Hindi and English reports, including PDF.
- [ ] Add configuration capture and experiment comparisons.
- [ ] Publish contributor documentation and reproducible examples.

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

```sh
npm run dev
```

This starts the backend and frontend together. Use the frontend URL printed by Vite; the backend defaults to port **5001**. Full simulation functionality requires valid credentials. The imported application still uses upstream branding, prompts, and Twitter/X + Reddit simulation behavior.

### Validate

```sh
npm run build
uv run --project backend python -m pytest backend/tests tests
```

See [the original MiroFish README](./README.upstream.md) for upstream usage and Docker instructions. Its deployment links and container images refer to the upstream project, not an India-adapted release.

## Contribute

We welcome help from developers, native-language reviewers, researchers, designers, and maintainers.

High-value early contributions include:

- Reviewing the architecture and local-memory tradeoffs.
- Writing fictional, well-documented Indian starter scenarios.
- Designing persona templates that avoid demographic stereotypes.
- Evaluating Hindi and regional-language model behavior.
- Defining tests for cost, reproducibility, and simulation limitations.
- Designing a clear bilingual research interface.

Please open an issue before starting substantial implementation so the scope and direction can be agreed on.

## Inspiration and licensing

MiroInd is based on [MiroFish by 666ghj and its contributors](https://github.com/666ghj/MiroFish). The source was imported from upstream `main` at commit [`7657031ac01184afe2cb220f5ee3545573b5e843`](https://github.com/666ghj/MiroFish/commit/7657031ac01184afe2cb220f5ee3545573b5e843). The original documentation is preserved in [README.upstream.md](./README.upstream.md) and [README-ZH.md](./README-ZH.md). MiroInd does not claim affiliation with or endorsement by the upstream maintainers.

The imported code is licensed under the **GNU Affero General Public License v3.0**; see [LICENSE](./LICENSE). Preserve upstream copyright, attribution, and license notices. Distribution and network deployment of modified versions must comply with the AGPL, including applicable corresponding-source requirements.

The import retains the upstream application unchanged; this README documents the MiroInd direction and local setup. The Git remote `origin` points to MiroInd, while `upstream` points to MiroFish for future reference. Source history remains available through the upstream remote; the files were imported as a snapshot, not a merge of Git histories.

---

**Built around India's languages, contexts, and questions—with assumptions you can inspect.**
