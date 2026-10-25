# Instructions for Claude Code sessions in this repository

Read GOVERNANCE.md first. It is the authoritative copy of the owner's rules.

Start every session with:

```
uv sync --locked
uv run citerift-gov recover
uv run citerift-gov check
```

- Work only on what the owner explicitly authorized in the current instruction.
  The registry (`governance/stage_registry.json`) shows what is authorized;
  `recover` prints it. Never authorize or accept a stage yourself, and never
  record an owner decision without a reference to the owner's own words.
- Stage 01 belongs to a separate external agent. Never duplicate, predict or
  invent its findings.
- Change stage state only through `citerift-gov transition ... --apply`, then
  commit the registry and `PROJECT_STATUS.md` together.
- `main` is protected: use a branch and a pull request; the `ci-gate` check
  must pass.
- Before claiming anything is done, run `uv run pytest`, `uv run ruff check .`,
  `uv run mypy` and `uv run citerift-gov check`, and report actual output.
- Final reports end with exactly one of: VERIFIED COMPLETE (for a stage:
  VERIFIED — AWAITING OWNER ACCEPTANCE), BLOCKED — EVIDENCE PROVIDED,
  NOT VERIFIED.
- The owner writes in English and Arabic; reply in the language they used.
