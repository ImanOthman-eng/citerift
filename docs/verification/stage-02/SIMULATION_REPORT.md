# Stage 02 Simulation Report

What was simulated before and beside the engine, what each simulation shows,
and how independent it is of the engine. Results are at the code revision
named in HANDOFF.md ("Verified Git commit"); the commands are in section 7.

## 1. Prebuild policy simulator

`simulations/stage02/policy_simulator.py` is an executable reference model
of lookup (SPECIFICATION.md 10.3), projection (11.1) and Evidence Tension
(11.2). It imports nothing from `src/citerift/retraction`. It was written
before the engine, with the frozen synthetic cases it runs:

| Case set | Cases | Simulator | Engine (`test_rde_policy_cases.py`) |
|---|---|---|---|
| `cases/policy_cases.json` | 37 | 37 pass | 37 pass |
| `cases/tension_cases.json` | 16 | 16 pass | 16 pass |

Output: `evidence/simulator.json`. The frozen case files have not changed
since `36696b3`. One expectation is amended after freezing, P04 (a
reinstatement alone was `verified_fact`, `reinstated`; it is now `uncertain`,
null, `REINSTATEMENT_UNLINKED`), in `cases/post_freeze_amendments.json`. Both
loaders check that the frozen value is still the one in the frozen file
before they apply the amendment, so an edit to the frozen file is detected.

On 2026-10-28 three more were amended for the owner's R-026 correction (C-25,
SPECIFICATION.md 16 item 25): P33 (a PMID query whose only retraction is a
bridged DOI-only record was `verified_fact`, `retracted` with a verified date;
it is now `uncertain`, null, no date) and the `exclude_ambiguous_links`
changed-field sets of T05 and T06 (their base is now unsettled, so the view
changes status, value and support instead of value and date). An amendment
now names the part it replaces (`field`: `expected`, or `interventions` for a
tension case). The simulator was changed for rule 7f in the same commit as
the engine (`a0666b3`), as code of its own: it reduces the direct
assertions and the full set separately and compares them, and it marks a
Crossref relation as bridged when its DOI is not the query's. Like C-9 to
C-14 before it, the change was written by the same agent as the engine, so on
these points the two implementations are not independent (section 5).

## 2. Independent streaming oracle (gate 02-C)

`simulations/stage02/oracle_stream.py` reads the pinned CSV in one streaming
pass with the standard `csv` module and its own identifier normalizer and
role map; it shares no code with the engine. `scripts/oracle_compare.py`
compares, for every key, the ordinals the oracle finds in the original and
notice roles with the ordinals the engine's public lookup returns.

| Measure | Oracle | Engine |
|---|---|---|
| Records / accepted / quarantined | 73,356 / 73,356 / 0 | 73,356 / 73,356 / 0 |
| Physical lines | 173,491 | 173,491 |
| Valid DOI keys / PMID keys | 112,481 / 63,010 | same |
| Absent synthetic keys | 1,300 DOI + 300 PMID | same |
| Key-role comparisons | 350,982 | |
| Mismatches | **0** | |

Output: `evidence/oracle-comparison.json` (oracle output SHA-256
`f6d15226…`, unchanged since the first run). This checks extraction and
query fidelity against the source bytes, not the truth of any record.

## 3. Seeded property simulations

| Test | Draw | Properties |
|---|---|---|
| `test_rde_tension_properties.py` | 300 seeded evidence sets | views never mutate or invent evidence; removal cannot create a positive observation (INV-P6); a redistributed copy is not an independent witness (INV-P7); controls give no change (INV-X1); deterministic, bounded reports |
| `test_rde_bridge_sufficiency.py` | 600 seeded sets with bridged assertions of both origins | INV-P9 (no verified value from bridged support), INV-P10 (a verified value holds with the bridges rejected and accepted), INV-P11 (direct sufficiency kept); non-vacuity floor of 20 per branch; fails on the code of `720a049` (`evidence/fail-first/r026-bridge-sufficiency-at-720a049.txt`) |
| `test_rde_policy_properties.py` | 400 seeded sets per property | INV-P1 and INV-P8 (a retraction needs clear, known-origin support), INV-P2 as amended (a later concern or correction on another proposition, or an ordered one on the same notice, does not undo a retraction), INV-P3 (no reinstatement without supersession); each property has a non-vacuity floor of 50 applicable draws |

The reducer property file was added after the review passes. Against the code
of `3a6f1eb` it fails on INV-P2 (same notice) and INV-P3
(`evidence/fail-first/policy-properties-at-3a6f1eb.txt`); it passes now.

## 4. Real policy impact of the post-freeze changes

`scripts/policy_impact.py` projects every original DOI and PMID key of the
snapshot (96,803 keys) with two code revisions and compares the results
(`evidence/policy-impact-rw.json`, RW-only index; `policy-impact-cr.json`,
with the pinned Crossref replay). Between `3a6f1eb` and the review batch:

