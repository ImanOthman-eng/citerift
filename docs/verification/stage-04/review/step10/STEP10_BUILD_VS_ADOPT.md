# Stage 04 Step 10: Build-vs-Adopt review (command line, rendering, export)

Owner Step 10 instruction (`cmsg_018VCB51nDHP6HXmLU4ea5yPSW7jXkQV4o696BLytWfZux`, item 2) and the permanent
Open-Source Leverage rule (owner, 2026-11-10). The default is no new dependency; a candidate is adopted only for a
concrete need the standard library does not meet.

Method. Each third-party candidate was installed in a scratch virtual environment outside the project (Python 3.12,
`uv venv`), never in the project; versions, licences, declared requirements and Python bounds are read from the
installed metadata and the PyPI JSON API (2026-11-16); import times are `python -X importtime` cumulative times on
this container (one warm run; they vary by a few milliseconds); `pip-audit` was run over the candidates and their
resolved dependencies ("No known vulnerabilities found", 2026-11-16). [limit] Open issues and repository activity
were not read (the GitHub API in this session is limited to this repository), so maintenance is judged from release
history only. The project has no licence chosen yet; every licence below is permissive, so no candidate needed an
owner decision on copyleft.

## Needs

1. Parse seven subcommands with typed options, mutually exclusive inputs and usage errors on exit code 2.
2. Print text and JSON with a stable shape and one exit-code table.
3. Render fixed explanation templates (S-12.2: no free text, byte-identical output).
4. Write files and directories safely (no symlink following, no overwrite, atomic rename, fsync).
5. Shell completion was considered and is not needed: the owner did not ask for it, and the CLI is driven by scripts
   and tests.

## Candidates

| Field | argparse (stdlib) | Click | Typer | Cyclopts |
|---|---|---|---|---|
| Repository | CPython `Lib/argparse.py` | github.com/pallets/click | github.com/fastapi/typer | github.com/BrianPugh/cyclopts |
| Capability | subcommands, typed options, groups, usage errors | decorators, groups, completion, testing runner | type-hint CLI on its own core, completion, rich help | type-hint CLI, rich help |
| Release | ships with Python 3.12 / 3.13 | 8.5.1 (2026-11-06) | 0.29.1 (2026-11-11) | 5.5.1 (2026-11-16) |
| Licence | PSF-2.0 | BSD-3-Clause | MIT | Apache-2.0 |
| Transitive licences | none | none (0 dependencies) | pydantic 2.14.3 (MIT), pydantic-core (MIT), annotated-types (MIT), typing-extensions (PSF-2.0), typing-inspection (MIT), shellingham (ISC), rich (MIT), markdown-it-py (MIT), mdurl (MIT), Pygments (BSD-2-Clause), annotated-doc (MIT): 12 packages | attrs (MIT), docstring-parser (MIT), rich-rst (MIT), rich and its tree |
| Maintenance (release history) | CPython | frequent releases | frequent releases, 0.x | frequent releases |
| Security | CPython | pip-audit clean | pip-audit clean (12 packages to watch) | pip-audit clean |
| 3.12 / 3.13 | yes / yes | `>=3.10` | `>=3.10` | `>=3.11` |
| Cost | none | none | none | none |
| Reproducibility | fixed by the interpreter | one pinned wheel | twelve pinned wheels incl. a compiled `pydantic-core` | several pinned wheels |
| Network | none | none | none | none |
| Import time (cumulative) | 6.6 ms | 30 ms | 92 ms | not measured (rich alone 12 ms) |
| Complexity saved | none needed | decorators instead of ~40 lines of parser code | the same, by type hints | the same |
| Complexity added | none | a dependency and its exit-code conventions to override (Click exits 2 on usage, 1 on `ClickException`; our table must be exact) | pydantic and rich in the runtime of a scientific tool, coloured output to disable for byte-stable text | the same as Typer |
| Testability | `main(argv)` called in process; `SystemExit` mapped | `CliRunner` | `CliRunner` | its own runner |
| Versus internal | baseline | no need it meets that argparse does not | none | none |
| Decision | **ADOPT (stdlib baseline)** | REJECT | REJECT | REJECT |

For scale: importing `citerift.investigation.cli` costs about 245 ms on this container, almost all of it the
project's own modules (schemas, Stage 02 and Stage 03 engines). The framework choice moves start-up by at most a few
tens of milliseconds and buys no capability the command needs.

## Rendering and output

| Candidate | Version, licence | Need | Decision |
|---|---|---|---|
| Jinja2 | 3.1.6 (2025-03-05), BSD-3-Clause by classifier (the PyPI licence field is empty), requires MarkupSafe | fixed sentences with a few fields | REJECT: a template language, auto-escaping rules and a sandbox question for sentences that `str.format` over fixed strings renders exactly; S-12.2 wants the templates as reviewable constants in one module (`explanations.py`) |
| Rich | 15.0.0 (2026-04-12), MIT, requires markdown-it-py and Pygments | coloured tables | REJECT: terminal styling makes text output depend on the terminal; the text output is plain and the JSON output is the stable contract |
| `string.Template` / `str.format` | stdlib | fixed templates | ADOPT (stdlib) |
| `json` (stdlib) and the Stage 04 canonical encoder | stdlib / internal | JSON output, canonical checkpoint bytes | ADOPT (existing) |
| `os` (`O_EXCL`, `O_NOFOLLOW`, `dir_fd`, `fsync`, `rename`, `link`) and the Stage 04 `fsutil` | stdlib / internal | safe writes | ADOPT (existing). `atomicwrites` (MIT; last release 1.4.1 on 2022-07-08, none since) was REJECTED: no release in four years and no refusal of a target inside a given root; `tempfile` + `os.replace` alone does not refuse a symlinked target or keep "no overwrite" without a race, which `os.link` gives |

## Result

No new dependency: `pyproject.toml` gains only the `citerift-investigate` console-script entry, and `uv.lock`
records no new package (`uv lock --check` passes). Nothing was installed in the project environment.
