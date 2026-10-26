# Stage 00 Mathematical Model (correction A-00-001)

Sections 1 to 5 of the accepted model (`superseded/741476c/MATHEMATICAL_MODEL.md`)
still hold, with one guard added: an acceptance needs no open blocker (X-10).
The abstract model `simulations/stage00/state_machine_model.py` changed only
there. This document restates them briefly. It then adds what the
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
the accepted model, table 2, except that VA→AC also requires no open blocker
(X-10). Before this, both the model and the replay let a stage be accepted
with a blocker open.

`D` is fixed by the registry schema for every stage (X-07). Without that, an
edit of `depends_on` before authorization was not a history entry, so it
could remove a dependency that the guards would then never check.

A move `μ = (k, t, actor, inputs)` is permitted iff all four hold:

- `(σ_k, t) ∈ T`
- the actor may take the edge
- the guard holds
- the successor state `σ'` satisfies every invariant

## 2. Invariants

I1 to I7 are as before. The correction strengthens two of them and adds five.

- **I6 (replay consistency), strengthened.** Before the correction, `check`
  required only `fold(H, NSⁿ) = σ`, with each entry an edge of `T` taken by
  an allowed actor. Now each prefix must also be permitted:
  `∀ i: permitted(σ^{(i-1)}, h_i)`, where `σ^{(i)} = fold(h_1…h_i, NSⁿ)` and
  `permitted` evaluates the guards that the history decides. Those guards are:
  - single active engineering stage after the entry
  - dependencies accepted at entries into AU, VA and AC
  - a correction amendment recorded at or before a reopening, not cited by
    an earlier reopening (V-08)
  - an open blocker at a block (IP→BL), and none at start (AU→IP), unblock
    (BL→IP), verify (IM→VA) or accept (VA→AC, X-10)
  - an `owner_ref` on owner edges; for an acceptance, one not used by a
    history entry or an amendment at or before the last VA entry (F-17, V-07)
  - for an amendment, an `owner_ref` not cited by a history entry or another
    amendment at or before its own instant, the same second included (X-13,
    Y-07); the reopening that uses a correction amendment may share its
    reference
- **I7 (evidence immutability), strengthened.** For a verified stage the
  record pins the following, each by sha256:
  - `M = {(p, sha256(p)) : p ∈ files(vdir) ∖ ignored}` (the manifest;
    `ignored` is what `git check-ignore` reports, S-01)
  - `δ = sha256(canon(definition ∪ policy))` (the definition hash)
  - the artifact hashes

  Required: the current `M` equals the pinned `M`, apart from test reports of
  enhancement amendments added later. Every other amendment's test report is
  checked against its own hash (V-05). The current `δ` equals the pinned `δ`. And
  `content(owned, ρ) = content(owned, HEAD)`, compared by `git diff` of trees,
  not by `git log`. Comparing trees is what catches a merge that restores old
  content (F-01).
- **I8 (records match history).** Each authorization, verification and
  acceptance record equals the time and `owner_ref` of the last history entry
  that created it.
- **I9 (bounded time).** Every recorded time `≤ now + 5 min`, where `now` is
  the clock of the machine running `check` (V-11, R-012).
- **I10 (unique ids).** Amendment ids are unique within a stage, and blocker
  ids are unique within a stage (V-09).
- **I11 (enhancement contracts).** If an enhancement amendment changes a
  contract under `schemas/contracts/` from its content at the stage's last
  acceptance, the contract's version must increase, and every accepted valid
  fixture must still validate against the changed contracts (X-13). Whether
  the change keeps the contract's meaning is not decided here; it is the
  owner's judgment.
- **I12 (amendment placement).** An amendment recorded at instant `t` needs
  `σ_k = AC` after the stage's entries before `t`, or an entry into AC at
  `t` itself (Y-06). The covering set of the drift rule (I7) holds the
  verified revision and only the enhancements recorded at or after the
  stage's current acceptance, while it is accepted.

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
| `small` (in the test suite) | 3 (2), 02 depends on 00 and 01 | 134 | 45,024 | 4,104 | 0 |
| `full` | 4 (3), 02 and 03 depend on 00 and 01 | 459 | 205,632 | 15,160 | **0** |
| `full` at `ae2ce9e` (before the correction), model before X-10 | same | 459 | 205,632 | 15,640 | **12,872** |

