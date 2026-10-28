# Stage 02 Mathematical Model

Definitions and invariants behind SPECIFICATION.md. Each invariant names the
test or check that enforces it (TEST_RESULTS.md maps them to results).
Written before production code; §9 lists later changes.

## 1. Records and accounting

Let the source bytes be `B` with receipt `ρ = (size, sha256)`. Import is a
partial function `I(B, ρ)`; it is defined only when `|B| = ρ.size`,
`H(B) = ρ.sha256`, `B` is strict UTF-8 without NUL, and the strict CSV
grammar parses `B` into a header `h` and records `r_1 … r_n`
(`n ≤ 2·10⁶`). Otherwise `I` returns a typed failure and no artifact.

Physical lines: `L = h_lines + Σᵢ span(rᵢ) + blank`, where `span(rᵢ)` is the
number of `\n`-terminated lines record `i` occupies. Disposition
`δ: {1..n} → {accepted, quarantined}` is total, so

- **INV-A1** `n = |δ⁻¹(accepted)| + |δ⁻¹(quarantined)|`;
- **INV-A2** `L` equals the physical line count of `B`;
- **INV-A3** every accepted record has exactly one event: `|events| = |δ⁻¹(accepted)|`.

Duplicate groups are a relation `D ⊆ records × kind`; they never change
`δ` or `n` (**INV-A4**). (Checked in `build` before publication, in
`verify`, and in `test_rde_ingest.py`.)

## 2. Identifier normalization

`ν_doi: String → Key ∪ {⊥}` with record `(form, transformations, issues)`.
Let `fold` map ASCII `A–Z` to `a–z` and fix every other code point.

- **INV-N1 (idempotence)** `ν(k) = k` for every key `k` in the image of `ν`.
  Proof sketch: a key is bare (starts with `10.`), has no outer whitespace, no
  `doi:` or `http` prefix (it starts with `1`), and `fold(fold(x)) = fold(x)`;
  bare forms are not percent-decoded, so `%` sequences are stable.
- **INV-N2 (no Unicode folding)** `ν(x) = ν(y)` ⇒ `fold(strip(form⁻¹(x))) =
  fold(strip(form⁻¹(y)))`: two DOIs collide only if they differ in ASCII
  case, outer whitespace, the `doi:` prefix or the resolver URL form.
- **INV-N3 (single decoding)** for URL forms, `ν` decodes `%xx` exactly once;
  `ν("https://doi.org/" + quote(k)) = k` and `ν(k)` never decodes.
- **INV-N4 (v1 conformance)** every key matches the v1 `doi` pattern; every
  valid PMID key matches the v1 `pmid` pattern.

(Property and table tests in `test_rde_identifiers.py`; the oracle uses a
separately written normalizer, §6.)

## 3. Anchors, roles and lookup

Each accepted record `r` has original keys `d(r), p(r) ∈ Key ∪ {⊥}`, notice
key `n(r)`, and anchor `a(r) = doi:d(r)` if `d(r) ≠ ⊥`, else `pmid:p(r)`,
else `rec:i`. Define for a DOI key `x`: `O_x = {r : d(r) = x}`,
`N_x = {r : n(r) = doi:x}`; `O_r ∩ N_r` is empty by construction because a
record whose notice equals its original has `n(r) = ⊥`.

- **INV-L1 (role separation)** `lookup(x)` reports `matched` iff `O_x ≠ ∅`,
  `notice_only` iff `O_x = ∅ ∧ N_x ≠ ∅`.
- **INV-L2 (no transitive union)** bridged events of a DOI query `x` are
  `{r : d(r) = ⊥ ∧ p(r) = q}` only when `{p(s) : s ∈ O_x} \ {⊥} = {q}`; one
  hop, never through a second DOI.
- **INV-L3 (compatibility)** a two-identifier query `(x, y)` is compatible iff
  `∀ s ∈ O_x: p(s) ∈ {y, ⊥}` and `∀ s ∈ O_y: d(s) ∈ {x, ⊥}`; incompatible
  queries return `ambiguous_identity` and never `O_x ∪ O_y` as one work.
