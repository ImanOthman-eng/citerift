# Stage 04 scientific evaluation: pre-registration (gate 04-I)

Status: **SUBMITTED FOR OWNER ACCEPTANCE. Not in force.** Until the owner accepts this document by its manifest
digest, no seed is fixed, no sample is drawn, no article is captured, nothing is annotated and no prediction is run.
After acceptance, nothing in this document, `PARAMETERS.json`, the guide, the briefs or `tools/` may change; a change
needs an explicit owner decision recorded before the draw, and no metric definition may change after the sample is
drawn (D-068).

Scope: Stage 04 Step 13 only (owner message `cmsg_018VCB51nDHP6HXmLU4ea5yPV9NbT2xMsMtwK9Z5Wt3WZ6`, 2026-11-18).
The frozen engine is not changed. Step 14 (draw, capture, annotation, the one prediction run, scoring) is not
authorized by this document.

Every file this document names under `evaluation/` is listed, with its SHA-256, in `PREREGISTRATION_MANIFEST.json`;
the manifest's canonical digest is the identity of this pre-registration (section 4.1).

## 1. What is evaluated, against what

| Item | Value |
|---|---|
| Engine | the Stage 04 freeze: content commit `b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0`, tree `86152ad543971d321059f16f93c3aff671f467c4`, freeze manifest digest `609796cee9fc168b379669dde7ca5c410868e37455944d86b12624578fae42cc`, attestation `15ef3c302e3d0a5406150e523b144174ed69f433` (CI run 338); accepted by the owner (D-066) |
| Detector | decision table `dt-1`, production detector, unchanged |
| Checked source | the Stage 02 index of the pinned Retraction Watch snapshot `rw-2f116e9ffed718e6` (CSV SHA-256 `2f116e9f…0a655`), identity per D-062/D-064 |
| Extraction | the accepted Stage 03 extractor (`citerift.wiki.extract.extract_bundle`, default configuration), inside the frozen tree |
| Capture | the accepted Stage 03 capture (`citerift-wiki capture --page-id`), current revision at capture time |
| Unit of analysis | a Stage 03 citation unit of a captured article revision |

The one prediction run checks, before its first article, that the trees of `src`, `schemas`, `pyproject.toml` and
`uv.lock` at the running commit equal those of `b5bf8ed` and have no uncommitted change (`tools/s13_run.py`).

## 2. Owner decisions applied

| Decision | How it is applied |
|---|---|
| D-3 (D-040) | two independent blinded Claude Sonnet annotators per item; labels locked before predictions; a third blinded Sonnet adjudicator; evidence and model metadata retained; Haiku auxiliary only (not used); disclosure as AI-generated single-vendor labels (section 7) |
| D-5 (D-040) | 30 primary and 10 predetermined reserve articles per language, expansion within 200 acquisition attempts, denominators never weakened, no prevalence claim (sections 5, 10) |
| D-064 | every engine process verifies the index by `verify_index_identity`; no cross-process trust, no reduced profile |
| D-066 | the ≤ 5 s p95 target is NOT_MET; nothing here measures or claims it |
| D-067 (E-05) | identity conflicts: exhaustive, descriptive, no minimum (section 8.7) |
| D-068 (E-06) | primary precision over all four positive classes, per language, exact interval; per-class results; optional secondary subset (sections 8.2 to 8.4) |
| D-069 (E-08) | baseline and sensitivity variants as evaluation-only tooling, committed and hashed here, tested on exposed fixtures (section 11) |

**Superseded wording, flagged for the owner.** Registry gate 04-I still says "minimum positive, negative and
identity-conflict denominators", and MATHEMATICAL_MODEL.md 11.2 still defines precision over two classes and applies
the ceiling rule to the identity-conflict denominator. D-067 and D-068 supersede both. This pre-registration follows
D-067 and D-068; the registry and MM 11.2 text were not edited (the frozen documents are not changed, and the registry
is changed only through `citerift-gov`). The owner may record the alignment at Stage 04 acceptance.

## 3. Frames (E-10, E-02, E-14)

### 3.1 Source

Per language, the frame is derived from the Wikimedia dumps of 2026-10-01 (`externallinks` and `page` tables) and
the pinned Retraction Watch CSV by the unchanged Stage 01 script
`docs/verification/stage-01/scripts/stage01_census.py dump-scan` (SHA-256 `12e76154…f350844`), which checks each
dump's sha1 against the run's published `dumpstatus.json` values before reading it.

