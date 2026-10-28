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
uses a name stated on both sides must agree); otherwise every use in it is `unmatched`. Uses produced in template
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
