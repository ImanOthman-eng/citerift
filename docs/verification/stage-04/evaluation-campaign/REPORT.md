# Stage 04 Step 14: evaluation campaign report (gate 04-I)

Executed under the accepted pre-registration P = `4eded723bbb464c247b31e675d2f2fc7d16133328d55925c9a787801efd1098a`
(owner message `cmsg_018VCB51nDHP6HXmLU4ea5yP2Hk5yHet3jmkhGoVf9yZD5`, D-070), on the frozen engine `b5bf8ed`.
Every number below comes from `SCORES.json`, written by the pre-registered scorer `s13_score.py` from the locked
labels and the one prediction run. Nothing was tuned, re-drawn or re-run after any result existed. Every deviation
is in `PROTOCOL_LOG.md` and in section 6.

## 1. Outcome

**Gate 04-I is NOT PASSED.** The pre-registration requires all five gates in both languages.

| Gate | ar | en |
|---|---|---|
| G1 positive units ≥ 30 | 38 — pass | 42 — pass |
| G2 one-sided 95 % upper bound of false attachments ≤ 0.10 | 0 of 38, bound 0.0758 — pass | 1 of 42, bound 0.1080 — **fail** |
| G3 hazards H1–H4 = 0 | 0 — pass | 1 (H1) — **fail** |
| G4 structural violations S1–S3 = 0 | 1 (S1) — **fail** | 0 — pass |
| G5 negative units ≥ 60 | 1,288 — pass | 1,016 — pass |

- **English G2 and G3** fail on one unit: `en-39868218` (Ignazio Ciufolini) `un-00011`. The unit cites a
  "*Withdrawal:*" item in JASIST (DOI 10.1002/asi.23238). The Retraction Watch record lists that same DOI as the
  original paper and gives no notice identifier. The engine classed the unit `RETRACTED_WORK_CITED`. The final label
  (A, B and the adjudicator agree on `kind = notice_citation`; record R1 judged `cited_notice` by A, `cannot_tell` by B
  and the adjudicator) makes it a false attachment (`unverifiable`) and hazard H1. With n = 42, one error gives a
  bound of 0.1080; the pre-registration stated that one error is tolerated only from n = 46.
- **Arabic G4** fails on one article: `ar-10305362`. Its investigation COMPLETED and its VERIFY passed, but its
  export was refused because the pre-registered run tool did not create the `run/exports/` parent directory, which the
  frozen engine requires (section 6, deviation 2). The scorer counts the missing export as S1, as registered. Apart
  from this, Arabic passes every gate.

## 2. Primary metric: attachment precision over the four positive classes (D-068)

| | ar | en |
|---|---|---|
| positive units | 38 | 42 |
| correct | 38 | 41 |
| precision (exact two-sided 95 %) | 1.000 [0.907, 1.000] | 0.976 [0.874, 0.999] |
| false-attachment rate, one-sided 95 % upper bound | 0.0758 | 0.1080 |
| unannotated / unverifiable positives | 0 / 0 | 0 / 1 |

Per class (n > 0 only; no per-class minimum):

| Class | ar n (correct) [95 %] | en n (correct) [95 %] |
|---|---|---|
| RETRACTED_WORK_CITED | 31 (31) [0.888, 1.000] | 38 (37) [0.862, 0.999] |
| CORRECTION_CITED | 7 (7) [0.590, 1.000] | 3 (3) [0.292, 1.000] |
| CONCERN_CITED | 0 | 1 (1) [0.025, 1.000] |
| REINSTATED_WORK_CITED | 0 | 0 |

Secondary (RETRACTED + CONCERN, does not replace the primary): ar 31/31 [0.888, 1.000]; en 38/39 [0.865, 0.999].

## 3. Negatives and recall (descriptive, E-07)

| | ar | en |
|---|---|---|
| negative units (G5) | 1,288 | 1,016 |
| truth-positive among negatives (two-sided 95 % upper limit) | 0 (0.0029) | 0 (0.0036) |
| exact misses (H4) | 0 | 0 |
| truth-positive units (retrieval-scoped) | 43 | 42 |
| retrieval-scoped recall | 38/43 = 0.884 [0.749, 0.961] | 41/42 = 0.976 [0.874, 0.999] |
| recall, identifier-reached truth positives | 38/43 | 41/41 |

Recall is bounded by the retrieval routes of PREREGISTRATION section 6.

## 4. Identity conflicts (D-067, exhaustive and descriptive)