- **Arabic**: the committed Stage 01 output `docs/verification/stage-01/data/census/ar_scan.json`. Re-derived for
  this pre-registration from the same dumps by the same script: identical except `generated_at`.
- **English (E-10)**: Stage 01 did not commit its English scan. It was re-derived here by the same script from the
  pinned dumps and committed as `frame/en_scan.json`; its counts equal the committed Stage 01 summary
  (`census_summary.json` `en_dump_scan`) — see section 3.4.

The planning wording "Arabic: census-confirmed articles" is not used: `ar_confirm.json` is a live check of 2026-10-27
revisions that reads article content, so both languages use the same dump-scan rule (E-14).

### 3.2 Members and strata

- **Member**: a page of the scan in namespace 0 that is not a redirect (the scan holds pages whose external links
  point to the DOI or PMID of a Retraction Watch record, original paper or notice).
- **S1**: at least one linked record of nature `Retraction` reached through the original paper's identifier.
- **S2**: every other member (expressions of concern, corrections, reinstatements, notices only).

Only identities, strata and counts are computed before the draw. No article content is read, and no Stage 01 excerpt
(`ar_render.json`, `ar_confirm.json`, reference markup) is used as a label, an engine input or a selection input.

### 3.3 Exposure exclusion (E-02, E-04)

A member is excluded when any of these holds:

1. its (wiki, page id) is a record of the Step 12 exposure manifest (`freeze/exposure/EXPOSURE_MANIFEST.json`,
   SHA-256 `5a6d466f…abeb83b`; 298 articles: every Stage 03 bundle, attempt and development title, the 232 Stage 04
   development revisions, Stage 01 purposive pages and evidence);
2. its (wiki, normalized title) is one of a manifest record's titles;
3. its normalized title is a manifest title of the **other** wiki (the other language's article of an exposed one;
   this excludes one page, the English `BCAS3`, counterpart of design case VS-5).

**The Stage 03 listed tier is recorded but not applied (E-02; owner choice, section 15).** The listed tier
(regenerated by the Stage 03 rule `stage-03/evaluation/confirmation-d036/scripts/exposure_set.py` at the manifest
commit `bdeeac1`, committed as `frame/listed_tier.json`, checked against the manifest's `listed.output_sha256`
`84653870…beff35`) holds every page id and title named in any committed Stage 03 JSON, in any wiki. Applied, it
would also exclude 438 of the 745 English articles and 9 Arabic ones that the rules above keep. Traced: those pages
are named in Stage 03 **selection frames** (lists of pages embedding retraction templates, random lists) and in the
derived Stage 03 exposure-set files, or share a title with a link inside a captured page. They were listed, never
captured, read or annotated, and Stage 04 design never used them; every Stage 03 article that was captured, attempted
or evaluated is already in the manifest (its sources `S03-BUNDLE`, `S03-ATTEMPTED`, `S03-DEV-TITLE`). Applying the
tier would remove 59 % of the English articles; many of them come from Stage 03 lists of pages embedding retraction
templates, so the sample would lose marked articles and the marker hazard (H2) would be tested less. `FRAME.json`
marks those members `listed_only`, and `PARAMETERS.json` `frame.exclude_listed_tier` switches the rule (if the owner chooses to
apply it, the frame, the manifest and its digest are rebuilt before acceptance).

The rule is applied again to each captured page's current id and title (a page moved after 2026-10-01): a match is an
acquisition failure `EXPOSED_AT_CAPTURE` (section 5.3).

### 3.4 Counts after exclusion (E-14)

`frame/FRAME.json` (format `citerift-stage04-eval-frame/1`, built by `tools/s13_frame.py`) holds every member with
its stratum, every excluded page with its reasons, and the digest of each frame.

| | ar | en |
|---|---|---|
| namespace-0 non-redirect pages | 195 | 745 |
| before exclusion, S1 / S2 | 158 / 37 | 432 / 313 |
| excluded (first reason: manifest page id / manifest title / other-wiki title) | 15 (13 / 2 / 0) | 58 (56 / 1 / 1) |
| **frame, S1 / S2 (total)** | **143 / 37 (180)** | **380 / 307 (687)** |
| of which `listed_only` (S1 / S2) | 9 (9 / 0) | 438 (275 / 163) |
| frame digest | `8313e0e1…920db968` | `5987777a…2b78fb2c` |
| with the listed tier applied (not proposed): frame S1 / S2 | 134 / 37 | 105 / 144 |

