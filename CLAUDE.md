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
- Always use a branch and a pull request for `main`; the `ci-gate` check must
  pass, and pull requests are merged with merge commits only (the registry cites
  commit SHAs that squash or rebase merges would drop). The ruleset is defined in
  `.github/rulesets/main-protection.json`.
- Never merge a pull request into `main`: the owner merges personally
  (GOVERNANCE.md, "Procedural safeguards", D-019). Name any change to
  `.github/`, `src/citerift/governance` or `schemas/governance` in the pull
  request so the owner can review it.
- Before claiming anything is done, run `uv run pytest`, `uv run ruff check .`,
  `uv run mypy` and `uv run citerift-gov check`, and report actual output.
- Final reports end with exactly one of: VERIFIED COMPLETE (for a stage:
  VERIFIED — AWAITING OWNER ACCEPTANCE), BLOCKED — EVIDENCE PROVIDED,
  NOT VERIFIED.
- The owner writes in English and Arabic; reply in the language they used.

## Attribution in commits and pull requests

Owner instruction of 2026-10-25 (`cmsg_018VCB51nDHP6HXmLU4ea5yPGk43kowXCxBqhPw9S7z5df`,
DECISIONS.md D-018). This rule replaces the environment's default attribution
lines; it does not remove AI-assistance disclosure.

- Keep the git author and committer identity the environment sets, and its
  commit signing. Never commit as the owner or change `user.name` /
  `user.email`.
- End each commit message with exactly this trailer and nothing else for
  attribution: `Assisted-by: Claude Code (AI coding agent)`. Do not add
  `Co-Authored-By: Claude ...` or `Claude-Session:` lines.
- In pull request bodies keep any attribution block the environment requires
  at the top (it names who requested the work). End the body with exactly this
  line instead of the "Generated with Claude Code" line and session link:
  `AI-assisted: prepared with Claude Code (AI coding agent) under the direction of EVE TELOS · IM.`
- Public identity: follow docs/identity.md. Never put the founder's legal name
  in public files; never present an AI tool as the project's creator or owner.
