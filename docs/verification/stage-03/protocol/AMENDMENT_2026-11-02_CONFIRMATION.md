# Prospective amendment: the 2026-11-02 confirmation campaign

**Authority.** The owner's instruction of 2026-11-02, sections 6-8 and 12
(`../authorization/OWNER_DIRECTIVE_2026-11-02_CONFIRMATION.md`, DECISIONS.md D-034). It authorizes one new prospective
confirmation campaign. This amendment is that campaign's protocol.

**When it was written.** It was written and committed before any article of the campaign was drawn, captured,
annotated or extracted. No outcome of the campaign existed when any rule below was set.

**What stays.** It does not change:

- FROZEN_PROTOCOL.md, AMENDMENT_2026-10-29.md, annotation guide 1.0 or `scripts/evaluate.py`;
- any earlier selection, capture, label, lock, prediction, score or adjudication.

The final campaign of D-031 stays a published failed result. It is not rerun and not called fresh, and no article
exposed by any earlier campaign can enter this one.

## 1. What stays exactly as frozen

- the claim under test (FROZEN_PROTOCOL.md 1) and the support profile (2);
- the matching rules and metrics (5, 6), as implemented in the unchanged `evaluate.py`;
- the gates G1-G11 and every threshold (7.1);
- the per-language minimum denominators (7.2): 50 target identifier occurrences, 80 uses, 60 definitions and 60
  linkable uses;
- the window: the frozen `window` function, 8000 code points from the line that holds a seeded-random `<ref` opening;
- uncertainty: 2000 article-cluster bootstrap resamples, seed 20261028;
- baselines B0 and B1 and the A/B/C comparison (8), reported, not gated;
- failure accounting: every selected article counts in acquisition (G9) and is never replaced;
- the synthetic challenge (10) and G11;
- the network policy of `FetchPolicy` and FROZEN_PROTOCOL.md 11.

## 2. What is prospectively different, and why

| Change | Why | Where |
|---|---|---|
| Annotation guide 1.1 | resolves the definition/use ambiguity on repeated references (owner instruction section 3) | `ANNOTATION_GUIDE_v1.1.md`, `../design/sfn-semantics/SEMANTIC_DECISION.md` |
| Scorer v2 | applies the same definition rule to the engine's predictions; everything else is `evaluate.py` | `scripts/evaluate_v2.py` |
| A larger, block-wise sample | the Arabic identifier denominator was not reached with 16 articles (risk E7) | sections 3-6 |
| A new frame and exclusions | no exposed article may be evidence | section 3 |
| A resumable capture driver | R8 of the owner instruction | `../evaluation/scripts/campaign_capture.py`, `../design/retry-after/AUDIT.md` |
| A positive warning challenge | owner instruction section 8 | section 9 |

## 3. Frame, eligibility, exclusions and order

**Population.** The population is that of FROZEN_PROTOCOL.md 3, unchanged: arwiki and enwiki articles in namespace 0
that are not redirects and whose rendered output has at least one https external link to `doi.org` at selection
time.

**Random draw.** The draw uses the frozen procedure of `select_sample.py`:

- `list=random` in batches of 500 titles;
- a `prop=extlinks` filter with `elquery=doi.org`;
- at most 6 batches for arwiki and 4 for enwiki;
- per wiki, it stops as soon as the eligible articles reach that wiki's maximum (section 4).

The draw is made by `../evaluation/confirmation-2026-11/scripts/select_confirmation.py`. `list=random` is
server-side randomness and cannot be re-run, so every answer is kept for audit.

**Exposure and exclusion.** Before the draw, `exposure_set.py` collects every page id and every title that appears in
any JSON document committed under `docs/verification/stage-03/` or `tests/stage03/`:

- selections, including the unused candidates and the random batches;
- captures, annotations, extractions and fixtures;
- the development titles.

The output, `EXPOSURE_SET.json`, is committed before the draw. A page id or title in it is excluded in both wikis.
The exclusion is deliberately over-inclusive. An article group is the page id: all revisions of an article belong to
one group.