- **INV-L4 (pagination)** for any page size `s ∈ [1, 100]`, the
  concatenation of pages equals the full ordered event list, and
  `total_event_count`, `projection` and `evidence_digest` do not depend on
  `s` or on the cursor.

## 4. Projection reducer

Let `E` be the matched events and `C` the comparable typed assertions
(RW rows and typed Crossref relations) about the query anchor. Group `C` by
proposition `π = (notice key, anchor)`; records without a notice key are
singleton propositions. `T(π)` is the set of types asserted for `π`.
Conflict groups: `K = {π : |T(π)| ≥ 2}`. Clear RW events:
`E_c = {e ∈ E : π(e) ∉ K}`. Let `R = {e ∈ E_c : type = retracted}` and
`S = {e ∈ E : type = reinstated}`.

`P(E)` is the first applicable rule of SPECIFICATION.md §11.1. Properties:

- **INV-P1 (no default positive)** `P(E) = retracted` ⇒ `R ≠ ∅`.
- **INV-P2 (concern then retraction)** adding expression-of-concern or
  correction events to an `E` with `P(E) = retracted` and `S = ∅` leaves
  `P = retracted` (retraction is not undone by a later correction or an
  earlier concern).
- **INV-P3 (unlinked reinstatement)** `S ≠ ∅` and `E \ S ≠ ∅` without
  supersession evidence ⇒ `P(E) = uncertain/null`.
- **INV-P4 (order independence)** `P(E)` depends only on the multiset of
  `(type, proposition, bounds, supersession)`, not on row order, ids or
  dates beyond `definitely_before`; in particular there is no
  latest-row-wins and no greatest-date-wins.
- **INV-P5 (no negative from absence)** no input yields a value outside the
  v1 enumeration, and `no_record` yields `not_found_in_checked_sources` only
  with status `uncertain` and non-empty provenance.
- **INV-P6 (evidence removal is conservative)** for an intervention view
  `E' ⊆ E` (removing assertions), `R(E') ⊆ R(E)` as sets of supporting
  observations: removal cannot create a new positive source observation. The
  projected value may change (for example a conflict may disappear), and
  every change is reported.
- **INV-P7 (redistribution)** adding an assertion whose origin is already
  present never increases `|support.origins|`.

## 5. Temporal evidence

A date evidence `t` has bounds `[t⁻, t⁺] ⊆ days ∪ {⊥}`. For RW values:
reported day `D` with day-of-month 1 ⇒ `t⁻ = t⁺ = ⊥`
(RW guide: day 1 encodes unknown day, month range start, season or volume);
otherwise `t⁻ = t⁺ = D`.

- **INV-T1 (partial order)** `A ≺ B ⇔ A⁺ ≠ ⊥ ∧ B⁻ ≠ ⊥ ∧ A⁺ < B⁻`. `≺` is
  irreflexive and transitive; ties, overlaps and unknown bounds are
  incomparable. No total order is presented as chronology.
- **INV-T2 (interval difference)** for cause `C` and effect `E`,
  `Δ ∈ [C⁻ − E⁺, C⁺ − E⁻]`, defined only when all four bounds exist.
- **INV-T3 (no year cutoff)** any proleptic Gregorian date with a 4-digit
  year is parseable; validity is calendar validity only.

## 6. Oracle comparison

For the set `K` of all valid original and notice DOI and PMID keys of the
real snapshot plus a set `A` of ≥ 1,000 synthetic keys known to be absent,
the oracle `Ω` (one streaming pass, separately written normalizer and role
map) gives `Ω(k) = (sorted ordinals in original role, sorted ordinals in
notice role)`. The index gives `Q(k)` from its SQL tables through the public
lookup. The gate requires `Ω(k) = Q(k)` for all `k ∈ K ∪ A` (0 mismatches).
This checks extraction and query fidelity, not the truth of any record.

## 7. Evidence Tension

`R(q, E)` is a finite record of comparison fields (SPECIFICATION.md §11.2).
For an intervention `ι` with view `ι(E)`, the report is
`Δ_ι = {f : R_f(q, E) ≠ R_f(q, ι(E))}`. `ι` is *applicable* iff
`ι(E) ≠ E`. Properties tested:

