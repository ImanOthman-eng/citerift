# Stage 04 final corrective cycle: role-collision recall study (owner decision D-083, item 5)

**Result: D-072 stays strict.** bib-1 never resolves an identifier role collision, and the recall cost of D-071 and
D-072 stays a stated limitation. Neither of the two conditions the owner set for a resolution can be proven:

- that bib-1 agreement *genuinely discriminates* the publication object;
- that it *cannot convert an ambiguous object into a positive*.

The reasons follow. Development evidence only: no campaign label, adjudication or score was read (reviewer finding
F-08 of the corrective cycle).

Tool: `role-collision/role_collision_study.py`. Output: `role-collision/ROLE_COLLISION_STUDY.json`, whose provenance
names a clean commit, checked by `tests/stage04/test_final_provenance.py`.

## 1. What a resolution would have to do

A role collision (SPEC 7.3a, D-10, `IDENTIFIER_ROLE_COLLISION`) means the checked sources give one identifier two
roles: the original work's identifier and a notice's identifier. The P2 campaign abstained on 13 such units. The
owner's D-083 instruction (item 5, message `cmsg_018VCB51nDHP6HXmLU4ea5yPYP4QxCiKQ1Hzx2XLj9zxep`) states that all 13
were genuine work citations. That statement comes from the scored P2 campaign. It is quoted here only as the reason
for the study; no argument or count below uses it (reviewer findings F-08 and C-04). A resolution would turn some of
these abstentions into positives when "independently verified bibliographic agreement" shows that the citation names
the original work.

The owner's four conditions:

1. it must not restore the JASIST false attachment;
2. it must not weaken notice/original separation;
3. it must not convert ambiguous publication objects to positives;
4. it may improve recall only where independent publication-object evidence genuinely discriminates.

## 2. Same-record collisions: bib-1 cannot discriminate, by construction

On the pinned snapshot (`snapshot` in the study output; equal to the corrective census `CENSUS.json`, which is
itself unchanged under dt-3), 13,681 DOIs and 1,053 PMIDs are same-record collisions. One Retraction Watch record
gives the key as both its original and its notice identifier, as for JASIST `10.1002/asi.23238`. These are 99.7 % of
the 13,724 DOI keys and 97.6 % of the 1,079 PMID keys in both roles.

The lookup of such a key can hold several events: 13,681 DOI keys cover 13,700 records and 1,053 PMID keys cover
1,341 (`regression/census/CENSUS.json`), and 4 of the 18 development candidates of section 4 have 2 to 4 events. But
every event describes a retracted work through its record's title, authors, journal and year (spec 2.3), and
Retraction Watch never records the notice's own bibliographic fields. So the lookup holds only descriptions of works,
never of the notice, and the same fields stand for both roles (reviewer finding C-05). bib-1's verdict is a function
of the citation and those records. It is therefore the same whether the citation means the work or the notice that
carries the same identifier. A citation of the notice that reproduces the work's title and authors is COMPATIBLE
exactly when a citation of the work is. No verdict of bib-1 can satisfy condition 4 here.

A rule that resolved these collisions on COMPATIBLE would decide them from a cue that does not depend on the role,
which breaks condition 3. JASIST shows how thin that cue is. The JASIST unit is a same-record collision, and under
such a rule its abstention would rest on its "Withdrawal:" title word alone (bib-1 MATERIAL_CONFLICT). A JASIST-like
notice citation without that word would become positive. JASIST itself would still abstain, so condition 1 holds for
the observed unit, but only by that one word.

## 3. Cross-record collisions: the records can differ, on a small population, and a resolution is not safe

Here the key is the original identifier of some records and the notice identifier of others: 56 DOIs and 27 PMIDs,
13 DOIs and 1 PMID of which are also same-record. The study compares each original-role record with each
notice-role record of the same key, the original-role record standing for a citation that reproduces it exactly.
A MATERIAL_CONFLICT means only that the two records describe different works. The notice-role record describes its own
retracted work, not the notice (reviewer finding C-05):