Thinning (E-14): exclusion removes 15 of 158 Arabic S1 members (9 %) and 52 of 432 English ones (12 %). The planned
positions fit: per language 40 positions before expansion (29 in S1), and the 200-attempt ceiling is reached before
either frame is used up (ar 180 members, en 687).

## 4. Seed and draw order

### 4.1 Identity of this pre-registration

`PREREGISTRATION_MANIFEST.json` lists every evaluation file (this document, `PARAMETERS.json`, the guide, the briefs,
the frame inputs and `FRAME.json`, every tool, the Step 13 test file, the development run) with its SHA-256, and the
frozen references of section 1. Its canonical digest (sorted keys, no whitespace, UTF-8, SHA-256) is the
**pre-registration digest** `P`. The owner accepts the pre-registration by `P`.

### 4.2 Seed

Nobody can choose or predict the seed when `P` is committed:

- beacon: drand `quicknet` (chain `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971`, genesis
  1692803367, period 3 s); a round's randomness is the SHA-256 of its BLS signature. The tool checks that the
  published randomness equals the SHA-256 of the published signature; it does not verify the BLS signature against
  the chain's public key (agreement of independent mirrors is the safeguard, and the signature is kept in `SEED.json`
  so anyone can verify it later);
- round `R`: the first round whose time is at least **one hour after the owner's acceptance message** (fixed by that
  message's timestamp alone);
- `R` is read from the mirrors `api.drand.sh`, `api2.drand.sh`, `api3.drand.sh` and `drand.cloudflare.com`; at least
  two must return the same verified randomness. If no two agree within 24 hours of the round time, the draw stops for
  an owner decision; no other round is ever used;
- seed = SHA-256(`citerift-stage04-eval-seed/1|P|R|randomness`), written to `SEED.json` with every mirror's answer.

### 4.3 Order

Within each (wiki, stratum), frame members are ranked by SHA-256(`citerift-stage04-eval-order/1|seed|wiki|stratum|
page_id`), ascending (`tools/s13_draw.py plan`, written to `DRAW.json`). The order depends only on the seed and the
page id.

## 5. Sampling, acquisition, replacement, expansion

### 5.1 Allocation (per language, `PARAMETERS.json` `sampling`)

| Block | S1 | S2 | Total |
|---|---|---|---|
| primary | 22 | 8 | 30 |
| reserve (replacements only) | 7 | 3 | 10 |
| expansion block k (k = 1..12) | 10 from S1 in order; from S2 only when S1 is used up | | 10 |

S1 is weighted because positive units come mainly from it; S2 keeps notices, concerns and corrections in the sample.
This is a stratified, deliberately unbalanced design: no prevalence or population rate is estimated (D-5).

### 5.2 Rounds

1. `primary`: the 60 primary positions (both languages).
2. Each round is captured, packeted, annotated by A and B, adjudicated where they disagree, and **locked** before the
   expansion decision for the next round is made.
3. `<wiki>-expansion-<k>`: block k of one language, when the rule of 5.5 says so.

### 5.3 Acquisition of a position

The page id is captured by `citerift-wiki capture --wiki W --page-id P` (render on, redirects not followed); the
current revision at capture time is the evaluated revision and is recorded.

| Outcome | Result |
|---|---|
| exit 0 (complete) or 6 (partial) | captured |
| exit 4 (unavailable) or 8 (deferred) | retried twice, 300 s apart; still 4 or 8 → `CAPTURE_FAILED` |
| any other exit | `CAPTURE_FAILED` (for example a redirect, a deleted page, another namespace) |
| Stage 03 extraction neither `complete` nor `partial` | `EXTRACTION_FAILED` |
| captured page id differs from the drawn one | `PAGE_ID_MISMATCH` |
| captured (wiki, page id) or current title meets the rule of 3.3 | `EXPOSED_AT_CAPTURE` |

Each position whose capture is started is one acquisition attempt; retries of the same position are not. The ceiling
is **200 attempts for both languages together**. `ACQUISITION.json` is append-only and records every attempt, try,
exit code, failure and replacement.

