# Stage 04 final corrective cycle: performance and storage bounds (engine 0.4.0, table dt-3)

Owner decision D-083, items 6 (C-07), 8 (performance) and 13 (freeze-3 evidence). Every number below comes from a
committed result file whose provenance names a clean commit (`tests/stage04/test_final_provenance.py` checks it).

## 1. Run time (D-061 target: at most 5 s p95)

**NOT_MET**, unchanged since owner decision D-066. D-064 is not weakened: every process still runs
`verify_index_identity` (about 18 s) before it trusts the Stage 02 index, and that check dominates a run. The dt-3
change adds the bib-1 comparison per candidate (section 3), which is small next to it. The run times of the freeze-3
vertical slice are in `../freeze-3/FREEZE_REPORT.md` and `../freeze-3/VALIDATION.json`. No claim of meeting the
target is made.

## 2. Storage bounds (D-055 re-proved for dt-3)

Source: `bounds/bounds.json`, written by `bounds/dt3_bounds.py` (code commit `14fe609`). The historical dt-2
derivation (`../review/step7/d055/`) is unchanged.

| Quantity | dt-2 (D-055) | dt-3 | Limit |
|---|---|---|---|
| Largest record | not compared | 50,297 B (`investigation_created`) | 1 MiB |
| Largest evidence item `E_max` | not compared | 50,412 B (`cited_bibliography`) | |
| Maximal journal at the Stage 03 caps | 8,640,021 B (headroom 62.1x) | 434,316,192 B (headroom 1.2x) | 512 MiB |
| Typical journal | not compared | 1,345,917 B (headroom 398.9x) | 512 MiB |
| Events per deciding lookup `E_L` | (4 witness events) | at most 25,753 | refused above 32,030 |
| Worst LOOKUP observation (v3) | (v2: D-048 bound) | 224,207,881 B | 256 MiB blob |

**Changed claim.** The D-055 test asserted "at least 20x headroom" for the maximal journal. Under dt-3 that is no
longer true. dt-3 commits two evidence items (`lookup_event`, `lookup_record`) for every event of a claim's deciding
lookup, where dt-2 committed at most four witness events. At the theoretical maximum of 25,753 events per lookup
(the 16 MiB lookup budget over the fewest charged bytes per event, 651.5), the maximal journal is 434 MB, within the
512 MiB limit with 1.2x headroom. A run whose lookups would push the journal past the limit (more than 32,030 events
per deciding lookup at the caps) is refused at the append with `JOURNAL_TOO_LARGE`. It fails closed and never
writes a partial journal. The test (`tests/stage04/test_d055.py::test_format_4_bounds_are_recomputed_and_proven`)
now asserts the bound and `E_L_at_journal_limit >= E_L` instead of the 20x factor.

**Scale on real data.** On the pinned snapshot the largest key has 281 events (PMID 35073579), about 1/90 of
`E_L`. At the theoretical maximum the evidence content would be about 1.1 TB of part files (3.6 billion items).
That is a disk bound, not a journal bound, and no real input comes near it.

**LOOKUP observation v3.** Each event's title and journal now also appear in `records`. The observation bytes per
charged byte (rho) were measured, with no analytic bound claimed. The maximum is 13.07, for notice-only Title+Journal
lookups. An earlier analytic claim of rho = 9 was refuted by this measurement and removed. At the schema-maximum
budget the worst observation is 224,207,881 B, within the 256 MiB blob limit (margin 1.2x). An observation above the
blob limit is `BLOB_TOO_LARGE`, a `STORAGE_ERROR` (fail closed).

**Candidate inputs (E-09).** Schema 2.0.0 adds `bibliography` to each unit. Its increment is bounded by the source
size: a cleaned value is never longer than its source, and nested templates are left out. The Step 8 terms (units,
candidates, observation keys, queries) still have no derived bound. That gap has existed since Step 8 and is stated
here: an overflow is `BLOB_TOO_LARGE` (fail closed).

## 3. Decision cost of dt-3 (reviewer findings C-07 and E-10)

Source: `lows/c07_profile.json`, written by `scripts/c07_profile.py` (code commit `ce5c86b`, engine identical to
HEAD). Each figure is the median of 5 runs of `dt1.decide`.

| Events per lookup (synthetic PAIR, 3 lookups, full bib-1 records) | decide |
|---|---|
| 10 | 0.001 s |
| 100 | 0.013 s |
| 300 | 0.054 s |
| 1,000 | 0.346 s |
| 3,000 | 2.484 s |

On the snapshot's largest keys (top 5 DOIs and PMIDs by event count, decided on the production LOOKUP observation
with a cited object), the slowest decision takes 0.026 s, at 145 events. The largest key (281 events) takes 0.00003 s
because it is decided at D-9, before any scan.

**Disposition: measure and retain (LOW, accepted residual).** The role scan grows quadratically in a lookup's
events. bib-1 is linear and runs twice per candidate (once for the guard, once for the evidence). On real data the
cost is below 0.03 s per candidate. Removing the quadratic term would mean restructuring the role-collision scan
that D-071/D-072 made normative, without differential evidence that the result is the same. D-083 item 6 allows
retaining the term when "the real maximum remains harmless", so it is retained.

## 4. How often bib-1's author rule agrees by accident (reviewer finding A-02)

Source: `lows/author_coincidence.json` (`scripts/author_coincidence.py`, code commit `14fe609`). Over 20,000 seeded
random pairs of Stage 02 records with different author strings, record a's names were cited against record b:

| Rule | Pairs whose authors AGREE by accident |
|---|---|
| First draft (any name word, given names included) | 2,151 (10.8%) |
| Amended rule (every comparable cited value names a record surname) | 157 (0.8%) |
| Amended rule, a single cited name (one commenter) | 665 (3.3%) |

A further 1,767 records hold a designation word in their own title, and 11,741 of 73,356 records list one author.
Agreement never makes a positive: bib-1 can only block one (spec 1). The accidental-agreement rate therefore
measures how often a conflict goes unseen through the author field alone, not a false-positive rate of the engine.
The title verdict and the designation check apply independently.

## 5. Limitations

- 5 s p95: NOT_MET (D-066); D-064 unchanged.
- The maximal journal has only 1.2x headroom at the theoretical `E_L`. Above 32,030 events per deciding lookup a
  run is refused (`JOURNAL_TOO_LARGE`), never truncated.
- LOOKUP v3 has a measured rho of 13.07, with no analytic bound.
- The decision is quadratic in a lookup's events (C-07), harmless at the real maximum.
- The Step 8 candidate-inputs terms have no derived bound (E-09). Overflow fails closed.
