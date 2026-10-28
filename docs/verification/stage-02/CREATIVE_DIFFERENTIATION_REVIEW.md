# Stage 02 Creative Differentiation Review: Evidence Tension v0

Required by the owner's standing rule (DECISIONS.md D-021; directive
section 12). It names the problem, the mechanism, the nearest prior art, the
measured difference, the cost, the failure modes and the test result.

## 1. Problem

A retraction lookup usually returns one answer: "retracted" or not. A reader
cannot see what that answer rests on. Three things in the source data make a
single answer fragile, and the reader has no way to tell:

- **Redistributed support.** Crossref republishes Retraction Watch records as
  `updated-by` relations with `source: retraction-watch`. Counted naively,
  one record looks like two confirming sources.
- **Uncertain identity or notice links.** A PMID-only record reaches a DOI
  through one co-occurrence; a notice DOI is also some other work's original.
- **Unsupported temporal precision.** Retraction Watch writes day 1 for an
  unknown day, a month range, a season or a volume number, so `6/1/2009` is
  not a date of 1 June 2009.

## 2. Mechanism

For a query proposition `q` and its evidence `E`, `R(q, E)` is the fixed-policy
result (SPECIFICATION.md 11.2). Evidence Tension evaluates four bounded
interventions on copies of `E`, never on the index:

| Intervention | View |
|---|---|
| `collapse_shared_origin` | support of one origin counts once |
| `exclude_origin(o)` | assertions of origin `o`, and those known to depend on it, removed (only when there are at least two origins); assertions whose dependence is unknown are listed as `dependence_unknown` |
| `exclude_ambiguous_links` | bridged events and ambiguous notice links withheld; exact events stay |
| `require_temporal_bounds` | date values and orderings without justified bounds withheld |

For each view the report gives applicability, the changed fields of `R`, the
affected assertion ids, reason codes, the evidence digests of the base and
the view, and source pointers. It has no score and no probability. The cost
is linear in the query's evidence, with at most four plus two interventions.
`base_unresolved` says when the base answer was never settled, so "nothing
changed" is not read as robustness.

Code: `src/citerift/retraction/tension.py`; CLI `citerift-rde tension`;
schema `schemas/retraction/v1/tension-report.schema.json`.

## 3. Nearest prior art (primary materials read on 2026-10-27)

| Tool | What it does (from its own code or pages) | What it does not do |
|---|---|---|
| RetractionBot (github.com/Cookies52/RetractionBot, `find_retractions.py`, `retraction_bot.py`, `db.py`) | Loads the Retraction Watch CSV in full, folds DOI case for A to Z, matches original DOI or PMID, writes a Wikipedia template per type; a Reinstatement removes the tag | No notion of origin or dependence; reinstatement is not linked to the notice it reverses; one row, one template |
| Retraction Tracker (retractions.thinkingpark.com/about) | Matches retracted papers' DOIs to Wikipedia revisions and scores passages with a model | Event types other than retraction, notice DOIs, dates and source independence are not described; no sensitivity analysis is described |
| OpenAlex `is_retracted` (help.openalex.org work object) | A boolean "per the Retraction Watch database" | No event types, dates, provenance or dependence |
| Crossref REST API and Crossmark (crossref.org documentation) | Update relations with a `source` of `publisher` or `retraction-watch` | Exposes the label; does not say whether two relations are independent |

These are the pages read; absence of a feature from them is not proof that no
tool anywhere does it. Offline lookup, case folding, notice guards and
reinstatement handling are not claimed as new. The claimed difference is
narrow: a per-query, replayable account of which conclusion changes when an
origin, an ambiguous link or an unbounded date is taken away, against a fixed
policy, with the evidence digests to replay it.

## 4. Measured difference

