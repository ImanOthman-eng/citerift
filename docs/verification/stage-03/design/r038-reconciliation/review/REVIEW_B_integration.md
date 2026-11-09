<!-- Copy of reviewer B's report (D-036 readiness gate). One change: the exact expiry time of the withheld presigned URL is cut to its date (section 2), as in security/PRESIGNED_URL_REVIEW.md. The scripts and outputs it cites are in the checksummed evidence export (review-d036/B/), not in the repository. -->

# Reviewer B: Stage 03 integration boundary at `10bf0d2` (R-038 correction, engine 1.2.0)

Independent adversarial review (D-036 directive, sections 3, 5, 6 and 7). Worktree: detached `10bf0d2`
(read-only; only gitignored caches such as `.venv`/`__pycache__` were created by `uv sync`/`uv run`). Baseline for
differentials: `ec81c7f` (`src` and `schemas` exported read-only with `git archive` to `B/old/`). All scripts and
outputs are in this directory (`B/` = this directory; `B/out/` holds outputs). No network was used; no key id,
signature, object path or query string is printed anywhere in this directory.

Bundles used: the 208 `capture.json` under `docs/verification/stage-03/`. One (`en-614753-a1`, revision 1380218630)
lacks its withheld artifacts in the worktree and is skipped, so 207 are extracted.

## 1. Findings

