# Stage 03 mathematical model

The formal definitions behind the engine's claims and the evaluation. Notation: `T` is the source text as a
sequence of Unicode code points, `B = utf8(T)` its bytes, `H` the retained render bytes.

## 1. Anchors

For a code point index `i`, `byte(i) = Σ_{j<i} len(utf8(T[j]))`, computed once by prefix sums over the non-ASCII
code points (`textmap.ByteMap`, binary search). An exact source anchor for an occurrence is the tuple
`(cp_start, cp_end, byte_start, byte_end, raw, sha256(utf8(raw)))` with

    T[cp_start:cp_end] = raw,   B[byte_start:byte_end] = utf8(raw),   byte_start = byte(cp_start),   byte_end = byte(cp_end).

All four equations are re-checked by `verify` from the retained bytes; any failure is `ANCHOR_MISMATCH`. A node
interval is used as an anchor only when `T[start:end] = str(node)` holds for the parse node (otherwise
`ANCHOR_NOT_EXACT`), and the parse must be lossless: `str(parse(T)) = T`.

## 2. Digests

`canon(x)` is the UTF-8 encoding of `x` with sorted keys, no insignificant whitespace and no NaN or infinity.
`digest(x) = SHA-256(canon(x))`. For an extraction document `D`,
`D.extraction_digest = digest(D \ {extraction_digest})` and `D.config_digest = digest(D.config)`. A bundle is named
by `SHA-256(capture.json bytes)` and each artifact by `SHA-256(artifact bytes)`. Replay reports `reproduced` iff
the recorded `D` satisfies its own digest equation and `extract(bundle, D.config) = D` (whole-document equality,
which with the digest equation implies equal digests).

## 3. Binding

Let `key(r) = (group(r), name(r))` with both trimmed and entity-decoded. Definitions with one key form a class `K`.
Container state: `single_definition` if `|K| = 1`; `identical_definitions` if all bodies are equal after trimming;
`conflicting_definitions` otherwise (no body chosen). A use `u` with a name binds to the container of `key(u)` if it
exists (`bound`, or `bound_conflicting`), else `definition_missing`. Anonymous refs are their own containers.
Identical `sfn`-family calls (equal after removing whitespace) form one container.

## 4. Roles

`role(c)` is the first matching rule of the decision list in SPECIFICATION.md 11.5, a total function of the
candidate's frames (template chain with parameter names), origin and container membership. Two properties follow
directly from the list and are tested: (P1) a candidate inside a marker template is never `primary_citation_field`;
(P2) a candidate in a citation template is `primary_citation_field` only if it is the value of an identifier field
of the innermost citation template and that parameter is not repeated later in the same template.

## 5. Render alignment

Let `S = (s_1..s_m)` be the source uses of one group (article text, template output, nested) and `R = (r_1..r_n)`
the rendered reference markers of the same group, both in document order. A name `x` is an **anchor name** when
`#{i : name(s_i) = x} = #{j : name(r_j) = x} ≥ 1`; the k-th source use with name `x` is paired with the k-th marker
with name `x`. Anchors split `S` and `R` into segments `(S_t, R_t)`. A segment is matched position by position iff
`|S_t| = |R_t|` and every pair is compatible (the marker's `data-mw` is readable; for `<ref>` tags group and name
are equal after trimming and entity decoding, anonymous on both sides counting as equal; for template-generated
uses a name stated on both sides must agree), and the pairing respects the list numbering: for the pairs whose
source use is its container's first use, the paired notes' positions `(list, index)` are strictly increasing within
each list in source order, continuing from the pairs already accepted in that alignment (Cite numbers notes in
order of first use). Otherwise every use in it is `unmatched` (unless paired by unique shared content). Uses produced in template
output are paired with markers of the same transclusion; a pair that is not fixed by name or position is accepted
only when it is unique in both directions and shares a URL or identifier with the note (bases
`unique_url_in_reference_text`, `unique_identifier_in_reference_text`). The rule never pairs across a length mismatch, so an inserted or missing marker leaves the segment
unmatched instead of shifting attachments. A container `c` is matched to note `n` iff every matched use of `c` points
to `n`, `n` occurs once as a DOM id, and no other container is matched to `n`; otherwise its render state is
`conflicting_notes` or `note_ambiguous` and no region is attached.

## 6. Marker state