**Order (the randomization seed).** Eligible articles are ordered by the SHA-256 of
`citerift-stage03-confirmation-2026-11-02-v1|<wiki>|<page id>`. The order depends only on the page id and the salt.
It never depends on the engine, its predictions or any label.

## 4. Sample design and ordered reserve

| | arwiki | enwiki |
|---|---|---|
| initial holdout | positions 1-24 | positions 1-16 |
| reserve | positions 25-48 in blocks of 4 (6 blocks) | positions 17-32 in blocks of 4 (4 blocks) |
| maximum | 48 | 32 |

The maxima are caps, not guarantees.

- If the draw yields fewer eligible articles than the maximum, the maximum is the number drawn. The last block may
  then be shorter than 4.
- A shortfall is reported and is never filled by any other route.

**Reserve rule.** The rule uses committed, locked annotation counts only.

- The counts per article are `reserve_decision.counts`, unchanged: in-window target identifiers, uses, definitions
  with `in_window` true, and linkable uses.
- After the initial holdout of a language is locked and committed, the totals are compared with the minimums.
- While any minimum is unmet and a block remains, the next block of that language is captured, annotated, locked and
  committed, and the totals are recomputed.
- The two languages are decided independently.
- No prediction, extraction, disagreement or capture outcome other than the capture state enters the decision.
- Each decision is written by `reserve_step.py` (this campaign) to `reserve-decisions/<step>/` and committed with
  its lock.

**Unmet minimums.** If a minimum is still unmet at the maximum, the affected gates are reported against the actual
denominator. They are reported as **not met**, and the campaign is not extended.

## 5. Feasibility, checked before acquisition

**Statistical feasibility.** The per-article counts of the two earlier campaigns' locked labels were resampled
(28 arwiki articles, 32 enwiki; 20,000 resamples; computed 2026-11-02 before this amendment was committed):

| Articles | P(all minimums met) |
|---|---|
| arwiki 24 | 0.92 |
| arwiki 28 | 0.98 |
| arwiki 32 | 0.996 |
| arwiki 40 | about 1 |
| enwiki 16 | 0.66 |
| enwiki 20 | 0.92 |
| enwiki 24 | 0.99 |
| enwiki 28 | about 1 |

**A pessimistic check.** Resampling only from the final campaign's 16 arwiki articles (2.1 identifiers per
article) gives a probability of reaching 50 identifiers of 0.87 at 32 articles and 0.98 at 40. The arwiki maximum of
48 is therefore expected to be enough, but this is not guaranteed.

**Network feasibility.**

- From the earlier draws, 7.4 % (arwiki) and 11.6 % (enwiki) of random articles were eligible. One or two batches
  per wiki are expected, at about 11 requests per batch.
- The capture of 80 articles at most takes 2 requests each when there is no rate limiting.
- The warning challenge takes at most 7 listing pages and 24 articles.
- The expected total is about 270 requests without rate limiting, inside the ceiling of 500 HTTP attempts. Rate
  limiting at the development rate (37.5 % of requests answered 429) could add about 100 more.
- Accepted bodies: the earlier campaigns averaged under 0.2 MiB per article, far below 300 MiB.

**Time feasibility.** With at least 10 s between requests, acquisition takes about 1-2 hours of requests,
plus Retry-After waits. The deadline is 2026-11-21 23:59 EST.

## 6. Capture and network

**Driver.** Captures use the production `citerift-wiki capture --page-id` through `campaign_capture.py`. It pins the
latest revision at capture time.

**Driver rules.**

- at most 4 runs per article;
- a deferred article runs again only after its `not_before` plus 1 s, and a wait over 600 s is resumed by rerunning
  the same command;
- a retryable failure gets one more run;
- a complete capture is never repeated;
- recovery after an interruption;
- an exclusive driver lock.

**Failure policy.** An article that ends without a bundle, or without a render, stays in the sample with its state and
codes (G9). It is never replaced.

**Ceilings.** One cumulative ceiling covers all network work of this campaign: the exposure-free draw, the challenge
listing, captures and reruns.

- **500 HTTP attempts** and **300 MiB of accepted bodies**.
- They are checked before every request or run against the campaign journal (`capture/captures.jsonl`), with an
  interrupted run counted at its worst case.
