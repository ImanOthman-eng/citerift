# CITERIFT

*CITERIFT — Created and Directed by EVE TELOS · IM*

**A multilingual scientific citation integrity platform.** CITERIFT investigates
citations to retracted scientific papers across Wikipedia language editions,
traces their context and history, compares how different editions respond, and
produces source-backed evidence for human review.

Research question: *How consistently and how quickly do different Wikipedia
language editions respond to scientific paper retractions?*

CITERIFT never treats a citation to a retracted paper as proof that the citing
claim is false, and it never claims complete Wikipedia coverage without
evidence. Built for the STEM2Connect AI Hackathon 2026.

## Status

Development is stage-gated: ten stages (00 to 09), each verified with evidence
and accepted by the project owner before the next one is authorized. Current
state: [PROJECT_STATUS.md](PROJECT_STATUS.md) (generated from
[`governance/stage_registry.json`](governance/stage_registry.json)).

What exists today is **Stage 00, the engineering foundation**: governance
tooling, persistent project memory, versioned data contracts, tests and CI.
There is no retraction data, Wikipedia extraction, AI model or user interface
yet; those are Stages 02 to 08.

## Quick start

Requirements: Python 3.12 or 3.13 and [uv](https://docs.astral.sh/uv/) 0.11.

```bash
uv sync --locked                 # create .venv from the committed lockfile
uv run citerift-gov recover      # reconstruct project state from the repository
uv run citerift-gov check        # validate registry, history, evidence and memory
uv run pytest                    # full test suite
```

More: [docs/development.md](docs/development.md).

## Repository map

| Path | Purpose |
|---|---|
| `src/citerift/governance/` | Project Orchestrator and Persistent Project Memory checks (`citerift-gov`) |
| `src/citerift/contracts/` | Contract loading, validation and compatibility checks (`citerift-contracts`) |
| `schemas/contracts/v1/` | Versioned data contracts (JSON Schema 2020-12) |
| `schemas/governance/` | Schema of the stage registry |
| `governance/stage_registry.json` | Canonical machine-readable project state and history |
| `simulations/stage00/` | Pre-implementation simulation of the governance state machine |
| `tests/stage00/` | Stage 00 tests |
| `docs/` | Architecture, contracts, sources policy, setup, stage verification packages |
| `GOVERNANCE.md`, `DECISIONS.md`, `RISKS.md`, `CHANGELOG.md` | Rules and persistent engineering memory |
| `OWNERSHIP.md`, `docs/identity.md` | Ownership, decision authority, attribution and identity standard |

## Architecture

Project governance layer (Stage 00): Project Orchestrator and Persistent Project
Memory. Application layers (later stages): retraction data, Wikipedia
extraction, detection, citation context, AI investigation, cross-wiki
intelligence with a FastAPI backend, and a React + Cytoscape.js frontend. See
[docs/architecture.md](docs/architecture.md).

## Data sources and attribution

Planned sources are the Crossref Retraction Watch data and the Wikimedia APIs.
Rules for provenance, attribution and licensing:
[docs/sources-and-attribution.md](docs/sources-and-attribution.md).

## Ownership and attribution

CITERIFT is an independent research and engineering project, created and
directed by EVE TELOS · IM. The owner sets its research direction and makes
every acceptance decision. It is built with AI engineering assistance (Claude
Code), used as a tool under the owner's direction and disclosed in commits,
pull requests and the final report. Details: [OWNERSHIP.md](OWNERSHIP.md) and
the identity standard in [docs/identity.md](docs/identity.md).

## License

Not yet chosen; a pending owner decision (see DECISIONS.md, D-007). Until a
license is added, no reuse rights are granted.