For the region text split into shown text `X`, citation text `C` (inside `<cite>`) and hidden text `Z`, with warning
terms `W`, ambiguous terms `A` and red links `L` to marker templates:

    state = recognized_warning_text            if W ∩ X ≠ ∅
            ambiguous_text                     else if W ∩ C ≠ ∅ or A ∩ (X ∪ C) ≠ ∅ or (W ∪ A) ∩ Z ≠ ∅
            missing_template_link_only         else if L ≠ ∅
            no_recognized_warning_in_inspected_region   else, only when a region was matched and inspected
    state = not_inspected                      when the container has no matched, unambiguous region
    state = unavailable                        when there is no accepted render

`∩` means term occurrence under the language's matching rule (case folding; English word boundaries; Arabic with
harakat and tatweel removed and attached letters allowed). The "no warning" state is reachable only from an inspected
region with no term anywhere in it, including hidden text.

## 7. Retry schedule

For attempts `a_1..a_k` of one operation with end times `e_i`, Retry-After `ρ_i` (seconds, possibly absent), minimum
interval `δ = 10`, backoff `β = 10`, deadline `t_0 + Δ` (`Δ = 180`) and at most `N = 3` attempts:

    wait_k = max(δ, ρ_k)                 if ρ_k present
             max(δ, β · 2^(k-1))         otherwise
    start_{k+1} = e_k + wait_k

The next attempt runs iff the last answer was retryable, `k < N` and `start_{k+1} < t_0 + Δ`; otherwise the result
is the last code, `ATTEMPTS_EXHAUSTED`, `DEFERRED_RETRY_AFTER` with `not_before = e_k + ρ_k` (when `ρ_k` is present)
or `DEADLINE_EXCEEDED`. Across processes the gate adds `start ≥ e_last(any process) + δ`. The simulation
(`simulations/stage03/fetch_policy_sim.py`) checks invariants I1-I7 against an independent reference model of this
schedule.

## 8. Evaluation statistics

Matching (FROZEN_PROTOCOL.md 5): an annotated point `p` matches a predicted interval `[s, e)` iff `s ≤ p < max(e, s+1)`,
nearest start first, one to one; identifiers match by same scheme and maximal positive overlap, one to one.
Per language, micro-averaged: `precision = TP / (TP + FP)`, `recall = TP / (TP + FN)`, binding accuracy, key error
rate, role agreement and render-link precision and coverage as defined in FROZEN_PROTOCOL.md 6.

Uncertainty: articles are the sampling unit, so the 95 % interval of a ratio is the 2.5 and 97.5 percentiles over
2000 bootstrap resamples of articles with replacement (seed 20261028), recomputing the micro ratio each time. For a
zero-tolerance count with `x` errors in `n` items, the one-sided 95 % Clopper-Pearson upper bound on the error rate is
the `p` solving `P(X ≤ x | n, p) = 0.05`: `1 − 0.05^{1/n}` for `x = 0` (5.8 % at `n = 50`, 3.0 % at 100, 2.0 % at
150). These bounds describe the sample, not the population of articles, and ignore within-article correlation;
the bootstrap intervals are reported next to them for that reason.

## Mathematical model: retained marker witness invariant

For retained source bytes S, retained HTML H, and validated limits C, let B(S,H,C) be the
source-container to rendered-region binding reconstructed in the bounded offline worker.
Let M(S,H,C) be the ordered marker records produced by deterministic region reconstruction
and contextual matching over B. Verification requires the supplied marker container set to
equal the reconstructed set and, for every container c, D.markers[c] = M(S,H,C)[c].
This equality covers the authorized region, evidence multiplicity and order, matched text,
locator, snippet, kind, part, exclusion, hiding basis, source markers, abstention and state.
A second genuine occurrence of the same word cannot authenticate an edited occurrence.
The verifier still checks local locator/anchor/hash consistency and retains its caches.
The worker preserves the established wall/CPU/address-space bounds and offline guard.
Replay remains complete document re-derivation; this marker check does not prove that every
non-marker semantic field equals a fresh extraction. Shared reconstruction rules can share
implementation mistakes. The verifier establishes consistency with retained bytes, not
publisher authenticity, scientific truth, or actual browser visibility.


## Publisher DOI path with a page-view route (RF-60, 2026-11-02)

Let `u` be a URL with a host other than a DOI resolver. Let `P` be its raw path after the ASCII `/doi/`, with the
optional `abs|full|pdf|epdf|book|reader/` prefix removed. Let `W` be the ASCII route words. `dec(·)` is
percent-decoding applied once, and `D` is the DOI shape `10\.[0-9]{4,9}/.+`.

