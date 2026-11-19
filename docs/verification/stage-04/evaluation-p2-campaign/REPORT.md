# Stage 04 Step 14 under P2: evaluation campaign report (gate 04-I)

Executed under the accepted pre-registration P2 = `5d323a67d89a521384772ce7a566520e862715ce9389227f428ff8439f74f75a`
(commit `10cc9d8`; owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP6Ugyq1ZbRyyuDXEcx5N7Bh`, D-077; seed round fixed by the
owner, D-078), on the frozen freeze-2 engine (content commit `28ba646`, engine 0.3.0, dt-2). Every number below comes
from `SCORES.json`, written once by the pre-registered scorer `p2_score.py` from the committed label lock and the one
prediction run. Nothing was tuned, re-drawn, replaced, expanded or re-run after any label or prediction existed. Every
deviation is in `PROTOCOL_LOG.md` and in section 8. The historical campaign (`../evaluation-campaign/`, P, engine
0.2.0 / dt-1, 04-I NOT PASSED) is not read, reused or combined here.

## 1. Outcome

**Gate 04-I is NOT PASSED.** P2 requires all five gates in both languages. Arabic passes every gate; English fails G2.

| Gate | ar | en |
|---|---|---|
| G1 positive units ≥ 30 | 42 — pass | 44 — pass |
| G2 one-sided 95 % upper bound of false attachments ≤ 0.10 | 0 of 42, bound 0.0688 — pass | 1 of 44, bound 0.1033 — **fail** |
| G3 hazards H1–H4 = 0 | 0 — pass | 0 — pass |
| G4 structural violations S1–S3 = 0 | 0 — pass | 0 — pass |
| G5 negative units ≥ 60 | 766 — pass | 1,717 — pass |

**English G2** fails on one unit: `en-27958530` `un-00004` (item `en-1373069395-un-00004`). The unit is a
`{{cite journal}}` whose DOI `10.1186/1743-422X-7-169` and PMID `20663162` are exactly the original-paper identifiers
of Retraction Watch record 1873 (Hon, Ng, Leung, *Virology Journal* 2010, retracted), but whose author is "Robert
Garry" and whose title ends "– Comments". The engine classed it `RETRACTED_WORK_CITED` on the DOI and PMID. The final
label, adjudicated (A: R1 `cannot_tell`; B and the adjudicator: R1 `unrelated`; all three `work_citation`,
same_work `yes`, single identifier attachable `no`), reads the cited document as a comment piece that is neither the
record's paper nor its notice, so the attachment is incorrect. It is not a hazard (not a notice, marker or identity
conflict). With n = 44, one error gives a bound of 0.1033; P2 section 8 states that one error is tolerated only from
n = 46 (bound 0.0990). The expansion rule stopped English at 51 identifier-reached truth positives, before any
prediction existed, and no expansion follows a gate result.

## 2. Primary metric: attachment precision over the four positive classes (D-068)

| | ar | en |
|---|---|---|
| positive units | 42 | 44 |
| correct | 42 | 43 |
| precision (exact two-sided 95 %) | 1.000 [0.916, 1.000] | 0.977 [0.880, 0.999] |
| false-attachment rate, one-sided 95 % upper bound | 0.0688 | 0.1033 |
| unannotated / unverifiable / ambiguous_object positives | 0 / 0 / 0 | 0 / 0 / 0 |

Per class (n > 0 only; no per-class minimum):

| Class | ar n (correct) [95 %] | en n (correct) [95 %] |
|---|---|---|
| RETRACTED_WORK_CITED | 40 (40) [0.912, 1.000] | 40 (39) [0.868, 0.999] |
| CORRECTION_CITED | 1 (1) [0.025, 1.000] | 3 (3) [0.292, 1.000] |
| CONCERN_CITED | 1 (1) [0.025, 1.000] | 1 (1) [0.025, 1.000] |
| REINSTATED_WORK_CITED | 0 | 0 |

Secondary (RETRACTED + CONCERN, does not replace the primary): ar 41/41 [0.914, 1.000]; en 40/41 [0.871, 0.999].

## 3. Negatives and recall (descriptive)

| | ar | en |
|---|---|---|
| negative units (G5) | 766 | 1,717 |
| truth-positive among negatives (exact two-sided 95 %) | 0 [0.000, 0.0048] | 1 [0.00001, 0.0032] |
| exact misses (H4) | 0 | 0 |
| truth-positive units (retrieval-scoped) | 51 | 54 |
| retrieval-scoped recall | 42/51 = 0.824 [0.691, 0.916] | 43/54 = 0.796 [0.665, 0.894] |
| identifier-reached recall | 42/48 = 0.875 [0.748, 0.953] | 43/51 = 0.843 [0.714, 0.930] |

The English truth positive among negatives is `en-60275503` `un-00010`: the unit's DOI `10.7759/cureus.1067` and
PMID `28409068` differ from the record's original identifiers (`10.7759/cureus.1047`, PMID `38348426`); it reached
the record by title only, so the engine's `NOT_FOUND_IN_CHECKED_SOURCES` is not an exact miss (H4 = 0). Recall is
bounded by the retrieval routes of P2 section 6.

## 4. dt-2 role-collision abstentions (P2 8.8, descriptive, no pass/fail)

| | ar | en |
|---|---|---|
| `UNRESOLVED_IDENTITY` units with `IDENTIFIER_ROLE_COLLISION` | 5 | 8 |
| annotated | 5 | 8 |
| final kind `work_citation` | 5 | 8 |
| truth positive (every reached record judged `cited_work`) | 5/5 [0.478, 1.000] | 8/8 [0.631, 1.000] |
| `notice_citation` / other kind | 0 / 0 | 0 / 0 |
| any record `ambiguous_object` / `cannot_tell` | 0 / 0 | 0 / 0 |
| independently clean cited identifier present | 0 | 1 (`en-73261569` `un-00028`) |

Units: ar `ar-7923503` un-00006, `ar-8029983` un-00009, `ar-8177443` un-00008, `ar-8312431` un-00001, `ar-8773304`
un-00003; en `en-2595296` un-00122, `en-28547` un-00027, `en-31632698` un-00013, `en-58713610` un-00016/17/18,
`en-73261569` un-00028 and un-00038. In this sample every role-collision abstention was a citation of the work
itself. This is the recall cost of the strict rule declared in D-072; it is a limitation, not a performance result,
and no abstention is converted into a positive.

## 5. Truth positives the engine withheld (P2 8.9, descriptive)

| Cause | ar | en |
|---|---|---|
| role collision (`IDENTIFIER_ROLE_COLLISION`) | 5 | 8 |
| other abstention (identity conflict) | 1 | 0 |
| other non-positive class | 3 | 3 |
| positive but incorrect | 0 | 0 |
| no claim | 0 | 0 |
| **total withheld** (truth positives − correct positives) | 9 of 51 | 11 of 54 |

## 6. Identity conflicts (D-067, exhaustive and descriptive)

| Language | Case | Engine | Final label | Abstained | Abstention justified | Single-identifier attachable | Converted to positive |
|---|---|---|---|---|---|---|---|
| ar | `ar-7378444` `un-00004` | IDENTITY_CONFLICT | work_citation, same_work cannot_tell, R1 cited_work (agreed) | yes | yes | yes | no |

Pooled: 1 engine case, 0 label-only cases, 0 converted to a positive, 0 unannotated. The unit's PMID and title match
the record's original; its DOI differs from the record's original DOI. The article ended NEEDS_RESOLUTION, as the
engine's design requires for an unresolved conflict. English has no case. No population rate is claimed.

## 7. Baseline and sensitivity variants (D-069, descriptive)

| | ar positives (FA), bound, hazards | en positives (FA), bound, hazards | NOT_COMPUTABLE |
|---|---|---|---|
| Engine (dt-2) | 42 (0), 0.069, none | 44 (1), 0.103, none | — |
| Naive baseline | 51 (3), 0.145, H1 3 | 73 (22), 0.402, H1 19 | — |
| (a) `identifier_link` excluded | 39 (0), 0.074, none | 43 (1), 0.106, none | 0 |
| (b) P-2 / identity protection off (role-collision guard kept) | 42 (0), 0.069, none | 44 (1), 0.103, none | 0 |
| (c) `labeled_reference_text` included | 40 (0), 0.072, none | 44 (1), 0.103, none | 87 (all ar) |

- Baseline recall: ar 48/51 (identifier-reached 48/48), en 51/54 (51/51).
- Under (b) the Arabic identity-conflict unit is no longer a conflict and does not become a positive.
- Variant (c) NOT_COMPUTABLE candidates (counted, never approximated): `ar-3208722` 67, `ar-1775585` 10,
  `ar-1761069` 8, `ar-4501381` 1, `ar-6010866` 1.
- Every article passed the variants' faithfulness self-checks (the tool stops otherwise); no variant is declared
  NOT_COMPUTABLE as a whole.

## 8. Protocol deviations

1. **Seed boundary.** The acceptance message's sent and stored timestamps (12:16:15Z / 12:16:16Z) selected different
   rounds under the registered rule; the owner fixed round 34096937 before either round existed (D-078).
2. **One drand mirror** (`drand.cloudflare.com`) answered HTTP 403; three agreed (within the registered rule).
3. **Instance `B-ar-p05`** ended without a final hand-back reply; its label file was complete and format-valid.
4. **Expansion `status` runs** made between one language's lock and the other's also listed the other language's
   decision; those listings were not acted on (twice). Every decision acted on was computed after that language's
   lock.
5. **Prediction-run wrapper (operational).** The session's background-command wrapper kills its process tree after
   2 hours; the run needed 153.9 minutes. At 15:20:50Z, after 2 articles, the `uv run` launcher process was killed so
   that the runner process (same PID, arguments and log) was reparented and left that tree; this was tested first on
   a dummy process. The runner was not interrupted, was invoked once, never resumed an article (0 resumes) and wrote
   `RUN.json` once. The `exit 137` line in the run log is the launcher's.
6. **Run outputs kept as in the historical campaign:** `RUN.json`, `PROGRESS.json` and `run-archive.tar.gz` (exports
   and full Investigation Memory), verified by extraction and `diff -r` before the raw exports left the working tree.
7. **Transcripts in the repository** keep every user and assistant record and the platform model attachment; platform
   context attachments are left out (original file hash and line count in `rounds/*/INSTANCES.json`).
8. **Executor glue** `executor/p2c_batches.py` is not pre-registered: the historical `s14_batches.py` with P2 paths;
   it copies files and records hashes and never reads or changes a label's content.

No tooling or protocol defect outside P2's rules appeared: 0 acquisition failures, 0 replacements, 0
`EXPOSED_AT_CAPTURE`, 0 structural violations, every A and B label file format-valid on its first submission.

## 9. Campaign summary

- Seed: drand quicknet round 34096937 (13:16:15Z), randomness `8402f166…3772`, seed `b4566639…4e6c` (`SEED.json`,
  commit `2f898ae`).
- Draw: `DRAW.json` file SHA-256 `4efdb7bf…226d`, canonical digest `be63947a…7285` (commit `2a17c48`).
- Acquisition: 100 attempts of 200; 100 acquired (ar 50 = S1 42 + S2 8; en 50 = S1 42 + S2 8); 0 failures, 0
  replacements, 0 `EXPOSED_AT_CAPTURE` at capture-time recheck. Rounds `primary` (60), `ar-expansion-1`,
  `en-expansion-1`, `en-expansion-2`, `ar-expansion-2` (10 each). Expansion stopped by the registered rule after
  block 2 in each language (ar 48 / 785, en 51 / 1,718 identifier-reached truth positives / negative-proxy units).
- Annotation: 167 items (ar 66, en 101). A and B agreed on every scored field for 157 items (ar 59, en 98); 10 were
  disagreed (ar 7, en 3), all adjudicated. Per-field A/B agreement: ar kind 65/66, same_work 61/66, single identifier
  attachable 61/66, record judgments 66/66; en kind 99/101, same_work 101/101, single identifier attachable 101/101,
  record judgments 99/101. 40 Claude Sonnet instances (18 A, 18 B, 4 adjudicators; platform model
  `claude-sonnet-5-5`), each new, each on at most six articles of one language, blinded to every engine output.
- Label lock: `LOCK.json` `92a4f6408e52c835eb4a31fa7fc3febd4aac062d281ef06f27718cd0911b3961`, committed in `7284214`
  before the run; the runner verified it (and every packet hash) before article 1.
- Engine identity (checked by the runner and the scorer): content commit `28ba6467…059ca7`, tree `45c52da4…`, freeze
  manifest `d9db2704…1c13`, engine 0.3.0, dt-2, schema 4.0.0, claim schema 3.0.0, detector
  `citerift-dt1-detector/3 (dt-2)`, plan-1.
- Run: 100 investigations (99 COMPLETED, 1 NEEDS_RESOLUTION), 100 VERIFY passed, 100 exports, 0 resumes; median
  89.1 s per article, maximum 139.4 s. `run/RUN.json` `db8c5432…de3e` (index SHA-256 `abedb94e…ff24`);
  `run/run-archive.tar.gz` `54835a74…c7a4` (commit `44a8479`).
- Scores: `SCORES.json` `1d674dfe…ec67` (commit `44a8479`).

## 10. Limitations (as pre-registered, plus observed)

AI-generated single-vendor labels, not human gold labels; retrieval-scoped truth; stratified unbalanced sample with no
prevalence claim; current revisions captured; pinned Retraction Watch snapshot; dt-2's strict role-collision rule
withholds work citations (D-072; here 13 truth positives, all genuine work citations); variant (c) leaves 87 Arabic
candidates NOT_COMPUTABLE; performance (D-061) NOT_MET (D-066). Observed: the English failure is a single unit whose
citation text and identifiers disagree (identifiers of the retracted paper, author and title of a comment piece);
the engine attaches on identifiers, and the annotators judged the cited document from its text.
