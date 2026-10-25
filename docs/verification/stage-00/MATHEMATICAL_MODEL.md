# Stage 00 Mathematical Model (correction A-00-001)

Sections 1 to 5 of the accepted model (`superseded/741476c/MATHEMATICAL_MODEL.md`)
still hold, and the abstract model `simulations/stage00/state_machine_model.py`
has not changed. This document restates them briefly. It then adds what the
correction needed: the model of the history replay, its conformance with the
transition model, and the evidence-binding rules for the manifest, definition
and selection. Every check here is exhaustive over a finite configuration or
seeded and reproducible. None is statistical.

## 1. State space and transitions (unchanged)

- `S = {NS, AU, IP, BL, IM, VA, AC}` is the set of states.
- `A = {AU, IP, BL, IM}` is the active set.
- `K` is the set of stages, `E ⊆ K` the engineering stages, and `D` the
  acyclic dependency relation.

The relation `T` has 11 edges, 4 of them owner-only. The guards are those of
the accepted model, table 2.

A move `μ = (k, t, actor, inputs)` is permitted iff all four hold:

- `(σ_k, t) ∈ T`
- the actor may take the edge
- the guard holds
- the successor state `σ'` satisfies every invariant

## 2. Invariants

I1 to I7 are as before. The correction strengthens two of them and adds two.

- **I6 (replay consistency), strengthened.** Before the correction, `check`
  required only `fold(H, NSⁿ) = σ`, with each entry an edge of `T` taken by
  an allowed actor. Now each prefix must also be permitted:
  `∀ i: permitted(σ^{(i-1)}, h_i)`, where `σ^{(i)} = fold(h_1…h_i, NSⁿ)` and
  `permitted` evaluates the guards that the history decides. Those guards are:
  - single active engineering stage after the entry
  - dependencies accepted at entries into AU, VA and AC
  - a correction amendment recorded at or before a reopening
  - an open blocker at a block (IP→BL), and none at start (AU→IP), unblock
    (BL→IP) or verify (IM→VA)
  - an `owner_ref` on owner edges, not used before the last VA entry for an
    acceptance
- **I7 (evidence immutability), strengthened.** For a verified stage the
  record pins the following, each by sha256:
  - `M = {(p, sha256(p)) : p ∈ files(vdir) ∖ ignored}` (the manifest)
  - `δ = sha256(canon(definition ∪ policy))` (the definition hash)
  - the artifact hashes

  Required: the current `M` equals the pinned `M`, apart from amendment test
  reports added later. The current `δ` equals the pinned `δ`. And
  `content(owned, ρ) = content(owned, HEAD)`, compared by `git diff` of trees,
  not by `git log`. Comparing trees is what catches a merge that restores old
  content (F-01).
- **I8 (records match history).** Each authorization, verification and
  acceptance record equals the time and `owner_ref` of the last history entry
  that created it.
- **I9 (bounded time).** Every recorded time `≤ now + 5 min`.

## 3. Why the replay has to check each prefix

Take a history whose final state satisfies every state invariant but which
broke a rule on the way. For example, two stages are active at entry 7, and
one of them is moved back to NS by entry 9. Under the old I6 this history
passed (F-04). More generally, a property of the final vector cannot express
"each step was permitted". I3 can be violated and repaired, and I2 can be
broken at authorization and hidden once the dependency is accepted. So the
replay must evaluate the guards on every prefix. That costs `O(m · n)` per
check for `m` entries and `n` stages.

## 4. Dependency on a reopened stage (F-11)

The model's guard for AC→IP requires `single_active` and a correction
amendment. It does not require that the dependents are not accepted. The
implementation also required I2 to hold *in the current state* for every
accepted dependent. So once Stage 02 was accepted, reopening Stage 00 made
Stage 02's acceptance a permanent error, and the correction could never be
made. The model and the implementation disagreed (F-11).

Resolution:

- I2 is evaluated where the model evaluates it: at the moves into AU, VA and
  AC (§2).