- If `P = R + "/" + w + ("" | "/")` with `w ∈ W` (ASCII case-insensitive), and `dec(R) ∈ D`, and the last segment
  of `dec(R)` is not in `{"", ".", ".."}`, then the normalizer input is `dec(R)`, and the steps
  `DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS` and `PAGE_VIEW_SEGMENT_REMOVED` are recorded.
- Otherwise the input is `dec(P)`. `DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS` is recorded when `P` or `dec(P)` ends in a
  route.

The rule is applied at most once, so it never shortens repeatedly. The key is `normalize_doi(input)`, the accepted
Stage 02 function, unchanged.

## Final-campaign sample bounds (2026-11-02)

One-sided 95 % Clopper-Pearson upper bounds (section 8) for the adjudicated final campaign:

| Language | Measure | Observed | Upper bound |
|---|---|---|---|
| ar | key errors | 0 / 32 | 8.9 % |
| ar | identifier misses | 1 / 33 | 13.6 % |
| ar | definition false positives | 10 / 116 | 14.2 % |
| en | key errors, frozen candidate | 1 / 52 | 8.8 % |
| en | key errors, post-exposure RF-60 | 0 / 52 | 5.6 % |

The RF-60 figure is measured on exposed data, so it describes the repair on the data it was designed from. It is not
an independent estimate.

## Confirmation-campaign estimates (2026-11-03)

The estimands of amendment section 8, computed by
`evaluation/confirmation-2026-11/scripts/intervals.py` with the frozen scorer's aggregate, seed 20261028 and 2000
article-cluster resamples (`evaluation/confirmation-2026-11/campaign/scores/intervals.json`, adjudicated labels):

| Language | Measure | Observed | 95 % interval |
|---|---|---|---|
| ar | identifier recall | 98 / 103 = 0.951 | bootstrap [0.857, 0.992] |
| ar | key errors (G2) | 0 / 98 | one-sided upper 3.0 % |
| ar | promotions (G3a) | 0 / 98 | one-sided upper 3.0 % |
| en | unit precision (G5c) | 126 / 145 = 0.869 | bootstrap [0.718, 0.971] |
| en | key errors (G2) | 0 / 48 | one-sided upper 6.1 % |
| en | promotions (G3a) | 0 / 48 | one-sided upper 6.1 % |
| en | warning sensitivity (challenge) | 6 / 6 | Clopper-Pearson [0.541, 1.000] |

At these sample sizes a zero count bounds the rate only at 3 % (n = 98) and 6 % (n = 48), not at the 1 % of the G2
threshold. Gates are decided on the point values, as frozen; the intervals are reported, not gated.


## Citation-unit classes (owner instruction D-035, engine 1.1.0)

**Notation.**

For a definition $d$ (a ref with content, not a short footnote) let:
- $T(d)$ be the templates called in $d$ outside any other template of $d$;
- $\mathrm{own}(d)$ be the text runs of $d$ outside every template called in $d$;
- $L(d)$ be the external links among $\mathrm{own}(d)$, together with the DOI/PMID candidates of $d$ that are not
  template fields and are nested only in profile identifier wrappers.

For a template $t$ let $e(t) \in \{\mathsf{cite}, \mathsf{short}, \mathsf{none}, \bot\}$ be its render evidence:
- $\mathsf{cite}$: a `<cite class="citation">` in its own output;
- $\mathsf{short}$: a `#CITEREF` link and no cite element;
- $\mathsf{none}$: neither;
- $\bot$: no usable output of its own.

Equal source keys must give one value of $e$, otherwise $e = \bot$.

**Note evidence** (review 2, RV2-4). Let $\bot_0(t)$ hold when no render transclusion has $t$'s key at all (so not a
conflict and not an unexpanded call). For a definition $d$ with $C(d) \cup G(d) = \emptyset$ whose container is
matched to exactly one note $n(d)$ (backlinks agree, no conflicting definitions, no unexpanded template in the note),
let $e(n(d))$ be the same function of the note's elements, and $B(d) = \{t \in \Delta(d) : e(t) = \bot \wedge
\bot_0(t)\}$. If every $t \in \Delta(d) \setminus B(d)$ has $e(t) = \mathsf{none}$, then $e$ is redefined on
$B(d)$:
- $e(n(d)) = \mathsf{none} \Rightarrow e(t) := \mathsf{none}$ for every $t \in B(d)$;
- $|B(d)| = 1 \Rightarrow e(t) := e(n(d))$ for its one element.