### 5.4 Replacement

A failed **primary** position is replaced by the next unused **reserve** position of the same language and stratum,
in draw order. When that stratum's reserves are used up, it is not replaced. Expansion positions are not replaced.
Nothing else ever replaces an article: not its content, its items, its labels or any engine output.

### 5.5 Expansion rule (engine-independent)

After a language's rounds are locked, `tools/s13_acquire.py status` computes, over that language's locked rounds:

- **identifier-reached truth-positive units**: items whose final label is `work_citation`, same_work not `no`, with
  a record judged `cited_work` that an identifier of the unit reached as the original paper; target **≥ 40**;
- **negative-proxy units**: units with a valid DOI or PMID in a candidate role (`primary_citation_field`,
  `identifier_link`) none of whose keys is an identifier of any Retraction Watch record; target **≥ 75**.

If either count is short, the next expansion block of that language is acquired, while planned positions remain and
fewer than 200 attempts are used. The targets carry a margin over the gate minima (30 and 60) because both counts are
computed without the engine and before any prediction; the gates themselves (section 10) are evaluated only on the
one prediction run, and a short gate after the ceiling is a failed gate, never a weakened one.

## 6. Item set and packets

Built by `tools/s13_packets.py` from the captured bundle, the Stage 03 extraction (retained as
`extractions/<article>.json`) and the index with plain SQL. It never imports or runs the Stage 04 engine.

**Candidate records of a unit:**

1. **identifier-reached**: every Retraction Watch event whose original or notice identifier equals the Stage 02
   normalized key of any valid DOI or PMID occurrence of the unit, **any role**;
2. **title-reached**: every event whose title tokens `T(r)` (Stage 02 `search.title_tokens`) satisfy `|T(r)| ≥ 4`
   and `|T(r) ∩ T(u)| / |T(r)| ≥ 0.8`, where `T(u)` are the tokens of the unit's wikitext; at most 5 per unit, ranked
   by that ratio, then shared tokens, then event id.

**Item set**: every unit with at least one candidate record. A unit with none cannot be a truth positive within this
retrieval scope; that boundary is declared (section 13). This replaces the planning proposal's "pre-registered sample
of units without a candidate key": the title route covers units without an identifier exhaustively instead of by
sample (flagged in section 14).

**Packet** (`citerift-stage04-eval-packet/1`): the article identity, the extraction digest, and per item the unit
wikitext (at most 6,000 bytes, cut on a UTF-8 boundary and marked), its identifiers as written and normalized, and
per record the Retraction Watch fields (nature, title, original and notice DOI/PMID, journal, author, dates, article
type) and the search reason. Nothing of Stage 04 is shown: no class, rule, role, key choice or lookup state.

## 7. Annotation and adjudication (D-3)

- **Guide**: `ANNOTATION_GUIDE.md`. Fields: `kind` (work_citation, notice_citation, retraction_marker, other_mention,
  not_a_reference, cannot_tell); `same_work` (yes, no, single_identifier, no_identifier, cannot_tell); a judgment per
  record (cited_work, cited_notice, unrelated, cannot_tell); `single_identifier_attachable` (yes, no, cannot_tell);
  `note` (≤ 500 characters, not scored).
- **Annotators**: two Claude Sonnet instances per item, A and B (`ANNOTATOR_BRIEF.md`), each a new agent with its own
  context, at most six articles of one language per instance, the same items for the A and B instance of a batch,
  never each other's work, no repository, no network.
- **Adjudication**: an item on which A and B differ in any scored field goes to a third Claude Sonnet instance (ADJ,
  `ADJUDICATOR_BRIEF.md`) that sees the item and both labels; its label is final. An agreed label is final as it is.
- **Blinding**: no Stage 04 output exists for any sampled article until every round is locked (section 9).
- **Metadata**: per instance, the model name and version the platform reports, times, batch, input file hashes and
  the transcript where the platform keeps one (a missing transcript is recorded as missing).
- **Lock**: `tools/s13_labels.py lock` validates the format of every file, requires the adjudicated items to be
  exactly the disagreed ones, and writes the round's `LOCK.json` with the SHA-256 of every packet and label file;
  `merge` joins the rounds into the campaign `LOCK.json`. Locks are committed before the prediction run. The executor
  never edits a label.