| Language | Case | Engine | Final label | Abstained | Abstention justified | Single-identifier attachable | Converted to positive |
|---|---|---|---|---|---|---|---|
| ar | `ar-8414305` `un-00006` | IDENTITY_CONFLICT | work_citation, same_work **yes**, R1 cited_work, R2 unrelated (agreed) | yes | **no** | yes | no |
| en | `en-60575` `un-00107` | IDENTITY_CONFLICT | work_citation, same_work **no** (adjudicated), R1 cited_work | yes | yes | yes | no |

Pooled: 2 engine cases, 0 label-only cases, 0 converted to a positive, 0 unannotated. The Arabic case is a later
(".pub2") version of a Cochrane review whose PMID is shared with the earlier version's record: annotators judged one
work cited, so that abstention was not justified by the label. No population rate is claimed. Both articles ended
NEEDS_RESOLUTION, as the engine's design requires for an unresolved conflict.

## 5. Baseline and sensitivity variants (D-069, descriptive)

| | ar positives (FA) bound, hazards | en positives (FA) bound, hazards | not computable |
|---|---|---|---|
| Engine | 38 (0) 0.076, none | 42 (1) 0.108, H1 1 | — |
| Naive baseline | 49 (7) 0.252, H1 5 | 55 (14) 0.369, H1 13 + H3 1 | — |
| (a) `identifier_link` excluded | 37 (0) 0.078, none | 42 (1) 0.108, H1 1 | 0 |
| (b) P-2 / identity protection off | 38 (0) 0.076, none | 42 (1) 0.108, H1 1 | 0 |
| (c) `labeled_reference_text` included | 38 (0) 0.076, none | 42 (1) 0.108, H1 1 | 4 units |

Baseline recall: ar 42/43, en 41/42. Under (b) the two conflict units are no longer conflicts and neither becomes a
positive.

## 6. Protocol deviations

1. **Aborted first run invocation (no output).** The run tool put the Investigation Memory inside the repository; the
   engine refused all 24 articles it reached (`MEMORY_ROOT_UNSAFE`, exit 3) before creating any investigation. The tool
   was stopped and `RUN.json` was never written. The one run was then executed on a byte-identical copy of the
   campaign outside the repository (verified with `diff -r` before the run, and again after scoring). Evidence:
   `aborted-run-attempt-1/`.
2. **Missing export parent directory.** The run tool does not create `run/exports/`. The first article's export was
   refused; the executor created the empty directory at 14:46:30Z, before the second article finished, and touched nothing else. That article keeps no export
   and counts as S1 (Arabic G4).
3. **Transcripts in the repository** keep every user and assistant record and the platform model attachment; platform
   context attachments are left out (original file hash and line count recorded in `rounds/*/INSTANCES.json`).
4. **Platform context of the instances** included the repository `CLAUDE.md`, the tool listing and a queued copy of
   the owner's acceptance message. No Stage 04 output existed for any sampled article when any instance ran.
5. **One adjudicator** (`ADJ-ar-p01`) tried once to write the clock time outside its work directory; the platform
   denied it. No instance read outside its work directory.
6. **Self-reported times** are placeholders in several label files; platform timestamps are in `INSTANCES.json`.
7. One drand mirror (`drand.cloudflare.com`) answered 403; three agreed.

## 7. Campaign summary

- Seed: drand quicknet round 34067905, seed `32aebd7f…bc60f` (`SEED.json`).
- Acquisition: 80 attempts of 200; 80 acquired; 0 failures; 0 replacements; rounds `primary` (60),
  `ar-expansion-1` (10), `en-expansion-1` (10). Expansion stopped by the registered rule after block 1 in each language.
- Items: 161 (ar 77, en 84); A/B disagreed on 14 (ar 5, en 9), all adjudicated. 31 Claude Sonnet instances (28 annotators, 3 adjudicators;
  platform model `claude-sonnet-5-5`), each new, each on at most six articles of one language.
- Locks: `LOCK.json` `6059e462…72dc`, committed in `5b70068` before the run.
- Run: 80 investigations (78 COMPLETED, 2 NEEDS_RESOLUTION), 80 VERIFY passed, 79 exports, 0 resumes; median 89 s per
  article (the D-064 per-process identity check included). `run/RUN.json` `864c552a…0558`; full memory and exports in
  `run/run-archive.tar.gz` (`e4313af9…f679`).
- Scores: `SCORES.json` `bbc2b58d…daea`.

## 8. Limitations (as pre-registered, plus observed)

AI-generated single-vendor labels, not human gold labels; retrieval-scoped truth; stratified unbalanced sample with no
prevalence claim; current revisions captured; pinned Retraction Watch snapshot; variant (c) leaves 4 units not
computable. Observed: the English failure is a single case where the Retraction Watch record gives the withdrawal
item's DOI as the original paper's DOI, so the engine's original-identifier match and the annotators' reading of the
unit as a notice disagree.