The model is then rebuilt with the redefined $e$. A note shows the whole definition, so $e(n(d)) = \mathsf{none}$
implies that no template of $d$ writes citation markup or a short link; with one template without evidence and
every other one showing none, a mark in the note can only be that template's.

**Kind sets.** Let $P$ be the profile citation and external-data templates, and $U \subseteq P$ those that are citation
templates only by the RF-37 name rule.

**Units.** Let $N(t)$ hold when some template of $P$, or some template the profile does not classify, is called
inside the arguments of $t$ within the same ref: Parsoid renders it as part of $t$, so $t$'s output also holds its
markup. An unclassified nested template $s$ is not counted when it is a literal magic word (`{{!}}`, `{{=}}`), or
when every single-template transclusion of its canonical name in the render has evidence $\mathsf{none}$ and there is
at least one (review 2, RV2-5). Literal magic words are also excluded from $\Delta(d)$ (RV2-8). The template units of $d$ are

$$C(d) = \{t \in d : t \in P \wedge \neg(t \in U \wedge e(t) = \mathsf{short})\}, \qquad
G(d) = \{t \in T(d) : t \notin P \wedge e(t) = \mathsf{cite} \wedge \neg N(t)\}.$$

$C(d)$ is as in 11.3, except for RF-37 templates rendered as short-citation links. $G(d)$ is
`unsupported_citation_template`. Let $\Delta(d) = \{t \in T(d) : t \notin P \vee t \in U\}$ be the templates whose
render is read as evidence. When $C(d) \cup G(d) = \emptyset$, the class of $d$ is the first that applies:

1. $L(d) \neq \emptyset \Rightarrow D$;
2. $\mathrm{alnum}(\mathrm{own}(d))$:
   - $\exists t \in \Delta(d): e(t) \in \{\mathsf{short}, \mathsf{cite}, \bot\} \Rightarrow H$ (beside a short-citation
     link; beside citation markup that holds nested templates; beside a template the render cannot show);
   - $d$ is generated by the `efn` family $\Rightarrow H$;
   - otherwise $D$;
3. $\mathrm{alnum}$ holds only inside tags the engine does not read (`<nowiki>`, `<pre>`, …) $\Rightarrow H$;
4. $T(d) \neq \emptyset \wedge \forall t \in T(d): e(t) = \mathsf{short} \Rightarrow E$;
5. $T(d) \neq \emptyset \Rightarrow H$;
6. otherwise empty: no unit (class F is now only this case and an `efn` without own text).

Here $\mathrm{alnum}(\mathrm{own}(d))$ means some character of the own text is in a Unicode letter or number
category. Only class $D$ yields `unstructured_text`; class $H$ yields the issue `UNIT_CLASSIFICATION_UNRESOLVED`.

**Invariant.** $C(d) = \emptyset$ alone never implies $D$. $D$ needs a locator, or own text in a non-explanatory
reference where every template of $\Delta(d)$ beside the text has render evidence $\mathsf{none}$.

**Monotonicity.** Against the 1.0.0 rule ($C(d) = \emptyset \Rightarrow D$), the set of `unstructured_text` units can
only shrink, with one exception. A definition whose only template unit was an RF-37 template rendered as a
short-citation link, and which also gives a locator, becomes $D$. There are none in the 146 retained real bundles
(`design/unit-semantics/differential/DIFFERENTIAL.md`). Outside that exception, false-positive `unstructured_text` units cannot
increase. The new $G$ units are new predictions: their precision is measured, not implied. Unit recall can decrease only
where a labelled-unstructured definition falls into E, F or H. On the three exposed campaigns no labelled
unstructured definition did (`design/unit-semantics/SEMANTIC_DECISION.md` section 7). This is regression evidence,
not an estimate.

**Determinism and cost.** Classification reads indexes built once per document:
- templates by ref;
- candidates by ref;
- render evidence by template key, over transclusions with one part.

Each definition costs $O(|T(d)| + |\mathrm{cand}(d)|)$. The whole step is $O(n)$ in templates, candidates and
transclusions, plus one walk of the output elements of each transclusion whose key is wanted. $N$ is one walk up the parent chain of
each citation-like template, $O(n \cdot \mathrm{depth})$. No step depends on
iteration order: sets of evidence values are compared only for size, and unit order is by span.

Note evidence needs the matched notes, so when it redefines $e$ on some template the model is built and reconciled a
second time. Containers, uses and their notes do not depend on units, so the second reconciliation matches the same
notes and the procedure stops after two passes; its cost is at most twice that of one pass.