| id | severity | title | file:line | evidence (script, observed output) | gates affected and how | classification | smallest fix |
|---|---|---|---|---|---|---|---|
| B-1 | medium (regression; creates false links) | A number anchor, or a short (<3 character) text anchor, that matches **another** use's marker forces a swap; R-038 attaches two uses to each other's markers where 1.1.0 was right | `src/citerift/wiki/reconcile.py:482-486` (support), `:903` (an anchored use may take only supporting markers), `:96` (short-anchor rule) | `B/repro_number_anchor_swap.py` (`B/out/repro_number_anchor_swap.txt`): two reuses of `M` in one infobox, `p_a = {{val\|6}}` shown `6`, `p_b = 6` shown `c. 6` (or `6 m`), source order = render order. Engine 1.2.0: `p_a matched anchor_in_template_output got=cite_ref-M_1-2 want=cite_ref-M_1-1 <-- FALSE ATTACHMENT`, `p_b ... got=cite_ref-M_1-1 want=cite_ref-M_1-2 <-- FALSE ATTACHMENT`. Engine `ec81c7f` on the same bundle: both correct (`name_in_template_output`). Randomized metamorphic check `B/template_order_sim.py` (200 SYNTHETIC infoboxes per seed): faithful renders (`SIM_TRANSFORMS=plain,plain,val,icon,link`, seed 2) `linked 1157, abstained 287, WRONG 0`; with a template-added qualifier in the cell (`...,label,...`, seed 3) `WRONG 6`; full mix seed 1 `linked 906, abstained 495, WRONG 10` (old engine, seed 1: `linked 392, WRONG 1019`). Every wrong pair has basis `anchor_in_template_output` or `elimination_in_template_output`; mechanism shown by `B/sim_debug.py 1 105 N1`, `3 10 N2`, `3 81 N0`. Real-corpus precondition (`B/anchor_failure_probe.py`, `B/out/anchor_failure_probe.txt`): of 20 number anchors in real same-name groups, **7 support no marker at all** (the template does not show the numbers it is given), so "numbers equal" is weak evidence; no real instance of the full swap exists in the 207 bundles | G6b/G6a: each occurrence is 2 false attachments with a confident basis; G6b tolerance is max(1, 1 % of links). Directive section 7 requires "no incorrect source/render link known" | genuine defect (in the correction; unusual input, reproduced synthetically only) | Do not let a weak anchor exclude alternatives: in `_settle`, give a use whose support comes from `source_numbers` or from a text anchor shorter than `_ANCHOR_MIN` `allowed = ren_set` (not only its supporting markers), and do not let such a use make a marker "taken"; then the repro is ambiguous and abstains. Add the repro and the simulation (faithful + qualifier transforms, `WRONG == 0`) as tests |
| B-2 | medium | Before-marker walk is quadratic and not bounded by `ANCHOR_MAX_NODES`: many same-name markers in one block turn a complete extraction into `EXTRACTION_DEADLINE_EXCEEDED` | `src/citerift/wiki/render.py:657-695` (`walk` decrements the budget only per descended element; sibling markers, skipped and hidden children cost a loop iteration but no budget), `reconcile.py:470-473` (one walk per marker, no per-block sharing) | `B/perf_one_block.py` (SYNTHETIC: a template output `<div><p>` holding N same-name reuses with text): in-process 1.2.0 `n=1000 names=5 seconds=17.2` vs `ec81c7f` `seconds=1.8`; `n=2000 names=1` 4.2 s. Worker (`isolated`): `n=1000 names=10` → 1.2.0 `seconds=30.1 status=failed codes=['EXTRACTION_DEADLINE_EXCEEDED']`; `ec81c7f` `seconds=5.2 status=complete`. Source side is quadratic too (`B/perf_one_param.py`, 2000 uses in one parameter: 7.8 s vs 0.4 s) | G10/G8: near the 30 s wall the outcome depends on machine speed (extract on one host, deadline on another; verify's marker reconstruction runs the same walk in a worker with the same limit). The whole document fails, not just the group (failure containment) | genuine defect (resilience; pathological input, not seen in the corpus: slowest real bundle 8.5 s both before and after) | Count every iterated child (including skipped and marker children) in the budget, and compute the prefixes of all markers of one block in one pass (cache per block); likewise compute source anchors per parameter once |
| B-3 | medium | The Stage 00 secret scan (the only guard on committed captures) misses access-bearing URL shapes, and nothing scans a capture before it is committed | `tests/stage00/test_repository.py:147-155`; `docs/verification/stage-03/evaluation/scripts/campaign_capture.py` (no scan); `.github/workflows/ci.yml` (runs only after push) | `B/secret_scan_gaps.py` (`B/out/secret_scan_gaps.txt`, FAKE samples): `DETECTED S3 SigV2 presigned, long-term key id`; `MISSED S3 SigV4 presigned, temporary STS credentials + session token`; `MISSED ... key id percent-encoded`; `MISSED Google Cloud Storage V4 signed URL`; `MISSED Azure blob SAS`; `MISSED Google API key`; `MISSED Slack incoming webhook`. The D-035 instance was detected only after commit `4766a1f` was pushed. The nested `.gitignore` lists only the five known paths | No gate; evidence integrity / public history: a new capture whose article holds an STS-signed URL (whose session token is access-bearing until expiry) would be committed and pushed unnoticed | genuine defect (process gap; Stage 00 is accepted and frozen, so the fix belongs in the Stage 03 campaign tooling) | Add a pre-commit scan step to the campaign procedure (captured artifacts and packets) with patterns for `X-Amz-Credential=`, `X-Amz-Security-Token=`, `ASIA[0-9A-Z]{16}`, `AWSAccessKeyId=`, `X-Goog-Signature=`, `[?&]sig=`, `AIza[0-9A-Za-z_-]{35}`; refuse to commit on a hit |
| B-4 | low | Historical documents do not all verify under the current engine; RISK_ANALYSIS E17 says "Old documents validate" | `src/citerift/wiki/verify.py:528` (marker reconstruction always runs the current engine); `docs/verification/stage-03/RISK_ANALYSIS.md:97` | `B/verify_old.py` (`B/out/verify_old.json`), 203 recorded documents: 1.1.0: 47/47 verify; 1.0.0: 148 verify, 8 fail: 5 `run-1` documents `BUNDLE_SCHEMA_INVALID` (`/markers/N/evidence/0: 'locator' is a required property`), `final/run` and `post-exposure-rf60` `en-1374633449` (`marker context reproduces: ct-00009/11/12`), `run-1/ar-76372332` (`an identifier link lies in a reference or a citation template`). All 8 fail identically with the `ec81c7f` engine (`B/verify_some.py`, `B/out/verify_old_failures_at_ec81c7f.txt`), so R-038 changes nothing here. Every old document replays as `REPLAY_IDENTITY_MISMATCH` (or schema-invalid), as specified | G8 on historical evidence only; no current campaign document is affected | supported boundary, undocumented (pre-existing) | State in the specification that `verify` checks a document against the current engine's marker reconstruction and schema, and list these 8 documents as no longer verifying |
| B-5 | low | Security review's reproduction claim is false at the head: `git grep ... HEAD` is not empty | `docs/verification/stage-03/security/PRESIGNED_URL_REVIEW.md:44`, `:113` | Running the documented command at `10bf0d2`: `HEAD:docs/verification/stage-03/security/PRESIGNED_URL_REVIEW.md:3` (the review matches its own words `AWSAccessKeyId`/`X-Amz-Signature`). The substantive facts hold (section 2 below) | none | documentation inaccuracy | Exclude the review file in the command (`-- . ':!docs/verification/stage-03/security/PRESIGNED_URL_REVIEW.md'`) or search only the key-id pattern |
| B-6 | low | Next campaign cannot reuse the capture driver unchanged after 2026-11-14 | `docs/verification/stage-03/evaluation/scripts/campaign_capture.py:71` (`ACQUISITION_END`, no CLI override); `confirmation-d035/scripts/select_confirmation.py:152` | Code reading: `run()` defaults to the D-035 constant and `main()` passes no override; after that date every article stops with `acquisition_closed.json` (exit 5), and `run_confirmation.plan_run` accepts a stopped capture as resolved | Fails closed (no silent mis-score); denominators would simply not be met | noncritical enhancement (protocol parameter) | Make the acquisition end a required argument (or a value in the plan) of the new campaign's copy, recorded in the protocol |
| B-7 | info | Extractor identity does not bind the code: any tree reporting 1.2.0 produces "1.2.0" documents | `src/citerift/wiki/extract.py:83-93` | Code reading; provenance currently relies on `prediction.head` and the post-hoc tree comparison of the integration audit | G10 provenance only | noncritical enhancement | Record a digest of `src/citerift/wiki` (and `schemas/wiki`) in the run log of the prediction step, and check it in `run_confirmation.py` before running |
| B-8 | info | Specification and risk analysis still describe engine 1.1.0 and R-038 as "Not changed" | `docs/verification/stage-03/SPECIFICATION.md:1`, `:553`; `RISK_ANALYSIS.md:97` | Code reading at `10bf0d2` | none (documentation pending for this phase) | documentation | Update with the 1.2.0 compatibility list (additive basis values; 1.1.0 documents replay as `REPLAY_IDENTITY_MISMATCH`) |

No critical finding. B-1 is the only route found by which the correction creates a wrong source/render link.

## 2. Checked and found sound

**R-038 integration (question 1).**
- The render reader reaches reconciliation on every path: the only callers of `reconcile` are the two calls in
  `units.source_model` (`units.py:205,210`, both pass `reader`); `source_model` is the only model builder used by
  extraction (`extract.py:207`), the worker's marker reconstruction in verify (`verify.py:506`) and replay (replay
  calls `extract_bundle`). Render failure and revision rejection set `render = reader = None` identically in
  `extract.py:183-197` and `verify.py:490-502`. No path reconciles with a render but without the reader.