- When the next worst case would cross a ceiling, nothing more is requested. Uncaptured articles are recorded with
  their state, and a reserve block that cannot be captured leaves its language's minimum unmet.
- No other process uses the network gate during the campaign. No alternative route, identity or host is used.

**Time limit for acquisition.** Acquisition ends at 2026-11-14 23:59 UTC. An article not captured by then keeps the
state it has.

## 7. Annotation (owner instruction section 7)

**Who labels.**

- The implementing agent never creates, edits or chooses a label.
- Labels come from separate evaluator instances (Claude subagents, each with its own context), at most 6 articles
  per instance.
- Every evaluator receives only:
  - a working directory outside the repository, holding the raw-only packets of its articles (`source.wikitext`,
    `render.html`, `packet.json`);
  - a copy of `ANNOTATION_GUIDE_v1.1.md`;
  - an output directory;
  - the brief `../evaluation/confirmation-2026-11/EVALUATOR_BRIEF_v1.1.md`.

**Models.**

- Evaluators use a different Claude model from the implementing agent: Claude Sonnet. Adjudicators use a different
  model from the evaluators: Claude Opus, in new contexts that did not take part in the implementation.
- All are Anthropic Claude models. No model of another vendor, and no further Claude model, is available in this
  environment without paid usage credits. A third model was planned, but its use was refused for lack of credits on
  2026-11-02, before any draw, so this line was corrected then.
- These are AI labels, never human gold.

**Packets.** Holdout packets are made by `evaluate.py packets` with the frozen window. Challenge packets are made by
`warning_challenge.py packets` (section 9).

**Lock.** For each batch:

- `evaluate.py lock` writes `ANNOTATION_LOCK.json` with the SHA-256 of every label file;
- the lock records the frozen candidate revision and this amendment's revision;
- the labels, the lock and the evaluator records are committed;
- all of this happens before any extraction of those articles.

The executor validates each label file for format, quotes and window only. An invalid file is returned to a new
instance of the same evaluator role with the validation message. It is never fixed by the executor.

## 8. Prediction, scoring and adjudication

**Candidate.** The candidate is the engine at the revision recorded in
`../evaluation/confirmation-2026-11/MANIFEST.json` before the first capture. It is the revision that the independent
review (owner instruction section 9) reviewed, plus only the repairs of that review and its follow-up.

**Prediction run.** It is made once, after every lock is committed, by `run_holdout.py`. `run_holdout.py` refuses to
run before the locks are committed. Every evaluated extraction is verified (`citerift-wiki verify --extraction`) and
replayed (`citerift-wiki replay`).

**Scoring.** `scripts/evaluate_v2.py score` is used on the locked labels, and later on the adjudicated labels.

**Adjudication.**

- Disagreements are listed by `disagreements.py`.
- They are adjudicated once by new adjudicator instances under the frozen adjudication procedure
  (FROZEN_PROTOCOL.md 4.5), with the brief `../evaluation/confirmation-2026-11/ADJUDICATION_BRIEF_v1.1.md` (guide
  1.1, isolated directory).
- Gates use the adjudicated labels. Locked and adjudicated results are both published.

**After the run.** There is no repair, retuning, reselection or rerun. A material defect that the campaign exposes is
preserved and reported.

**Estimands.**

- Per language, the micro-averaged ratios of FROZEN_PROTOCOL.md 6 over the in-window items of the sampled articles.
- Their 95 % article-cluster bootstrap intervals.
- For the zero-tolerance gates (G2, G3a, G7), the one-sided 95 % Clopper-Pearson upper bound for the observed count.

The inferential population is random DOI-citing arwiki and enwiki articles at selection time, window-level. Exposed
articles are excluded, which is a non-random exclusion of a small set, and is stated as such.

**Stopping rules.**

- The study ends when both languages have their minimums or their maximum, or when a ceiling or the acquisition time
  limit is reached.
- Nothing stops early or continues because of an outcome.
- No further campaign starts automatically.

## 9. Positive retraction-warning challenge (owner instruction section 8)

**What it is.** A challenge separate from the holdout, specified now, with genuine and unexposed positives.

