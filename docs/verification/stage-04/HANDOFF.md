# Stage 04 handoff: Detection Engine and Vertical Slice (non-passing final closure)

**Status: Stage 04 is BLOCKED by B-04-001 — gate 04-I NOT PASSED under P2.** This is a non-passing final closure
audit and handoff (owner decisions D-079 to D-082, message `cmsg_018VCB51nDHP6HXmLU4ea5yPCrAWa1AotYwE4STJgegth4`):
evidence finalization, not scientific acceptance. Stage 04 is **not** verified, **not**
VERIFIED_AWAITING_OWNER_ACCEPTANCE and **not** ACCEPTED_CLOSED. Stage 05 is not authorized. Both prospective
evaluations are final and immutable; neither is combined with the other, and neither is described as a pass.

The closure audit (25 items) is in [`final-closure/AUDIT.md`](final-closure/AUDIT.md), with the machine-readable result
of checks 1–13 in `final-closure/AUDIT.json` and the script that produced it, `final-closure/closure_audit.py`.

## 1. Frozen engine identity (freeze-2, D-076)

| Item | Value |
|---|---|
| Content commit | `28ba6467c7005eec7bf51869974719a402059ca7` |
| Tree | `45c52da459b09597f105d6e4abd8ab00332c6799` |
| Attestation commit | `6dab7f8ea1b97982dca978c38ca0fc8eea6e1a7f` (CI runs 365 and 366) |
| Freeze manifest digest | `d9db2704c495459acc3487b0e656d27b386f124cae4e3bdf36b1e059a2c61c13` |
| Exposure manifest v2 | `b2a2a937a6ec245135a3495dad9e458e1b6a64e69cdf2eb4099794c5ab45e67b` (378 articles) |
| Engine / package | 0.3.0 / 0.3.0 |
| Decision table | dt-2 (strict identifier role-collision rule, D-072) |
| Schemas | common 4.0.0, claim 3.0.0; plan-1 |
| Detector identity | `citerift-dt1-detector/3 (dt-2)` |
| Trees at the run | src `ed0e1c17…`, schemas `11599931…`, pyproject.toml `0cf25557…`, uv.lock `9013ce30…` |
| Oracles | frozen dt-1 `simulations/stage04/oracle/MANIFEST.json` `41105077…`; dt-2 `oracle-dt2/MANIFEST.json` `60a21534…` |

The superseded freeze `b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0` (engine 0.2.0, dt-1) is marked
SUPERSEDED_AFTER_FAILED_04_I (D-071) and is unchanged.

## 2. The two prospective evaluations (permanent record, D-081)

| | Evaluation 1 | Evaluation 2 |
|---|---|---|
| Engine | `b5bf8ed`, 0.2.0, dt-1 | `28ba646`, 0.3.0, dt-2 |
| Pre-registration | P `4eded723bbb464c247b31e675d2f2fc7d16133328d55925c9a787801efd1098a` (commit `827ac1a`, D-070) | P2 `5d323a67d89a521384772ce7a566520e862715ce9389227f428ff8439f74f75a` (commit `10cc9d8`, D-077) |
| Seed | quicknet round 34067905, seed `32aebd7f82d03b153d226a941072fa2e76eeb8d46f92ddba96a43fc0dffbc60f` | quicknet round 34096937 (D-078), seed `b45666399e691ab6a1301086d33eb5f6b776748e6e0504a5399a407aaaba4e6c` |
| Draw (`DRAW.json` SHA-256) | `bc137002…db930` | `4efdb7bf75996060f4631a9aee5b756a06dbe631d116948547fcaa29f132226d` (plan digest `be63947a…7285`) |
| Articles | 80 (ar 40, en 40) | 100 (ar 50 = S1 42 + S2 8; en 50 = S1 42 + S2 8) |
| Items / adjudicated | 161 / 14 | 167 / 10 |
| Label lock | `6059e462c48afc7ed35c1203cd446b3b582d4a485a3a757cdca129ed562672dc` | `92a4f6408e52c835eb4a31fa7fc3febd4aac062d281ef06f27718cd0911b3961` |
| `RUN.json` | `864c552aaf4b5720e221be1af16382b64cd957876cf4c073251d5e51b9b20558` | `db8c5432014f4c104470b670bdacfe050da09b4f4e66737f8c9cadbcd4adde3e` |
| Run archive | `e4313af9ca5a9bc59394d4de5133afbf489547829949664bb8049ca1a380f679` | `54835a74c80b794522c370777aeea0f08e48910670a8ac9c8e2487939f9fc7a4` |
| `SCORES.json` | `bbc2b58d83f23e2f4f141c691debe27ba90d4f1ca96f66ecc101956a92e3daea` | `1d674dfe6d8c72506c0ea56667ab5ff5fbebf877aacf3bfc68d56e75c35bec67` |
| Evidence / report commit | `1064113` (CI 348) | `44a8479` (CI 378) / `2b45931` (CI 379) |
| Outcome | **04-I NOT PASSED**: en G2 (1/42, bound 0.1080) and G3 (H1, JASIST withdrawal DOI); ar G4 (missing export, runner defect) | **04-I NOT PASSED**: en G2 only (1/44, bound 0.1033); ar passes every gate |
| Report | `evaluation-campaign/REPORT.md` | `evaluation-p2-campaign/REPORT.md` |