- Determinism: in-process extraction of 207 bundles with `PYTHONHASHSEED=0` and `=98765` (`B/determinism.py`,
  `B/out/det_seed0.json`, `det_seed98765.json`): 0 digest differences. Every seed-0 document then verified and
  replayed in the worker (random hash seed): `Counter({(True, 'reproduced'): 207})` (`B/verify_new.py`,
  `B/out/verify_new.log`).
- Fixture re-pin: old and new engine documents of both observed fixtures differ only in `extractor/version`,
  `schema_version` and `extraction_digest` (`B/repin_check.py`, `B/repin_compare.py`, `B/out/repin_compare.txt`);
  the old digests equal the previously pinned ones.
- Version and schema consistency: `__version__` 1.2.0, `SCHEMA_VERSION` 1.2.0, schema `x-citerift-version` 1.2.0; all
  ten basis strings the engine emits (grep of `reconcile.py`) are in the schema enum; verification schema unchanged
  (1.0.0) as before.
- Old documents: all 47 engine 1.1.0 documents verify under 1.2.0; failures of 1.0.0 documents are pre-existing (B-4).
- Differential `ec81c7f` → `10bf0d2` over 207 bundles (`B/diff_old_new.py`, `B/out/diff_old_new.txt`): 6,615 uses
  unchanged, 27 same marker with a new basis, 13 different marker (the swaps listed in DESIGN.md section 6 minus the
  two withheld `MPGfacts` uses), 2 matched → abstained (`en-1473997-a1`, HESA data template); the only differences
  outside use pairing are in that one bundle (status, components, issues, exceptions, accounting, render-only uses),
  as expected. Markers are unchanged in every bundle. This independently reproduces DESIGN.md section 6.