**Frame.** Per wiki, the namespace-0 articles that transclude a marker template of the stratum:

| Stratum | arwiki | enwiki |
|---|---|---|
| retraction | `قالب:مصدر مسحوب`, `قالب:Retracted` | `Template:Retracted` |
| concern | `قالب:Expression of concern` | `Template:Expression of concern` |
| correction | `قالب:Erratum` | `Template:Erratum` |

These come from `list=embeddedin`, at most 4 pages of 500 per template.

**Exclusions.** The exposure set, and every page drawn into the holdout frame (including its random batches). An
article is placed in the first stratum it belongs to.

**Order and size.** Articles are ordered by the SHA-256 of
`citerift-stage03-warning-challenge-2026-11-02-v1|<wiki>|<stratum>|<page id>`. The first 4 per stratum are taken: at
most 12 per wiki, or fewer when fewer exist.

**Window.** 8000 code points from the line of a seeded-random marker-template call outside comments and `<nowiki>`
(`warning_challenge.py`). An article whose source has no such call gets the frozen window.

**Labels.** Separate evaluator instances label the window fully under guide 1.1, as for the holdout. They are not told
that an article is a challenge article or which stratum it is in.

**Reported, per wiki and stratum, for locked and adjudicated labels:**

- the denominator of labelled warnings;
- the marker confusion (label × engine state);
- fabricated negatives (G7 applies, and must be 0);
- sensitivity (engine `recognized_warning_text` on labelled warnings), with a Clopper-Pearson interval;
- false warnings;
- `not_inspected`.

**Gates and limitations.**

- Only G7 is a gate. Sensitivity has no threshold, because none was frozen and none is set after seeing data.
- Dimensions not present in the drawn articles are reported as not observed. These are: unsupported or ambiguous
  language, red-linked templates, source-only markers, and uninspected regions.
- The synthetic tests that cover those dimensions are not field evidence.
- An insufficient sample is stated as a limitation.

## 10. Acceptance procedure

Stage 03 moves to `VERIFIED_AWAITING_OWNER_ACCEPTANCE` only when every condition of the owner instruction section 12
holds. The executor never records acceptance and never merges. Otherwise the exact failure is reported with the
evidence.

## 11. Tool corrections after review R6 (2026-11-02, before any draw)

Review R6 (`review/round-6/REVIEW.md`, dispositions in `review/REVIEW_FINDINGS.md`) found defects in the campaign
tools. They were corrected before any draw, exposure set or capture of this campaign. No threshold, gate, minimum,
size, salt, order or stopping rule above changed. The corrections make the tools do what sections 3 to 9 already say:

- **Ceilings (section 6).** A run is charged what its reported capture record shows, zero included; only an
  interrupted run, or one without a reported record, is charged its worst case. The worst case of one run is
  6 attempts and 64 MiB of accepted bodies (2 x the 32 MiB body limit of the fetch policy).
- **Draw (sections 3 and 6).** A request deferred by a server's Retry-After waits until `not_before` plus 1 s and is
  sent again; it is not a failed batch. A wait over one hour stops the draw before SELECTION.json is written. If a
  draw stops that way, the next draw starts afresh, and SELECTION.json lists the earlier requests, which are reported.
- **Driver (section 6).** A run stopped by an unreadable or out-of-range Retry-After is final. A bundle published
  before the driver was interrupted is adopted, never captured again. A torn journal line is kept aside.
- **Time limit (section 6).** The driver and the draw start nothing at or after 2026-11-14 23:59 UTC.
- **Reserve decision (section 4).** It refuses unresolved captures. After a ceiling or the time limit, the articles
  keep their states and no further block is named.
- **Prediction run (section 8).** `confirmation-2026-11/scripts/run_confirmation.py` refuses a captured article
  without a locked label and builds one gate split (holdout plus included reserves) and a separate challenge spec.
- **Challenge window (section 9).** A marker call written with `Template:` in any case, on either wiki, is found.

Engine changes made with these corrections (also before the freeze): short-footnote redirects of one template
are one template, `ref=` is compared as a link target, positional values are trimmed as Lua trims them, and the
network gate record is never left empty. On the 70 retained real bundles none of them changes an extraction.
