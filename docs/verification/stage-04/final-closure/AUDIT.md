# Stage 04 non-passing final closure audit

Owner instruction `cmsg_018VCB51nDHP6HXmLU4ea5yPCrAWa1AotYwE4STJgegth4` (D-079 to D-082). Evidence finalization, not
scientific acceptance: Stage 04 stays BLOCKED (B-04-001, gate 04-I NOT PASSED under P2). No scientific artifact was
rewritten (section 3).

Audited candidate: `49c7a5839d641459f56b2e8be01236604a967ac1` (governance blocker and transition, handoff, audit tools).
Items 1–13 are computed by `closure_audit.py` (result `AUDIT.json`, `head` = the candidate); items 15–25 were run on the
same revision (output `evidence/static_checks.txt`, `SECRET_SCAN.json`). Item 14 (the full test matrix) is recorded,
with its CI runs, in `TEST_RUNS.md` of the commit that follows this one.

## 1. Results

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Reproduce `SCORES.json` byte for byte from the immutable retained inputs | **PASS** | `p2_score.py` on a copy of the campaign (outside the repository) with the exports and Investigation Memory extracted from `run/run-archive.tar.gz`, run at the scoring-time revision `7284214` (detached worktree): SHA-256 `1d674dfe…ec67` = committed. Run at a later revision the only difference is the operational field `engine_identity.head` (the checkout's HEAD), which the scorer records. |
| 2 | P2 digest and every listed file | **PASS** | `PREREGISTRATION_MANIFEST.json` digest and a rebuild (`p2_manifest.build`) both `5d323a67…f75a`; 28 listed files, 0 changed. |
| 3 | Seed and draw identities | **PASS** | Round 34096937 = the registered rule on 12:16:15Z; three mirrors' randomness = SHA-256 of the signature and agree (cloudflare 403); seed `b4566639…4e6c` recomputed; the draw plan recomputed from the frame and seed equals `DRAW.json` (`4efdb7bf…226d`). |
| 4 | Acquisition log and exposure-v2 non-overlap | **PASS** | Attempts 1–100 contiguous, 100 acquired (ar S1 42, S2 8; en S1 42, S2 8), every one a drawn position, one bundle each; 0 overlap with the 378 exposure-v2 articles (page id and normalized title) and 0 with the 80 articles of evaluation 1; exposure manifest hash `b2a2a937…` as pinned. |
| 5 | Packet hashes | **PASS** | All 100 packets hold their locked hashes; every packet and every Stage 03 extraction rebuilt from its committed bundle with the pre-registered `p2_packets.packet` is byte-identical to the committed file. |
| 6 | A/B/ADJ labels and `LOCK.json` | **PASS** | Each round's A, B and ADJ file re-combined from its instance files, each round lock rebuilt with `p2_labels.lock` (format, completeness, disagreement and adjudication rules) and the campaign lock re-merged: all byte-identical; 167 items, 10 adjudicated; lock `92a4f640…3961`. |
| 7 | Labels locked before `RUN.json` | **PASS** | `LOCK.json` added once, in `7284214` (15:16:37Z), an ancestor of `44a8479`, which added `RUN.json`; `RUN.json` records HEAD `7284214` and the lock hash; the run started 15:17:04Z. |
| 8 | Exactly one prediction-run identity | **PASS** | One `RUN.json` (`db8c5432…de3e`), committed once (`44a8479`), never modified; no other `RUN.json` in the campaign; 100 `run` commands, 0 `resume`; `PROGRESS.json` equals its articles. |
| 9 | Frozen engine `28ba646` | **PASS** | `RUN.json`, `SCORES.json` and the current checkout (`engine_check`) give content commit `28ba6467…`, tree `45c52da4…`, freeze manifest `d9db2704…`, identity 0.3.0 / dt-2 / 4.0.0 / 3.0.0 / plan-1 / `citerift-dt1-detector/3 (dt-2)`, and the same `src`, `schemas`, `pyproject.toml` and `uv.lock` trees. |
| 10 | All 100 exports and the Investigation Memory archive | **PASS** | Archive `54835a74…c7a4` extracted: its `RUN.json` and `PROGRESS.json` equal the committed ones; 100 exports, each `export.json` = the recorded hash, all 6,969 listed files present with their size and SHA-256; 100 investigations in the memory; 100 VERIFY passed; 99 COMPLETED, 1 NEEDS_RESOLUTION. |
| 11 | G1–G5 exactly as reported | **PASS** | Recomputed from `SCORES.json` with `PARAMETERS.json` and the exact bound: ar 42 / 0 of 42, 0.0688 / 0 / 0 / 766 (all pass); en 44 / 1 of 44, 0.1033 (**fail**) / 0 / 0 / 1,717. Gate 04-I NOT PASSED. |
| 12 | Baseline and sensitivity outputs | **PASS** | Inside the reproduced `SCORES.json`: baseline ar 51 (3), en 73 (22); (a) 39 (0) / 43 (1); (b) 42 (0) / 44 (1); (c) 40 (0) / 44 (1); NOT_COMPUTABLE a 0, b 0, c 87; every article passed the faithfulness self-checks. |
| 13 | All protocol deviations | **PASS** | 1 seed boundary (rounds 34096937 / 34096938 from the two timestamps; D-078); 2 one mirror 403; 3 `B-ar-p05` transcript recorded; 4 status listings not acted on (protocol log); 5 wrapper (`exit 137` is the launcher's, 100 article lines, one `run` per article, D-082; log in `evidence/p2_run.log`); 6 archive in place of raw exports; 7 transcripts of all 40 instances with original hash and line count; 8 executor glue differs from the historical one only in paths and names. |
| 14 | Full Python 3.12 and 3.13 test matrix | see `TEST_RUNS.md` | Recorded by the following commit, with its CI runs. |
| 15 | ruff | **PASS** | `ruff check .`: all checks passed. |
| 16 | format | **PASS** | `ruff format --check .`: 647 files already formatted. |
| 17 | mypy | **PASS** | `mypy`: no issues in 95 source files. |
| 18 | schemas | **PASS** | `python -m citerift.contracts.validate check-schemas`: 0 problems. |
| 19 | Step 3 checker | **PASS** | `review/step3/check_step3_docs.py .`: PASS (0 failed). |
| 20 | dt-1 and dt-2 oracle checks | **PASS** | `simulations/stage04/oracle/MANIFEST.json` `41105077…` and `oracle-dt2/MANIFEST.json` `60a21534…`, as frozen; no change under `simulations/stage04` since `28ba646`, none under `oracle/` since `b5bf8ed`; the oracle tests (`test_corrective_oracle.py`, `test_simulation_step4.py`, `test_step9_b8.py`) run in the full suite (item 14). |
| 21 | freeze-2 manifest | **PASS** | `build_freeze_manifest.py` re-run at `9028240` (its build revision) reproduces the committed `FREEZE_MANIFEST.json` byte for byte; canonical digest `d9db2704…1c13`; the file is unchanged since `28ba646`. |
| 22 | pip-audit strict | **PASS** | `pip-audit --strict --disable-pip --require-hashes` on the locked export: no known vulnerabilities; `uv lock --check` passes. |
| 23 | governance check | **PASS** | `citerift-gov check`: 0 errors, 0 warnings. |
| 24 | render-status check | **PASS** | `PROJECT_STATUS.md is up to date`. |
| 25 | secret scan | **PASS** | `secret_scan.py` (read-only; the D-036 gate's 16 patterns on the text and its percent-decoded readings) over every tracked file under `docs/verification/stage-04`, `DECISIONS.md`, `PROJECT_STATUS.md`, the registry, and every file of the extracted run archive: 23,266 files, 0 matches (`SECRET_SCAN.json`). |

## 2. Governance status

Stage 04: **BLOCKED**, open blocker **B-04-001** ("Gate 04-I NOT PASSED under P2", D-079), recorded with
`citerift-gov blocker add` and the existing `IN_PROGRESS → BLOCKED` transition (owner ref above). No governance code,
schema or rule changed. Not verified, not VERIFIED_AWAITING_OWNER_ACCEPTANCE, not ACCEPTED_CLOSED. Stage 05 is not
authorized.

## 3. No scientific artifact rewritten

`git diff` from each artifact's own commit to the audited candidate shows no change in: the historical P and campaign
(`evaluation/`, `evaluation-campaign/`, since `1064113`); P2 (`evaluation-p2/`, since `10cc9d8`); the P2 campaign
(`evaluation-p2-campaign/`, since `2b45931`); freeze-2 (since `6dab7f8`); the engine (`src`, `schemas`,
`pyproject.toml`, `uv.lock`) and `simulations/stage04` (since `28ba646`). The superseded Step 12 freeze directory has
only its own attestation (`15ef3c3`) and the D-071 `SUPERSEDED.md` marker added after `b5bf8ed`. The audit wrote only
outside the repository, apart from this directory, the handoff, the decisions and the governance record.
