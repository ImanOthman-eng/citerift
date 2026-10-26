# Stage 00 Mathematical Model

This is the formal model of the governance rules, written before the
implementation. The abstract simulation (`simulations/stage00/state_machine_model.py`)
implements it independently of `src/citerift`; SIMULATION_REPORT.md gives the
results. Nothing here is a statistical claim: all checks are exhaustive over a
finite model or seeded and reproducible.

## 1. State space

Let `S = {NS, AU, IP, BL, IM, VA, AC}` be the stage states and
`A = {AU, IP, BL, IM} ⊂ S` the active set. Let `K = {0, …, n-1}` be the stages,
`E ⊆ K` the engineering-agent stages (Stage 01 is external, so `01 ∉ E`), and
`D ⊆ K × K` the dependency relation, where `(k, d) ∈ D` means `k` depends on
`d`. `D` must be acyclic (checked with Kahn's algorithm; a cycle is the error
`DEPENDENCY_CYCLE`).

A project state is a vector `σ ∈ Sⁿ` together with the record set `R(σ)`
(authorization, implementation, verification, acceptance, blockers,
amendments) and an append-only history `H = (h₁, …, h_m)`.

## 2. Transition relation

Edges `T ⊂ S × S` (11 of the 49 ordered pairs):

| Edge | Actor | Guard |
|---|---|---|
| NS→AU | owner | `owner_ref` present ∧ every dependency is AC ∧ single-active |
| AU→NS | owner | `owner_ref` present |
| AU→IP | any | no open blocker |
| IP→BL | any | at least one open blocker |
| BL→IP | any | no open blocker |
| IP→IM | any | revision exists |
| IM→IP | any | true (rework) |
| IM→VA | any | artifacts ∧ test report ∧ gates ∧ CI ∧ revision ∧ no blocker ∧ no critical defect ∧ dependencies AC |
| VA→IP | any | single-active (rework) |
| VA→AC | owner | `owner_ref` present ∧ verified evidence still valid ∧ dependencies AC |
| AC→IP | owner | `owner_ref` ∧ correction amendment ∧ single-active |

A move `μ = (k, t, actor, inputs)` is permitted iff `(σ_k, t) ∈ T`, the actor
matches, the guard holds, and the successor state `σ'` (with `σ'_k = t`,
`σ'_j = σ_j` for `j ≠ k`) satisfies every invariant `C(σ') = ∅`. The
implementation realizes the last condition literally: `propose()` applies the
move to a deep copy and runs the full consistency check on the copy.

## 3. Invariants

- **I1 (acceptance soundness).** `σ_k = AC ⇒ verified_properly(k) ∧ accepted_by_owner(k)`,
  where both are ghost variables set only by the VA and AC moves.
- **I1b (verification soundness).** `σ_k = VA ⇒ verified_properly(k)`.
- **I2 (dependency order).** A move into AU or AC for stage `k` requires
  `∀ (k, d) ∈ D: σ_d = AC`.
- **I3 (single active engineering stage).** `|{k ∈ E : σ_k ∈ A}| ≤ 1`.
- **I4 (owner exclusivity).** The only moves into AU or AC, and the only moves
  out of AC, are taken by the owner with a non-empty `owner_ref`.
- **I5 (locality).** A move on stage `k` changes no `σ_j`, `j ≠ k`.
- **I6 (replay consistency).** `fold(H, NSⁿ) = σ`: replaying the history
  reproduces the recorded state.
- **I7 (evidence immutability).** For a verified stage, `sha256(file) = pinned hash`
  for every artifact, and no commit after the verified revision touches an
  owned path without a recorded amendment.

I1 to I5 are checked by the simulation. I1 to I7 are checked by the
implementation's consistency check (I6 is `STATUS_HISTORY_CONFLICT`, I7 is
`EVIDENCE_STALE` / `VERIFICATION_STALE`).

### Why I3 must be checked on every edge into A

Iteration 1 checked I3 only on authorize (NS→AU) and reopen (AC→IP). The edge
VA→IP also enters `A` from outside it. Counterexample (12 moves, found by
breadth-first search, hence of minimal length in the reduced model): accept
stage 0, take stage 1 to VA, reopen stage 0, then rework stage 1 (VA→IP), giving
two active engineering stages. The corrected rule is: for every edge
`(x, y)` with `x ∉ A`, `y ∈ A`, require `∀ j ∈ E∖{k}: σ_j ∉ A`. Edges inside
`A` (AU→IP, IP↔BL, IP↔IM) cannot increase the active count, so the rule is
complete: `|active|` can only grow on an edge from outside `A` into `A`.

## 4. Reachability (no deadlock of legitimate progress)

Liveness requirement: with honest inputs, the all-accepted vector `ACⁿ` is
reachable from `NSⁿ`. In the reduced model this is checked by search; in the
full 10-stage graph by a guided completion that follows a topological order
(50 moves = 10 stages × 5 forward edges).

## 5. Exhaustive search size

Reduced model: 4 stages (chain 0→1→2 of engineering stages plus independent
external stage 3). The environment is adversarial: from every reachable node it
tries every stage (4), every target state (7), both actors (2) and all 2⁶ = 64
combinations of guard inputs (owner reference, evidence, tests, blockers,
revision, amendment). Attempts per node = 4 × 7 × 2 × 64 = 3,584. The corrected
model reaches 490 nodes (status vector plus ghost variables), so
490 × 3,584 = 1,756,160 attempts, which matches the recorded count.

## 6. Differential equivalence

For a sequence of random moves `μ₁ … μ_m`, let `M(μ)` be the model's decision
and `P(μ)` the implementation's (`Orchestrator.propose`). The differential test
asserts `M(μ_i) = P(μ_i)` for every `i`, applying each permitted move to both.
It is run for 2 seeds × 200 moves with owner bias on owner-only edges, and
asserts at least 8 of the 11 edges are exercised. This is evidence of agreement
on the sampled paths, not a proof of equivalence.

## 7. Evidence binding

A test report `r` supports verification at revision `ρ` iff
`r.format = citerift.test-report/1 ∧ r.revision = ρ ∧ ¬r.dirty ∧ r.passed > 0 ∧
r.failed = r.errors = 0 ∧ r.exit_status = 0 ∧ ∀ suite ∈ required: passed(suite) > 0`.
A revision cited by the registry must satisfy `commit_exists(ρ) ∧ is_ancestor(ρ, HEAD)`.
Revision prefixes in a handoff must be at least 7 hex characters
(`16⁷ ≈ 2.7 × 10⁸` values), and the full 40-character SHA is stored in the
registry.

## 8. Limits of the model

The model treats guard inputs as booleans chosen by an adversary. It cannot
tell whether an `owner_ref` really contains approval (R-002), or whether a
fully consistent forged history is genuine (R-003). Those are outside any
check that reads only the repository.