| Transition | DOI keys | PMID keys | Cause |
|---|---|---|---|
| `verified_fact`/`reinstated` → `uncertain`/null | 147 | 128 | C-11 (unlinked reinstatement) |
| `conflicting` → `verified_fact`/`retracted` | 21 | 13 | C-12 (ordered sequence on one notice) |
| `conflicting` → `uncertain`/null (`MIXED_CURRENT_EFFECT`) | 2 | 2 | C-12 (an ordered concern and correction) |

No other key changes. Two keys stay `conflicting` (`10.1007/s11581-008-0309-x`,
`10.1016/j.ijrefrig.2015.10.002`). The same 313 keys change on both indexes.

Between `720a049` (policy 1.1.0) and `a0666b3` (policy 1.2.0, rule 7f), with
identity status and the number of supporting assertions also compared
(`evidence/policy-impact-r026-rw.json`, `policy-impact-r026-cr.json`): no key
changes on the RW-only index; 22 PMID keys change on the Crossref index, of
which 2 go from `verified_fact`/`retracted` to `uncertain`/null (TEST_RESULTS.md
12.2).

Between `ac959c6` (policy 1.2.0) and `1465e85` (policy 1.3.0, audit fixes F1
and F3), with issue codes also compared (`evidence/policy-impact-audit-rw.json`,
`policy-impact-audit-cr.json`): on the RW-only index 2 PMID keys go from
`verified_fact`/`correction` to `uncertain`/null (23649173, 25996123), 2 keep
their value with identity `bridged` (3507357, 25816875), and 2,095 more keys only
gain the issue `PMID_ROLE_COLLISION` (2,097 carry it) (TEST_RESULTS.md 13.2). The simulator
follows F1 (16 item 27) and still passes 37/37 policy and 16/16 tension
cases; no frozen case has a DOI with two PMIDs, so no expectation changed.

## 5. Independence limits

- One author. The simulator, the frozen cases and their expectations, the
  oracle and the engine were all written by the same AI coding agent (the
  oracle by a separately prompted pass of the same model). Separate code is
  not separate judgment: a misreading of the specification shared by all of
  them would not be detected. No human reviewed the cases.
- The simulator changed after the freeze, in four commits (SPECIFICATION.md
  16, last paragraph). On those points it was changed to agree with the
  specification as amended, not as an independent check of the engine.
- The 50 real cases in `tests/stage02/fixtures/real_cases.json` take their
  expected outcomes from the changed simulator. The science review ran the
  original frozen simulator on the 46 non-absent real cases of that time and
  got the same outcomes as the updated one, so those updates did not create
  agreement; the cases added or changed by C-11 and C-12 (R08, R09, R46, R47)
  were derived only with the changed simulator.
- The real cases were chosen by a deterministic script by class, not by
  outcome. The agent read all 50 cases against the specification after the
  regeneration (TEST_RESULTS.md 4). That is a model's reading, not a human
  adjudication.
- The oracle covers identifiers and roles only; it says nothing about
  projections, dates or tension.

## 6. What the simulations do not show

- That a source record is true. Every `verified_fact` means "established from
  the cited source record".
- Behaviour on sources other than the pinned Retraction Watch snapshot and the
  29-work Crossref replay.
- Any model capability. The simulations contain no model. The local open
  model was evaluated separately under AI Protocol v2 on real holdout groups
  and not admitted (TEST_RESULTS.md 7.2). The v2 power table
  (`ai/v2/PROTOCOL_V2.md` 4) is an exact calculation, not a simulation.

## 7. Commands

```bash
uv run python simulations/stage02/policy_simulator.py --output docs/verification/stage-02/evidence/simulator.json
uv run python simulations/stage02/oracle_stream.py --csv data/raw/rw/retraction_watch.csv --out ORACLE.json
uv run python docs/verification/stage-02/scripts/oracle_compare.py --oracle ORACLE.json \
  --index INDEX --out docs/verification/stage-02/evidence/oracle-comparison.json
uv run python docs/verification/stage-02/scripts/policy_impact.py --index INDEX --out NEW.json
uv run python docs/verification/stage-02/scripts/policy_impact.py --compare OLD.json NEW.json --out DIFF.json
```

AI Protocol v2 (development audit, draw, model runs and evaluation):

```bash
uv run python -I docs/verification/stage-02/scripts/ai_protocol_v2.py audit|devset|draw \
  --index data/index/bench/build1/rw-2f116e9ffed718e6.sqlite --out docs/verification/stage-02/ai/v2
unshare -n env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy \
  .venv-infer/bin/python -I docs/verification/stage-02/scripts/ai_model_run.py score --deny-network \
  --manifest src/citerift/retraction/model_manifests/mxbai-rerank-base-v2.json \
  --model-dir models/mxbai-rerank-base-v2 --cases docs/verification/stage-02/ai/v2/holdout-manifest.json \
  --out docs/verification/stage-02/ai/v2/runs/holdout-mxbai.jsonl
.venv-infer/bin/python -I docs/verification/stage-02/scripts/ai_model_run.py evaluate ...  # see ai/v2/holdout-result.json
```