- `body_role` over every real render (`B/body_role_survey.py`): no `contradictory` role anywhere; Arabic and English
  non-ASCII names resolve to `definition`/`reuse` like ASCII ones (ar non-ASCII 50/40, en 180/16).
- Installed wheel (`uv build --wheel --offline`, fresh venv, `CITERIFT_SCHEMAS=<worktree>/schemas`): extract,
  verify, replay of `ar-10469946-a1` (exit 6 partial / 0 / 0) and `en-186224-a1` (0 / 0 / 0) give the same digests as
  the in-process runs (`B/out/wheel/`).
- `tests/stage03/test_r038_template_output_order.py`: 32 passed. `ruff check`: all checks passed. `mypy`: no issues in
  52 source files. Stage 03 suite `pytest -q -p no:cacheprovider tests/stage03`: `845 passed in 95.39s`
  (`B/out/pytest_stage03.txt`). The worktree stays clean (`git status --short` empty) after all runs.

**Frozen scorer and campaign tooling (question 2).** `evaluate.py`/`evaluate_v2.py` read only `render.state`,
`render.locator.element_id`, container `render.state`/`region_id` and marker states; never `basis` or
`schema_version`. Abstained uses have no locator and count as abstentions. Run unchanged on the D-035 gate spec
(post-exposure regression, `B/score_new.py`, `B/out/score/summary.txt`): recorded 1.1.0 ar `false_attachments 2`, G6b
False; engine 1.2.0 ar `correct 184, false_attachments 0, abstained 13, precision 1.0, coverage 0.934`, G6a/b/c True;
en unchanged (186/190, 0 false). No crash, no mis-scoring. `disagreements_v2.py`, `intervals.py`,
`warning_challenge.py`, `reserve_step.py`, `run_confirmation.py` do not read basis values or versions.

**Byte limits and paths.** Extraction and verify use the same source (4 MiB) and render (16 MiB) limits as capture.
`preceding_text` holds lxml elements (not `id()`s); libxml2's nesting limit (~256) keeps the recursive walk below the
interpreter limit; `RenderLimitExceeded` inside the walk is contained (gives no anchor).

**Security review (question 4)**, checked from local bytes without printing values (`B/presigned_facts.py`,
`B/presigned_sig.py`, `B/blob_scan.py`): the five files hold one URL host `s3.amazonaws.com` with parameters
`AWSAccessKeyId`, `Expires`, `Signature`, `response-content-disposition` (signature version 2); one distinct key id,
one distinct signature (28 base64 characters = 20 bytes), one expiry `2024-03-25 [time of day removed in this copy]`; no
`X-Amz-Security-Token`, no `ASIA` id, no secret-key field; wikitext 1 match, render 3, API answer 1. Object database:
4,492 blobs now (4,467 when written), exactly 3 with the pattern, introduced by `4766a1f`/`763c1c4` and removed from
the index by `eba17d7`; `4766a1f` is not an ancestor of `main`, `origin/main` or any other local or remote branch
except the PR branch. No tracked file at the head contains a key id. The review's classification (key id plus
expired SigV2 signature, no secret, merge-commit propagation, clean delivery branch as the remedy) is correct; only the
"empty at the head" line is wrong (B-5).

## 3. Verdict

No critical defect. The R-038 integration itself is sound: the reader is on every path, output is deterministic
across hash seeds and processes, the re-pin changes only version strings, the frozen scorer works unchanged, and the
retained-corpus differential holds. Two medium defects remain in the correction: B-1 can create false render links
(two per occurrence, confident basis) on unusual but plausible infobox input where engine 1.1.0 was right, and B-2
lets a pathological block push extraction past the worker deadline. I rate neither high because neither occurs in the
207 retained bundles, but B-1 contradicts the readiness condition "no incorrect source/render link known" and has a
small fix, so I recommend fixing B-1 (and B-2) before freezing. B-3 should be addressed in the campaign procedure
before the next acquisition.