- **INV-X1 (controls)** if `ι(E) = E` then `Δ_ι = ∅`.
- **INV-X2 (locality)** computing `Δ_ι` reads only the assertions of the
  query's lookup; cost is linear in `|E|` and the number of interventions is
  at most 4 + 2 origins.
- **INV-X3 (no mutation)** the index bytes and `E` are unchanged.
- **INV-X4 (determinism)** equal inputs give byte-identical canonical
  reports.

The diagnostic value is measured against the event-log baseline on the
frozen 16-case set: diagnostic recall = detected expected classes / expected
classes; false diagnostics = changes reported on controls. The baseline
reports no dependency information, so its diagnostic recall is 0 by
construction; the measurable comparison is therefore also made on *answer
errors* the baseline makes on the same cases (claimed corroboration from a
redistributed channel, a precise date from a day-1 value, a retraction from a
notice-only or PMID-bridged link).

## 8. Ambiguity evaluation statistics

For held-out groups `g = 1..m` (`m ≥ 120`), baseline correctness `B_g` and
model correctness `M_g ∈ {0, 1}`. Discordant counts `b = #{B=1, M=0}`,
`c = #{B=0, M=1}`. One-sided exact McNemar: `p = P(X ≥ c)` with
`X ~ Binomial(b + c, 1/2)`. Accuracy gain `(Σ M − Σ B)/m`. Wilson interval
for a proportion `k/m` at `z = 1.96`:
`(k/m + z²/2m ± z·sqrt(k/m(1−k/m)/m + z²/4m²)) / (1 + z²/m)`.
Implemented in `src/citerift/retraction/stats.py`, tested against
hand-computed values. With `m = 120`, detecting a 10-point gain needs the
discordant pairs to be lopsided; this is a decision criterion, not a power
guarantee.

## 9. Changes after freezing

Sections 1 to 8 are left as frozen at `36696b3`. These changes, made while
implementing (SPECIFICATION.md 16 gives the reasons), replace the definitions
above where they differ:

1. **Notice sets (§3).** `N_x` is the set of records with a notice-role
   occurrence of `x` (notice DOI key `x`) whose original key of that scheme is
   not `x`; the grouping key `n(r)` is not used for it. Same for PMIDs.
2. **Two-identifier anchor (§3).** For a query `(x, y)` the anchor is `doi:x`
   when `O_x ≠ ∅`, else `pmid:y`; `query_pair` bridging needs `O_x ≠ ∅`
   (SPECIFICATION.md 16 items 4 and 10).
3. **Propositions (§4).** The proposition of an assertion is
   `π = (n, a)` for notice key `n` and anchor `a` (the code had grouped by `n`
   alone). A group `G` of one `π` with `|T(G)| ≥ 2` is split by type into
   `(n, a, t)` when every member is a Retraction Watch assertion, every type
   of `G` has an RW event, and `e ≺ f ∨ f ≺ e` for every pair of events of
   different types (INV-T1). Otherwise `G` stays one proposition, and a
   conflict group when `|T(G)| ≥ 2`. Splitting adds
   `SEQUENTIAL_EVENTS_SHARE_NOTICE`.
4. **Reinstatement (§4, rule 7d).** `S ≠ ∅` and no supersession evidence ⇒
   `uncertain`, null, also when `E \ S = ∅` (C-11).
5. **Unknown origin (§4).** Let `support(P)` be the clear assertions of the
   projected type. **INV-P8** `support(P)` made only of origin `unknown` ⇒
   `P = uncertain/null` (`SUPPORT_ORIGIN_UNKNOWN`). Every Crossref assertion
   records `dependence ∈ {known, unknown}`.

With these definitions the invariants of §4 read:

- **INV-P1** `P(E) = retracted` ⇒ `R ≠ ∅` and `R` has an assertion of known
  origin.
- **INV-P2** holds for added expression-of-concern or correction events on
  another proposition, and for added RW events on the same notice that are
  definitely ordered against every event of another type there. It does
  **not** hold for an added event on the same notice whose order is not
  established (equal dates, day-1 values, missing dates) or that comes from
  another origin: that is a conflict group, and with no other clear
  retraction the result is `conflicting`. This is the frozen conservative
  rule, kept on purpose: an unordered pair on one notice is a disagreement
  about what the notice is.