The permitted counts fell from 4,218 and 15,640 when the model gained the
X-10 guard: acceptances with an open blocker are no longer permitted. The
`ae2ce9e` row was measured with the model as it was then, so its 12,872 are
disagreements with the earlier model.

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
- the counts in `r` are non-negative integers, and its file and conftest
  lists are lists of strings (X-05)
- `r.dirty = false`, where a tree is dirty if `git status` lists a path, if a
  tracked file is flagged skip-worktree or assume-unchanged, if a tracked
  file's bytes do not hash to its index entry (Z-01), or if the report path
  itself is tracked, the path read literally (Y-01, Y-02, Z-05). The bytes are
  read when the run starts (`pytest_configure`), by the test process; this binds the tree,
  not code running in that process (R-004)
- `r.selection.complete = true`
- no test recorded as not run (`totals.not_run = 0`), and every outcome is
  `passed`, `failed` or `error`: skipped, xfailed and xpassed tests did not
  show their rule, so their count must be 0 (Y-03)
- `tests(ρ) ⊆ r.selection.files`, where `tests(ρ)` is the set of committed
  files `tests/**/test_*.py` and `tests/**/*_test.py` in the tree of `ρ`
  (V-01)

Let `C` be the node ids pytest collected, `F` the node ids left after every
`collection_modifyitems` hook (the plugin's hook runs last), and `D` the node
ids reported as deselected. These are lists, compared as sets of node ids,
not as counts: a conftest that removes tests and adds repeats of others keeps
the counts equal (X-03). `complete` holds iff all of the following hold
(F-07, V-01, X-02, X-03):

- every argument resolves to the repository root or a configured test path
- no argument names a node id (`::`)
- no `-k`, `-m`, `--ignore`, `--ignore-glob`, `--lf` or `--sw` was given
- every `-o` override is in the allowlist `{strict_markers=true}`, which is
  how pytest records `--strict-markers`
- the ini file is the repository's `pyproject.toml`
- the collection settings `python_files`, `python_classes`,
  `python_functions` and `testpaths` have their fixed values (X-02)
- no plugin was loaded with `-p` or `PYTEST_PLUGINS` (X-03)
- every conftest pytest loaded is tracked at `ρ` (X-03)
- `D = ∅` and `C ∖ (F ∪ D) = ∅` (no test dropped silently)
- `|F| = |set(F)|` (no test repeated)
- every item in `F` has an outcome

`tests(ρ) ⊆ files` catches a file never collected at all, for example through
`collect_ignore` in a conftest. None of these rules binds code that runs
inside the test process and writes a false report itself, or changes the
plugin's lists before they are written: the report is produced by the process
it describes (R-004). CI's check of the committed tree, and review of
committed test code, are what stand against that.

A JSON document is accepted only if no object has duplicate keys (F-18).
Without this rule, a reviewer and the checker can read different values from
the same bytes.

The definition hash is `δ = sha256(canon({f: stage[f] for f in DEFINITION_FIELDS} ∪ {policy}))`,
with `canon` = sorted keys, no whitespace, UTF-8.

Gate evidence. For a gate `g` with cited references `E(g)`, let
`files(g) = E(g) ∖ URLs`. The gate is supported iff `files(g) ≠ ∅` and every
`p ∈ files(g)` is pinned: `p ∈ dom(M)`, or `p` lies under an owned path and
`p ∈ tree(ρ)` (its content is then bound by I7's drift rule, which compares
committed trees; an ignored or untracked file is in neither, Y-09). A URL is
never pinned (F-02, V-02).
Every `p` must also be a plain path: no empty, `.` or `..` segment and no
symbolic link on the way, so `p` names the file that `M` or the drift rule
actually binds (X-01).

CI record. With `repo` = `project.repository`, the record `c` supports the
verification iff `c.head_sha = ρ`, `c.conclusion = success` and `c.run_url`
is, as a whole and compared without case, `https://github.com/repo/actions/runs/n`
for a decimal `n` (Y-10; a prefix test let `..` segments lead to another
repository, Z-02). The checker reads the record, not the run.

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
- whether CI ran the unmodified workflow, or with an unmodified
  `pyproject.toml` and `uv.lock` (R-016)
- whether code inside the test process wrote its own report (R-004)

These are outside any check that reads only the repository.