- **Disclosure**: the labels are AI-generated by one model vendor's models, not human gold labels.

## 8. Metrics (per language unless stated)

Notation: `L(u)` is the final label of unit `u`'s item. "Reached as original" means: a record whose original-paper
identifier equals a key of the claim (index table `ident`, role `original`).

### 8.1 Engine units

- **Positive unit**: a unit with at least one claim of the four positive classes `RETRACTED_WORK_CITED`,
  `CONCERN_CITED`, `CORRECTION_CITED`, `REINSTATED_WORK_CITED` (D-068).
- **Negative unit**: a unit with a `NOT_FOUND_IN_CHECKED_SOURCES` claim and no positive claim.

### 8.2 Primary metric: attachment precision (D-068)

A positive claim is **correct** when `L(u).kind = work_citation`, `L(u).same_work ≠ no`, and among the records its
keys reach as original at least one is judged `cited_work` and none `unrelated` or `cited_notice`. A positive unit is
correct when every positive claim of it is. A positive unit outside the item set, or without a final label, counts as
**incorrect** (reported as `unannotated`); one whose relevant judgments are all `cannot_tell` counts as incorrect
(reported as `unverifiable`).

`precision = correct positive units / positive units`, with the exact two-sided 95 % Clopper–Pearson interval; the
false-attachment rate `= 1 − precision` with its exact one-sided 95 % upper bound `u` solving
`P(Bin(n, u) ≤ x) = 0.05` (`x = 0`: `u = 1 − 0.05^{1/n}`; n = 30 gives 0.0950, n = 59 gives 0.0495).

### 8.3 Per class (D-068)

For each of the four classes with n > 0: n, correct, incorrect and the exact two-sided 95 % interval. A class with no
case is reported as n = 0. No per-class minimum.

### 8.4 Secondary (optional, never replaces 8.2)

Precision over positive units whose classes include `RETRACTED_WORK_CITED` or `CONCERN_CITED`, with its interval.

### 8.5 Negatives and recall (E-07; descriptive)

- **Negative denominator**: engine negative units (G5 counts them).
- **Misses among negatives**: negative units whose label is truth-positive (`kind = work_citation`, same_work ≠ `no`,
  some record `cited_work`), with interval. Unannotated negatives cannot be truth-positive within the retrieval scope.
- **Exact misses**: a `NOT_FOUND_IN_CHECKED_SOURCES` claim whose key is an identifier of the index (hazard H4).
- **Retrieval-scoped recall**: truth-positive units with a correct positive engine unit / truth-positive units, with
  interval; reported also restricted to truth positives reached by an identifier as original
  (`recall_identifier_reached`). Both are descriptive: truth is bounded by the retrieval routes of section 6.

### 8.6 Hazards and structural violations (must all be 0)

| Id | Definition |
|---|---|
| H1 | a positive unit with `kind = notice_citation`, or with a reached record judged `cited_notice` |
| H2 | a positive unit with `kind = retraction_marker` |
| H3 | a positive unit with `same_work = no` (an identity conflict counted as an attachment) |
| H4 | a `NOT_FOUND_IN_CHECKED_SOURCES` claim whose key is an identifier of the index |
| S1 | an investigation not COMPLETED or NEEDS_RESOLUTION, or without a passed `verify`, or without an export |
| S2 | a phrase of the frozen S-7.7 list (`explanations.FORBIDDEN`) in the article summary or an explanation |
| S3 | a positive claim without supporting evidence (`supporting_count < 1` or no evidence set) |

### 8.7 Identity conflicts (D-067; exhaustive, descriptive)