| Scheme | Keys | Every pair MATERIAL_CONFLICT (the records describe different works) | Some pair COMPATIBLE or INSUFFICIENT |
|---|---|---|---|
| DOI | 56 | 42 | 14 |
| PMID | 27 | 18 | 9 |

So the records of the two roles describe different works for at most 60 keys of the 14,803 role-colliding keys of
the snapshot (fewer where a key is also a same-record collision), and even there no record describes the notice
itself. Even there, a resolution would use bib-1 as **positive** evidence: agreement would create a positive. The specification
forbids that (spec 1: bib-1 can only block a positive, never create, restore or move one). That property is tested
on the whole dt-3 decision domain (`oracle-dt3`: with `bc` False, dt-3 equals dt-2 case for case). bib-1's
agreement is weak positive evidence. Over 20,000 random record pairs, one cited surname agrees by accident in 3.3 %
of pairs (`lows/author_coincidence.json`). Titles of different objects share a word in most Latin pairs (reviewer
finding A-02: OVERLAP in about 71 %). A resolution rule would need a calibrated agreement threshold. D-083 forbids
fuzzy thresholds without an independent specification and adversarial evidence, and 60 keys cannot supply that
evidence.

## 4. The role-collision abstentions of the development data

The candidates of the role-collision rule (dt-2 D-10 with `IDENTIFIER_ROLE_COLLISION`) in the three regression
sets, with the collision kind of their keys and the bib-1 object verdicts the regression recorded for their deciding
lookup:

| Set | Role-collision candidates | Collision kind of the key | bib-1 object verdicts of the candidate | dt-3 decision |
|---|---|---|---|---|
| 232 development revisions | 1 | same-record: 1 | COMPATIBLE: 1 | D-10 `UNRESOLVED_IDENTITY`: 1 |
| 80 evaluation-1 articles | 4 | same-record: 4 | COMPATIBLE: 3; MATERIAL_CONFLICT: 1 (JASIST, `en-39868218`) | D-10 `UNRESOLVED_IDENTITY`: 4 |
| 100 evaluation-2 articles | 13 | same-record: 13 | COMPATIBLE: 13 | D-10 `UNRESOLVED_IDENTITY`: 13 |

Source: `development` in `role-collision/ROLE_COLLISION_STUDY.json`, read from the three committed regression files
(`regression/*_REGRESSION.json`; their code commit is in the study output). Every one of the 18 candidates is a same-record collision,
the case of section 2 in which bib-1 cannot discriminate. 17 are COMPATIBLE. A resolution on COMPATIBLE would make
all 17 positive,
and it would do the same for a notice citation that reproduces the record's fields. The one MATERIAL_CONFLICT is
JASIST; it abstains under D-10 before D-13a is reached, so its outcome does not depend on bib-1.

These counts are in-sample development evidence, read without any label, and are not a recall estimate. Under D-072
the 18 candidates abstain, as under dt-2: dt-3 changes none of them.

## 5. Conclusion and limitation

D-072 stays strict, and bib-1 never resolves a role collision (SPECIFICATION 7.3b; spec 6). The four conditions are
kept:

- JASIST stays abstaining;
- notice/original separation is unchanged;
- no ambiguous object becomes positive;
- no recall is claimed.

The recall cost stays a stated limitation, never a performance result:

- every same-record and cross-record collision of a cited key abstains unless another cited key resolves it
  (D-072);
- 1,472 of 31,506 dt-1 positive DOI+PMID pairs of the snapshot stay `UNRESOLVED_IDENTITY`. The pair census, rerun
  on dt-3, is unchanged (`regression/census/PAIR_CENSUS.json`).

A future resolution would need record-level evidence of the notice's own object, which the checked sources do not
contain. Examples are the notice's own title or article type. That would be Stage 02 maintenance and needs a separate
owner decision (D-083 item 2).