- **INV-P3** `S ≠ ∅` and no supersession evidence ⇒ `uncertain`, null.

Tests: `test_rde_policy_properties.py` (INV-P1, P2, P3, P8 over 400 seeded
sets each, with a non-vacuity floor; fail-first run
`evidence/fail-first/policy-properties-at-3a6f1eb.txt`),
`test_rde_policy_regressions.py` (each change, including the unordered and
publisher-disagreement cases that stay conflicts).

6. **Evidence Tension (§7).** A report states `base_unresolved` when
   `R(q, E)` has no settled value; a changed field of such a report is not
   counted as fragility of a settled answer. `exclude_origin(o)` reports the
   assertions whose dependence is `unknown` (`dependence_unknown`): they
   cannot be shown independent of `o` and are kept, not removed.
7. **Trimming (§2).** The outer whitespace removed before normalization is
   Unicode whitespace that is not a control, plus tab, LF and CR; INV-N2's
   `strip` means this set.

## 10. AI Protocol v2 (2026-10-28; SPECIFICATION.md 12.4)

§8 is the v1 analysis and is kept. v2 replaces its admission arithmetic.

- **Unit.** A lineage group: a connected component, under union-find, of
  records that share an original or notice DOI or PMID, or a Record ID. One
  query per group and one decision per group. Each candidate pair is scored
  by its own forward pass with no shared context, so the groups are the
  independent units of the paired test.
- **Score.** For a pair text `x`, `s(x) = z_true(x) − z_false(x)`, the
  difference of the model's next-token logits for the "1" and "0" tokens at
  the last position. It is a ranking score, not a probability.
- **Wrapper.** With ranked scores `s_1 ≥ s_2 ≥ …` (ties by candidate id), the
  decision is `select c_1` iff `s_1 ≥ τ_s` and `s_1 − s_2 ≥ τ_m`
  (`s_2 = 0` when there is one candidate); otherwise `abstain`. `τ_s` runs over
  the development score range in steps of 0.25, `τ_m ∈ {0, 0.5, 1, 2, 3}`;
  the chosen pair maximizes development correct decisions subject to
  development negative false selections not above the baseline's (ties:
  larger `τ_s`, then larger `τ_m`).
- **Errors.** `E_B = Σ (1 − B_g)` and `E_M = Σ (1 − M_g)`. Relative error
  reduction `RER = (E_B − E_M)/E_B`, undefined when `E_B = 0` (no superiority
  claim). Admission needs `RER ≥ 0.25` and the one-sided exact McNemar
  `p = P(X ≥ c)`, `X ~ Binomial(b + c, 1/2)`, below 0.05.
- **Intervals.** Percentile bootstrap over groups, 10,000 resamples, seed
  20261030, for `RER` and for `(E_B − E_M)/m`.
- **Attainability at the draw.** With `E_B` baseline errors and `o` oracle
  errors (positives whose target is not among the five candidates), the best
  case is `b = 0`, `c = E_B − o`, so `p_best = 2^−(E_B − o)`. Rule:
  `E_B ≥ 15` and `p_best < 0.001`. At the draw `E_B = 26`, `o = 0`,
  `p_best = 1.5 × 10^−8`.
- **Power (preregistered, PROTOCOL_V2.md 4).** If the model fixes a share `f`
  of the `E_B` baseline errors and breaks a share `g` of the `m − E_B`
  baseline-correct groups, then `c ~ Bin(E_B, f)` and `b ~ Bin(m − E_B, g)`.
  The power of the whole rule is computed exactly over both distributions.
  For `E_B = 29`, `m = 300`: 0.94 at `f = 0.4, g = 0`, 0.67 at
  `f = 0.4, g = 0.01`.
- **Observed.** `b = 54`, `c = 13`, `E_B = 26`, `E_M = 67`; `RER = −1.58`
  (95% −2.95 to −0.79), `p = 1.0`. In the terms above, the model fixed half of
  the baseline errors (`f = 0.5`) and broke `g = 54/274 = 0.20` of the
  baseline-correct groups. That is far outside the region where the rule can
  admit.