The denominators are never combined.

## 3. Final P2 gate table (D-079)

| Gate | Arabic | English |
|---|---|---|
| G1 positive units ≥ 30 | PASS — 42 | PASS — 44 |
| G2 one-sided 95 % upper bound of false attachments ≤ 0.10 | PASS — 0/42, 0.0688 | **FAIL — 1/44, 0.1033** |
| G3 hazards H1–H4 = 0 | PASS — 0 | PASS — 0 |
| G4 structural violations S1–S3 = 0 | PASS — 0 | PASS — 0 |
| G5 negative units ≥ 60 | PASS — 766 | PASS — 1,717 |

**Gate 04-I = NOT PASSED.** The improvement over evaluation 1 is real and is reported as such, never as a pass: English
attachment precision 43/44 = 0.977 [0.880, 0.999]; Arabic 42/42 = 1.000 [0.916, 1.000]; zero hazards and zero
structural violations in both languages; the naive baseline is substantially worse (ar 51 positives with 3 false
attachments, bound 0.145; en 73 with 22, bound 0.402, 19 of them H1); the strict role-collision rule has a measurable
recall cost (section 5).

## 4. The exact false-attachment case (D-080)

- Unit `en-27958530` / `un-00004`, item `en-1373069395-un-00004`.
- The citation carries DOI `10.1186/1743-422X-7-169` and PMID `20663162`, the original-paper identifiers of Retraction
  Watch record 1873 (Hon, Ng, Leung, *Virology Journal* 2010, "Influenza or not Influenza: Analysis of a Case of High
  Fever That Happened 2000 Years Ago in Biblical Time", retracted).
- Its text names author Robert Garry and a title ending "– Comments", not the original paper's authors and title.
- The frozen engine attached `RETRACTED_WORK_CITED` on the DOI and PMID.
- Locked labels (authoritative): A record `cannot_tell`; B `unrelated`; ADJ `unrelated` (all `work_citation`,
  same_work `yes`, single identifier attachable `no`). The scored false attachment stands; the annotation is not
  reinterpreted after G2 was observed.
- Classification: **identifier-versus-bibliographic-object conflict not modeled by Stage 04 dt-2.** No string, author,
  journal, DOI-specific or title-suffix exception was or will be added in this cycle.

## 5. dt-2 role-collision recall cost (D-072; P2 8.8 and 8.9, descriptive)

- Population (corrective census, D-072): the strict rule removes 1,472 of 31,506 dt-1 positive pairs (the declined
  lenient rule: 800); the 53 C-01 same-work-sibling pairs stay `UNRESOLVED_IDENTITY` (D-073); 628 B-03 pairs stay
  positive on a clean original DOI (D-075).
- In P2: 13 `IDENTIFIER_ROLE_COLLISION` abstentions (ar 5, en 8). All 13 were annotated; all 13 are genuine
  citations of the work itself (every reached record judged `cited_work`; 0 notice, 0 `ambiguous_object`, 0
  `cannot_tell`). An independently clean cited identifier was present in 1 (`en-73261569` `un-00028`).
- Truth positives withheld: ar 9 of 51 (5 role collision, 1 identity conflict, 3 other non-positive class); en 11 of
  54 (8 role collision, 3 other non-positive class).
- Recall (retrieval-scoped): ar 42/51 = 0.824 [0.691, 0.916]; en 43/54 = 0.796 [0.665, 0.894]. Identifier-reached:
  ar 42/48 = 0.875; en 43/51 = 0.843. This is a limitation, never a performance result; no abstention is converted
  into a positive.

## 6. Identity-conflict result (D-067, exhaustive and descriptive)

P2: one engine case, `ar-7378444` `un-00004` (PMID and title match the record's original, DOI differs): abstained
(`IDENTITY_CONFLICT`, article NEEDS_RESOLUTION), abstention justified by the agreed label (work_citation, same_work
`cannot_tell`, R1 `cited_work`, single identifier attachable `yes`), not converted to a positive. English: none.
Label-only cases: 0. Evaluation 1 had two engine cases (one abstention not justified by its label). No population
rate is claimed.

## 7. Performance limitation (D-061, D-066)

The ≤ 5 s p95 per-article target is **NOT_MET** (≈ 25.5–30.5 s at freeze measurement); it is an accepted limitation,
never claimed met, and the per-process index identity check (D-064) is not weakened. In the P2 run the median was
89.1 s per article (maximum 139.4 s), 153.9 minutes for 100 articles, each including the investigation, VERIFY and
export.

## 8. Prediction-wrapper deviation (D-082)

The session's background-command wrapper kills its process tree after 2 hours; the run needed 153.9 minutes. At
15:20:50Z, after 2 articles, only the `uv run` launcher was terminated so that the running runner process left that
tree. The runner was not interrupted, was invoked once, made 0 article resumes, and wrote `RUN.json` once; all 100
investigations verified; all 100 exports exist; the frozen engine identity was unchanged (audit checks 8–10). The
deviation does not invalidate the scores and stays documented (`evaluation-p2-campaign/PROTOCOL_LOG.md`, report
section 8, deviation 5). **It must not be reproduced in a future scientific campaign**: a future long run is
launched under infrastructure whose declared lifetime exceeds the registered campaign duration.

## 9. Defect and limitation register (final)

Open review findings (all LOW; none MEDIUM or higher is open), from `corrective/review/TRIAGE.md`:

| Id | Severity | Status | Finding |
|---|---|---|---|
| A-04 | LOW | open | Non-cited bridge keys: small exposure; cannot create a positive the cited keys do not support (RISK_ANALYSIS R4-04). |
| D-05 | LOW | open | The role-collision fixture manifest lacks the selection index's `artifact_digest` and `semantic_digest` (it has `source_sha256`). |
| E-05 | LOW | open | `RUN.json` records the absolute memory root as an operational locator (outside every scientific digest); present in the P2 `RUN.json`. |
| E-07 | LOW | open | No dedicated engine-version error; a reused private memory root is accepted (the runner refuses where `RUN.json` exists). |
| C-07 | LOW | open | Role-collision scans are quadratic in a candidate's lookup events (2.3 s at 3,000; largest real key 281). |
| N-01 | LOW | open | `provenance()` checks `src` and `schemas` only; tools under `docs/` are identified by commit and tool hash. |

Accepted LOW limitations from the Step 12 triage (`review/step12/STEP12_TRIAGE.md`): C-07 (`run` idempotency depends
on path spelling; use `resume --key`), C-08 (a different bundle at the recorded path is STALE), C-12 (upstream Stage
02 `crossref_sources` ordering; no effect on the RW-only index).

Limitations:

1. **New (D-080):** identifier-versus-bibliographic-object conflict not modeled by dt-2 (section 4).
2. Strict role-collision recall cost (D-072; section 5); C-01 same-work siblings stay unresolved (D-073).
3. Performance NOT_MET (D-066; section 7).
4. Labels are AI-generated by one vendor (Claude Sonnet), not human gold labels; truth is retrieval-scoped; the
   sample is stratified and unbalanced, with no prevalence claim; current revisions were captured; the Retraction
   Watch snapshot is pinned (`rw-2f116e9ffed718e6`).
5. Sensitivity variant (c) leaves 87 Arabic candidates NOT_COMPUTABLE (counted, never approximated).
6. Seven P2 articles ended COMPLETED with run exit 6 (partial) and one NEEDS_RESOLUTION (exit 10); all verified and
   exported, so none is a structural violation.
7. Operational wrapper deviation (D-082; section 8).
8. The 378 articles of exposure v2 (which include the 80 of evaluation 1) and the 100 of P2 are design-exposed for
   any future evaluation.

## 10. Recommendations for any future dt-3 research (not authorized; D-081)

These are research directions only; none is authorized in this cycle, and none may be used to make 04-I pass on the
existing evidence.

1. **Bibliographic-object consistency layer.** Before a positive attachment, test that the citation's bibliographic
   text (title, authors, journal, year, volume/pages) is consistent with the publication object its identifiers
   resolve to, by a general rule designed and specified in advance (no string, author, journal or DOI exceptions);
   disagreement routes to an explicit unresolved state, never to a positive. Comment, reply, erratum, withdrawal and
   editorial items sharing or citing a retracted paper's identifiers are the adversarial cases.
2. **Adversarial evaluation first:** a constructed set of such conflicts and of the 13 role-collision work citations,
   evaluated against an independent reference model, with fail-first evidence, before any freeze.
3. **Role-collision recall:** study whether an independent clean cited identifier or bibliographic agreement can
   resolve a role collision without weakening the D-10 fail-closed rule (the strict rule's cost here: 13 of 13 P2
   abstentions were work citations).
4. **New freeze, new prospective holdout:** a new engine version and decision table, a new freeze and a new
   pre-registration excluding every exposed article (both campaigns and exposure v2), with sample-size planning
   stated in advance (P2 tolerates one false attachment only from n = 46 and two from n = 61), never adjusted after
   results.
5. **Infrastructure:** run the prediction step where the declared process lifetime exceeds the registered duration
   (D-082), and record the absolute memory root outside committed records (E-05).

## 11. Governance status

Stage 04: **BLOCKED** (`citerift-gov transition 04 BLOCKED`, owner ref
`cmsg_018VCB51nDHP6HXmLU4ea5yPCrAWa1AotYwE4STJgegth4`), open blocker **B-04-001: Gate 04-I NOT PASSED under P2**.
BLOCKED is an existing non-accepted state of the governance model (`IN_PROGRESS → BLOCKED` with an open blocker); no
governance code, schema or rule was changed. Under the unchanged rules, Stage 04 can be verified only when every
acceptance gate passes, and Stage 05 (and every later stage, which depend on it in a chain) can be authorized only
after Stage 04 is accepted (GOVERNANCE.md invariants 1 and 3).