- In the current state, a dependent whose dependency left AC after the
  dependent was accepted gets the warning `DEPENDENCY_REOPENED`, not an
  error.
- I3 still forbids a second active engineering stage, so the dependent
  cannot be reworked while its foundation is being corrected.

## 5. Conformance of the replay with the model

Let `R(H)` be the claim "`check` reports no history error for `H`", and
`P(H)` the claim "every move of `H` is permitted by the model". The replay is
conformant when `R(H) ⟺ P(H)` for every history the model can produce, plus
one adversarial extension of it. Evidence, tests and revision are taken as
satisfied, because the replay does not decide them. Those checks are covered
by I7 and their own tests.

`simulations/stage00/replay_conformance.py` checks this exhaustively.

1. Breadth-first search over the model gives every reachable status vector,
   with one shortest history `H_σ` for each.
2. For every vector `σ`, it forms `H_σ · μ` for every `μ` in this product:

   | Choice | Options |
   |---|---|
   | stage | `n` |
   | target state | 7 |
   | actor (owner or not) | 2 |
   | `owner_ref` present | 2 |
   | blocker open | 2 |
   | correction amendment | 2 |

   That is `n · 7 · 16` cases per vector.
3. For each case it compares `R` with `P`.

| Configuration | Stages (engineering) | Reachable vectors | Cases | Permitted by model | Disagreements |
|---|---|---|---|---|---|
| `small` (in the test suite) | 3 (2), 02 depends on 00 and 01 | 134 | 45,024 | 4,218 | 0 |
| `full` | 4 (3), 02 and 03 depend on 00 and 01 | 459 | 205,632 | 15,640 | **0** |
| `full` at `ae2ce9e` (before the correction) | same | 459 | 205,632 | 15,640 | **12,872** |

Count check: `459 × 4 × 7 × 16 = 205,632` and `134 × 3 × 7 × 16 = 45,024`. The first disagreements
at `ae2ce9e` are owner authorizations of Stage 02 with its dependencies
unaccepted. The model refuses them, and the old replay accepted them (F-04).

What this does not prove: conformance for histories longer than
`max_history_length` (28), other dependency shapes, or adversarial histories
that are not one move away from a model history. The seeded mutation property
test (TEST_RESULTS.md §3) covers some of the latter.

## 6. Evidence binding (extended)

A test report `r` supports verification at revision `ρ` iff all of the
following hold:

- the conditions of the accepted model §7 hold
- `r.selection.complete = true`
- no test recorded as not run (`totals.not_run = 0`)

The plugin sets `complete` to false when any test was deselected or did not
run.

`complete` holds iff all of the following hold (F-07):

- every argument resolves to the repository root or a configured test path
- no argument names a node id (`::`)
- no `-k`, `-m`, `--ignore`, `--ignore-glob`, `--lf` or `--sw` was given

A JSON document is accepted only if no object has duplicate keys (F-18).
Without this rule, a reviewer and the checker can read different values from
the same bytes.

The definition hash is `δ = sha256(canon({f: stage[f] for f in DEFINITION_FIELDS} ∪ {policy}))`,
with `canon` = sorted keys, no whitespace, UTF-8.

## 7. Date and time model (contracts and registry)

`utc_timestamp` is `YYYY-MM-DDTHH:MM:SS(.f{1,6})?Z`. It must also denote a
real instant: `datetime.strptime` succeeds, so February 30 is rejected. Event
order compares parsed instants, never strings. As strings,
`12:00:00.5Z < 12:00:00Z`, which is the false positive of F-09. A partial
date `YYYY`, `YYYY-MM` or `YYYY-MM-DD` must be a real calendar date.

## 8. Limits of the model (unchanged in substance)

Guard inputs are booleans chosen by an adversary. The model cannot tell:

- whether an `owner_ref` contains approval (R-002)
- whether a forgery that is consistent everywhere is genuine (R-003)
- whether CI ran the unmodified workflow (R-016)

These are outside any check that reads only the repository.