Every unit with an `IDENTITY_CONFLICT` claim, and every unit labelled `same_work = no`, is listed with: language,
article, unit, the engine classes, the final label (the adjudicated interpretation, with the annotators' notes),
whether the engine abstained, whether abstention was justified (`same_work ≠ yes`), the annotators'
`single_identifier_attachable`, and whether the case was converted into a positive (which is also hazard H3 when
`same_work = no`). Counts per language and pooled. If no case occurs, the report says that no case occurred. No
population rate is claimed. An unresolved identity conflict is never counted as a positive attachment. Every engine
conflict unit has candidate identifiers that reach a record, so it is in the item set by construction; an engine
conflict without a label would be reported as a protocol deviation and never as a positive.

## 9. The one prediction run

After every round is locked and committed: `tools/s13_run.py` checks the frozen tree, the pre-registered file hashes,
the seed's pre-registration digest and the locked packet hashes, then runs per acquired article
`citerift-investigate run --bundle … --index … --memory-root run/memory`, `verify`, and `export` (only after a passed
verify). An investigation left waiting (exit 8) or incomplete (exit 14) is continued with `resume` at most three
times, never re-created. An interrupted run is continued by invoking the tool again (the engine reopens the same
investigation key). `run/RUN.json` is written once; when it exists the tool refuses. Nothing is re-run after it,
whatever the scores; a failed investigation stays a structural violation (S1).

Scoring (`tools/s13_score.py`) reads only `LOCK.json`, the packets, the retained extractions, `RUN.json`, the exports,
the index and the retained Investigation Memory, checks that the run covers exactly the acquired articles and that the
engine's retained extraction is the annotated one, and writes `SCORES.json`.

## 10. Failure criteria (gate 04-I, per language)

| Gate | Criterion |
|---|---|
| G1 | positive units ≥ **30** |
| G2 | one-sided 95 % upper bound of the false-attachment rate ≤ **0.10** |
| G3 | hazards H1 to H4 = 0 |
| G4 | structural violations S1 to S3 = 0 |
| G5 | negative units ≥ **60** |

The evaluation passes only when all five hold in both languages. A short G1 or G5 after the ceiling or the end of
the planned positions means the gate is not passed (D-5); it is never weakened. G2 tolerates no false attachment below
46 positive units (n = 30, 0 errors: 0.0950; 1 error: 0.1486), one from 46 units (0.0990), two from 61 units.
Everything else (per-class results, secondary subset, negatives, recall, identity conflicts, baseline, variants) is
descriptive and has no pass/fail.

## 11. Baseline and sensitivity variants (D-069)

Evaluation tooling outside `src/`, never imported by production code, changing nothing of the engine, schemas or
`dt-1` (tests check both). Committed and hashed here, before the draw.

**Naive baseline** (`tools/s13_baseline.py`): a unit is flagged when any eligible cited identifier of it (a DOI or
PMID occurrence of the Stage 03 extraction belonging to the unit, in a candidate role, with a valid Stage 02
normalization) equals an original-paper or notice DOI or PMID of a Retraction Watch record in the index. It reads the
extraction and the index with plain SQL and never calls the production detector. Its flagged units are scored with
the same rules as engine positive units (8.2, 8.6).

**Sensitivity variants** (`tools/s13_sensitivity.py`), from the retained Investigation Memory of each investigation,
opened read-only, with the frozen functions called as they are, and no new lookup:

| Variant | Computation | Executable |
|---|---|---|
| (a) `identifier_link` excluded | the committed extraction with `identifier_link` occurrences given the non-candidate role `labeled_reference_text`, through the frozen NORMALIZE adapter, then `dt1.decide` | yes |
| (b) P-2 / identity-conflict protection disabled | the frozen candidates and lookups through `dt1.decide` with the frozen table without rule D-6 | yes |
| (c) `labeled_reference_text` included | the extraction with those occurrences given the candidate role `identifier_link`, through NORMALIZE, then `dt1.decide` | yes, except units needing a DOI–PMID pair query the investigation did not retain: `NOT_COMPUTABLE`, counted, never approximated |

Faithfulness self-checks run first on every investigation: `dt1.decide` on the retained inputs must reproduce every
committed claim class, and NORMALIZE on the committed extraction must reproduce the committed candidate inputs byte for
byte; otherwise the tool stops (`Unfaithful`) and the variant is reported as not computed for that article.

**Development run** (plan 8.4, E-08; `tools/s13_dev.py`, result `dev/DEV_RUN.json`): the baseline and the three
variants on the 232 design-exposed revisions, without labels; three shards of the frozen engine, offline (0
network attempts). Results (development evidence only, not an evaluation):

- 230 COMPLETED, 1 NEEDS_RESOLUTION (Obokata, arwiki), 1 FAILED (`en-1380218630`: `BUNDLE_ARTIFACT_MISSING` at ACQUIRE,
  as in Step 9); the self-checks passed on all 231 investigations that produced claims; 0 unfaithful.
- Engine positive units: 20. Baseline flagged units: 27 (the 20, plus 5 units the engine classes `NOTICE_CITED`, 1
  `IDENTITY_CONFLICT` and 1 `UNRESOLVED_IDENTIFIER`).
- (a): 4,595 candidates, 0 `NOT_COMPUTABLE`; 36 units move from `NOT_FOUND_IN_CHECKED_SOURCES` to `NO_IDENTIFIER`, 2
  `UNRESOLVED_IDENTIFIER` units change; positive units unchanged (20).
- (b): 0 `NOT_COMPUTABLE`; the one `IDENTITY_CONFLICT` becomes `UNRESOLVED_IDENTITY` (other protections still
  abstain); positive units unchanged.
- (c): 0 `NOT_COMPUTABLE`; 6 `NO_IDENTIFIER` units change (5 to `NOT_FOUND_IN_CHECKED_SOURCES`, 1 to
  `UNRESOLVED_IDENTIFIER`); positive units unchanged.

All three variants are therefore executable on real investigations. The executed code was `s13_dev.py`,
`s13_sensitivity.py`, `s13_baseline.py` and `s13_common.py` with the SHA-256 values recorded in `DEV_RUN.json`
(unchanged since the shards started).

## 12. Reporting

`SCORES.json` and a Step 14 report give, per language and pooled where stated: every number of section 8 with its
interval, the gates, the baseline and variants scored the same way (with `NOT_COMPUTABLE` counts), the D-067 case
list, the acquisition log summary (attempts, failures by kind, replacements, expansions), annotation agreement
(disagreed items before adjudication) and every protocol deviation. Results are reported whatever they are.

## 13. Limitations (declared before the draw)

1. Truth is retrieval-scoped: a unit that cites a retracted work with no identifier and a title outside the title
   route is not annotated, so recall is an upper bound within that scope.
2. Labels are AI-generated by one vendor's models, not human gold labels.
3. The sample is stratified and unbalanced; no prevalence or population rate is estimated.
4. Articles are captured at their current revision, which may differ from the 2026-10-01 revision that put them in
   the frame; an article whose link is gone stays in the sample.
5. Exposure is defined at article level by the Step 12 manifest; pages only listed in Stage 03 selection files stay
   in the frame (3.3).
6. The Retraction Watch snapshot is pinned; later records are not covered.
7. Variant (c) can leave units `NOT_COMPUTABLE`.

## 14. Deviations from the planning proposal (plan 12.3), for the owner

1. Item set: the title route over all units replaces "a pre-registered sample of units without a candidate key".
2. Frame: one dump-scan rule for both languages instead of "Arabic: census-confirmed articles" (3.1).
3. Strata: S1 is defined from the dump links (a Retraction record reached through the original identifier).
4. Expansion is decided on engine-independent counts with margins (5.5), because the gate counts need predictions.
5. G2's bound (0.10) is a proposal of this pre-registration; the plan left "the pre-registered bound" open.
6. Exclusion uses the Step 12 article-level manifest plus the other-wiki title rule; the Stage 03 listed tier is not
   applied (3.3).

## 15. Choices the owner makes by accepting

Accepting this pre-registration by its digest accepts, in particular:

1. the frame exclusion of 3.3 **without** the Stage 03 listed tier (the alternative: apply it, leaving English S1 at
   105 members; the frame and the manifest would then be rebuilt);
2. the gate values of section 10 (G1 30, G2 0.10, G5 60) and the expansion targets of 5.5 (40 and 75);
3. the allocation of 5.1 (22 S1 + 8 S2 primary, 7 + 3 reserve per language);
4. the deviations of section 14;
5. that registry 04-I and MATHEMATICAL_MODEL.md 11.2 are read as superseded by D-067 and D-068 (section 2).

The owner's acceptance message fixes the seed round (4.2). Nothing is drawn before it.

## 16. Files

`PREREGISTRATION_MANIFEST.json` lists every file with its SHA-256. Tools (`tools/`): `s13_common.py`, `s13_frame.py`,
`s13_draw.py`, `s13_acquire.py`, `s13_packets.py`, `s13_labels.py`, `s13_run.py`, `s13_score.py`, `s13_baseline.py`,
`s13_sensitivity.py`, `s13_dev.py`, `s13_manifest.py`; tests `tests/stage04/test_step13_evaluation.py`.