The measurement was fixed before the engine (MATHEMATICAL_MODEL.md 7; gate
02-E). The frozen documents state the measurement and the pass criteria but
not a named hypothesis; stated here from them, unchanged: *on the frozen
16-case adversarial set, Evidence Tension detects every expected diagnostic
class and reports no change on controls, and the event-log baseline misses
them; on at least four real pinned examples it shows the three classes.* It
would be falsified by a missed expected class, a change on a control, or
fewer than three classes on real data.

Frozen 16-case set (engine and simulator agree):

| Measure | Evidence Tension | Event-log baseline |
|---|---|---|
| Expected classes detected (12 non-control cases) | 12 of 12 | 0 (no diagnostics by construction) |
| Changes reported on the 4 controls | 0 | n/a |
| Cases where the answer itself is wrong or misleading | 0 (fixed policy) | 10 of 16 (`baseline_error` per case) |

Because the baseline has no diagnostics, its recall of 0 is a design fact,
not a finding. The comparable measure is the answer errors it makes on the
same cases: a Crossref copy counted as a second confirming source, a day-1
value stated as a precise date, a retraction missed or asserted through an
unverified link, a notice DOI reported as "no record".

Real pinned snapshot with the pinned Crossref replay
(`evidence/tension-demonstrations.json`; TEST_RESULTS.md 5 gives the table):

| Measure | Result |
|---|---|
| Demonstrations run | 8 |
| Demonstrations showing a diagnostic class | 5 (D1, D2, D3, D4, D6) |
| Required classes shown | 3 of 3: redistributed support (D1, D2, D3), uncertain identity or notice (D4), unsupported temporal precision (D6); origin dependence also shown (D2) |
| Base never settled, reported as `base_unresolved` | 2 (D5, D7) |
| True control unchanged | D8 |
| Baseline wrong or misleading | 7 of 8 (all but D8) |

Two examples in words. D2: the baseline sees eight confirming sources; they
come from two origins. Collapsing shared origin leaves two observations.
Removing the publisher deposits leaves the answer on Retraction Watch alone.
Removing Retraction Watch and its Crossref copies leaves one publisher
observation, whose dependence on Retraction Watch is unknown and listed as
such, with no notice link and no settled retraction date. D6: the baseline states 1989-10-01 as the retraction date; Retraction
Watch wrote day 1 for an unknown day, and `require_temporal_bounds` shows the
date value depends on that.

## 5. Cost and complexity

About 250 lines (`tension.py`) on top of the reducer, no dependency, no
database writes. Measured warm p95 per query with every intervention:
0.398 ms (budget 50 ms; `evidence/benchmark.json`).

## 6. Failure modes and limits

- A changed field shows what a result rests on under one fixed policy. It is
  not a probability of error, and a policy defect shows up in every view.
- Dependence is known only where a source says so (`source:
  retraction-watch`). Publisher deposits keep unknown dependence; the report
  lists them and does not call them independent.
- "No change" on an unresolved base is not robustness (`base_unresolved`).
  The class label stays `control` for compatibility with the frozen cases.
- `uncertain_identity_or_notice` fires when the identity status or the notice
  links change, even if status and date do not; that is by definition
  (11.2 compares those fields), and it can look alarming on a stable answer.
- Only Retraction Watch and a 29-work Crossref replay were available.
  Publisher text was not read.
- The review found that a single PMID-bridged event can still give
  `verified_fact` (TEST_RESULTS.md 10, Sci-3); Evidence Tension exposes it
  through `exclude_ambiguous_links`, but the base answer is the frozen one.

## 7. Result

The stated hypothesis was not falsified on the evidence available: 12 of 12
expected classes on the frozen set, 0 changes on its 4 controls, and 5 real
demonstrations showing the three classes (gate 02-E is met).

What this does and does not show. The frozen cases, the simulator and the
engine have one author, an AI agent, so agreement between them is not
independent confirmation. The real demonstrations were chosen by a script
for the classes they show, so they show that the mechanism works on real
records, not how often each class occurs. Nothing here measures whether a
reader makes better decisions with the report; that would need a user study,
which was not done. The prior-art comparison rests on the four tools' own
materials named above.