**Bibliography entries.** Let an entry $b$ span the lines of its list items, and $T_b$ the templates that start
inside $b$. A candidate $c$ of $b$ that is not a template field gives $D$ when $c$ is nested in $T_b$ only in
profile wrappers, or when $b$ has letters or digits outside every template of $T_b$ and every ref starting in $b$
(review 2, RV2-3). A candidate off a list line belongs to the list line on which the innermost template holding it
starts (RV2-7).

## D-035 confirmation estimates and the G6b computation (2026-11-03)

The estimators are those of the confirmation-campaign section above, applied to 24 + 24 unexposed articles
(`evaluation/confirmation-d035/campaign/scores/intervals.json`).

**G6b.** With $L$ engine render links and $F$ false attachments, the frozen gate value is
$F - \max(1, \lfloor 0.01\,L \rfloor)$, and the gate passes iff it is $\le 0$. Arabic: $L = 184$, $F = 2$, value
$2 - 1 = 1$, fail. English: $L = 203$, $F = 0$, value $0 - 2 = -2$, pass. The exact two-sided 95 % Clopper-Pearson
interval of the Arabic false-attachment rate, $2/184$, is $[0.0013, 0.0387]$; it is reported, not gated.

**Model correction for section 5.** For a group of uses produced in one template's output, let $S_x$ and $R_x$ be the
source uses and rendered markers with name $x$. The pairing of section 5 is fixed by name only when
$|S_x| = |R_x| = 1$. When $|S_x| = |R_x| = k > 1$, the $k!$ bijections between $S_x$ and $R_x$ are indistinguishable
by name and text (only the `data-mw` `body` of the definition's marker separates the definition from the reuses),
and the template, not source order, decides which one the render realizes. The specified
rule is to accept a bijection only on evidence that excludes the others, and otherwise to abstain on all of $S_x$.
The implementation at `fff0e5b` takes the order-preserving bijection instead (SPECIFICATION.md, "Known defect found
by the D-035 confirmation").

## Same-name pairing inside template output (owner instruction D-036, engine 1.2.0)

Replaces, for template output only, the k-th-to-k-th rule of section 5 for a name `x` with
`n = #{s ∈ S : name(s) = x} = #{r ∈ R : name(r) = x} ≥ 2` (R-038). Let `U` and `M` be those uses and markers.

**Roles.** `ρ(u) = def` iff the source use has content; `ρ(m) ∈ {def, reuse, ⊥}` from `data-mw` (`⊥` for unreadable
or contradictory). If some `ρ(m) = ⊥` or `#{u : ρ(u)=def} ≠ #{m : ρ(m)=def}`, the pairing is empty. Otherwise the
problem splits into two independent role classes `(U_def, M_def)` and `(U_reuse, M_reuse)` of equal sizes.

**Support.** For each use `u`, `a(u)` is its source anchor (visible text) or, if absent, its number tuple `ν(u)`;
`t(m)` is the marker's preceding text and `ν(m)` its numbers. Define the relation
`u ~ m` iff `t(m)` ends with `a(u)` at a word boundary (an anchor shorter than 3 characters only when
`t(m) = a(u)`), or `ν(u) = ν(m)` when `u` has only numbers. A use with neither has no constraint.

**Feasible pairings.** A bijection `π : U_c → M_c` within a class `c` is feasible iff for every `u`: if some marker
of `M_c` supports `u`, then `u ~ π(u)`; and if `π(u)` supports some use of `U_c`, then `u ~ π(u)`. A use whose text
or numbers match no marker of its class carries no constraint (its text was transformed by the template, so it says
nothing about position).

**Decision.** `_settle` repeatedly fixes `(u, m)` when, among the unfixed elements, `u` has exactly one feasible
marker or `m` exactly one feasible use. If every element gets fixed, the result is the unique feasible bijection
(each fixing step removes no other feasible bijection), and it is accepted. Otherwise only pairs `(u, m)` with
`{m' : u ~ m'} = {m}` and `{u' : u' ~ m} = {u}` are kept; every other use of the class is abstained. A use `u` with
an anchor whose supporting markers all lie in the other class empties the pairing of `x`.

**Properties.** (i) No pairing depends on source or render order. (ii) A pair is emitted only when it is forced by
roles, by mutually unique support, or by elimination within a completely settled class, so a swap requires the
evidence itself to be wrong (a marker whose `data-mw` names the wrong role, or a rendered text that equals another
parameter's text). (iii) For `n = 1` the rule is unchanged. (iv) The cost is `O(n²)` comparisons for `n ≤ 2000`.

