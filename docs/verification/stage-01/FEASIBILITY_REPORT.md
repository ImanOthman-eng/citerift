# Stage 01 Feasibility Report — Independent Feasibility Investigation

CITERIFT — Created and Directed by EVE TELOS · IM.
Investigation run on 2026-10-26 (UTC); data files re-derived from the
response cache and live re-verification run on 2026-10-27. Research protocol fixed beforehand in
[PROTOCOL.md](PROTOCOL.md) (commit `c26d2d9`, pushed before any Wikipedia
query). Machine-readable evidence: [EVIDENCE_MANIFEST.json](EVIDENCE_MANIFEST.json).

Labels used below: **verified** = read from the cited primary source in this
run and re-checkable; **inference** = the executor's reasoning;
**hypothesis** = not tested; **recommendation** = advice to the owner.

## 1. Summary

| Gate | Result | Key evidence |
|---|---|---|
| 01-A Retraction data accessibility | PASS | §4: pinned snapshot (git blob + SHA-256), 73,356 records; 17 of 19 purposive events have a resolving, separate Crossref notice; 4 have publisher confirmation of link and type |
| 01-B Wikipedia citation discoverability | PASS | §5: 63 confirmed citations in pinned revisions (52 en, 11 ar) for 10 purposive DOIs; two method pitfalls found and corrected |
| 01-C Positive and negative examples | PASS | §6: 3 positive cases in both languages; 5 negative controls (2 event type, extraction, absence, notice citation); 3 unresolved cases kept apart |
| 01-D Initial cross-language feasibility | PASS, narrow | §7: Arabic cites 3 of 10 purposive papers; 11 en/ar article pairs compared at pinned revisions; Arabic retraction markup does not render |
| 01-E Coverage limitations | PASS | §8: random-sample shares with intervals; 19 documented limitations |
| 01-F Reproducibility and source references | PASS | §9: manifest, scripts, live re-verification: 35 checks of 20 revisions and 9 Crossref works, 0 mismatches |
| 01-G Blockers and recommendation | PASS | §12: **RESCOPE** under the pre-registered criteria (GO's conditions are also met; the narrower-claim trigger applies) |

**Recommendation (advisory): RESCOPE**, applying the decision criteria fixed
in PROTOCOL.md §7. Every GO condition is met: every gate passes, English
positive cases are verified, and Arabic is feasible for detection and
comparison. The third RESCOPE trigger is met as well: a method limitation
forces a narrower claim than the research question ("How consistently and
how quickly do different Wikipedia language editions respond to scientific
paper retractions?"). With the citations this method finds, consistency and
speed can be shown per paper and per named article pair, not measured as
rates for a language edition: a random sample of 200 retracted DOIs found no
citation in either language (95% upper bound about 1.8% each), and Arabic
cites 3 of the 10 purposive papers against 10 in English. The protocol does
not rank the two outcomes; the executor reads RESCOPE as the more specific
rule. The owner decides. The narrower scope is in §12. Two further findings,
outside the criteria, support the same scope: (1) English-only retraction
flagging and persistence analysis already exist (RetractionBot; Shi et al.
2026), so the distinct contribution is the cross-language comparison;
(2) Wikipedia requests from this environment were limited to about 6.5 per
minute (§8.2), so the demo should run on precomputed, cached investigations.
Details in §12.

## 2. Executor, independence and scope

- The Master Plan assigned Stage 01 to "a separate, independent agent". The
  owner's directive of 2026-10-26 (message
  `cmsg_018VCB51nDHP6HXmLU4ea5yPHoNtmrTEksWGzn64yEgVJc`) instead had a Claude
  Code session in a separate project thread execute it in the registered
  `external-agent` role. That session is the same AI tool family as the
  engineering agent. Its independence is procedural (separate thread, own
  protocol, evidence that anyone can re-run), not organizational.
- No earlier Stage 01 report was available: none is in the repository, the
  project files or the project memory, and the registry records that no
  Stage 01 finding was ever delivered or accepted (R-007). Nothing here
  reuses or predicts one.
- No Stage 00 file, contract, workflow or dependency was changed. All Stage
  01 files are under `docs/verification/stage-01/`; the scripts use the
  Python standard library only.

## 3. Method

As fixed in PROTOCOL.md: Retraction Watch snapshot pinned to a GitLab commit;
Crossref REST API as the second check; Wikipedia discovery with M1
(`list=exturlusage`) and M2 (CirrusSearch `insource:`), each candidate
confirmed in the wikitext of the latest revision; a purposive set P of 10
high-profile retracted papers (selected by the AI executor, stated as such)
and a seeded random sample S of 200 retracted DOIs. Deviations, all forced by
observed API behavior and made before the sample results were seen, are in
§11.

## 4. Gate 01-A — Retraction data accessibility

### 4.1 Access and pinning (verified)

- Source: `gitlab.com/crossref/retraction-watch-data`, commit
  `a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4` ("Retraction Watch data for
  2026-10-23"), file `retraction_watch.csv`, 68,076,023 bytes
  (`file_bytes` in `data/rw_profile.json`), downloaded
  2026-10-26T18:16Z. Its git blob id `2a466638299c351ae50ae8e5736c410b96b99045`
  equals the blob id listed in the repository tree, so the file is exactly the
  committed one; SHA-256
  `2f116e9ffed718e6b2e37cd6ff652c091fd1971e1ad9c0639f0de16e7f50a655`.
- The repository is updated each working day (latest commits dated
  2026-10-21, -22, -23), so every result must name its snapshot.
- 73,356 records: Retraction 67,916; Expression of concern 3,733; Correction
  1,544; Reinstatement 163 (`data/rw_profile.json`).
- Each record gives the original paper DOI, the notice DOI, the event type
  (`RetractionNature`), the event date, PMIDs and a record id. Retrieval time
  and dataset version are recorded with every derived file.

### 4.2 Second source: Crossref REST API (verified)

For all 10 purposive papers, the original DOI and every notice DOI resolved
in Crossref (`data/purposive_lookup.json`). Two kinds of entries appear in a
work's `updated-by`:

- entries with `source: retraction-watch`: the same events as the snapshot,
  with the same record ids. **This is the same data delivered through
  another channel, not an independent confirmation.**
- entries with `source: publisher`: deposited by publishers, and
  inconsistent with the notices for 3 of the 10 purposive papers. Examples (verified): for the Lancet
  Surgisphere paper the publisher lists the actual retraction notice
  (`10.1016/s0140-6736(20)31324-6`) as an `erratum`, and a different DOI as a
  `retraction` dated the day of publication; for Séralini 2012 and Raoult
  2020 the publisher lists the paper itself as its own `retraction`, dated at
  publication, and the real notice as an `erratum`.

What is independent of Retraction Watch is what the publisher deposited:
the notice's own Crossref record (title, date) and any `update-to` link with
`source: publisher`. For the 19 events of the purposive set
(`purposive_event_independence` in the manifest):

| Independent support | Events |
|---|---|
| Publisher `update-to` link from the notice to the paper, same event type | 4 (retractions of Obokata 2014, Lesné 2006, Wolfe-Simon 2011; Lancet Surgisphere correction, deposited as `erratum`) |
| Publisher link exists but with another type (`erratum` for a retraction) | 3 (Lancet Surgisphere, Séralini 2012, Raoult 2020 retractions) |
| Only the notice's own Crossref record (resolves; title deposited by the publisher reads as the notice) | 10 |
| None (no notice DOI, or notice DOI equals the original DOI) | 2 (Raoult 2020 concern; Lesné 2022 concern) |

So 17 of 19 events have a resolving, separate notice record, but only 4 have
a publisher link that confirms both the link and the event type. The
`update-to` links with `source: retraction-watch` were not counted.

**Inference / recommendation:** Stage 02 should treat Retraction Watch as the
authoritative event source, use the notice's own Crossref record as the
cross-check, report which events have publisher confirmation, and not trust
publisher-deposited event types or dates without review.

### 4.3 Data quality (verified counts, `data/rw_profile.json`)

| Issue | Count (of 73,356 records) |
|---|---|
| Original DOI missing (`""` or "unavailable") | 5,952 |
| Original PMID missing (`""` or 0) | 5,118 |
| Notice DOI missing | 4,667 |
| **Notice DOI identical to the original DOI** | 13,700 |
| Original DOIs with several event types (of 64,343 distinct) | 2,476 |
| Notice DOIs shared by several records | 672 |

- Several events per paper are normal: Expression of concern + Retraction
  (1,663 DOIs), Correction + Retraction (672), three types (57), and
  Reinstatement with Retraction (1). The v1 contract stores one
  `retraction_status` and one `retraction_date` per paper; event history
  must live elsewhere (§13).
- One notice can retract several papers: Science's 2006 notice
  `10.1126/science.1124926` retracts both Hwang papers.
- Dates are `M/D/YYYY H:MM` with time 0:00, except record 18930 (a
  Philosophical Transactions retraction of 1756), written
  `6/24/1756 12:00:00 AM` (`dates_not_m_d_yyyy_0_00` in
  `data/rw_profile.json`); parsers must accept both forms.
- The two sources often disagree on dates (case U-02, compared at the
  coarser precision of the two): the original publication date differs for
  5 of the 10 purposive papers (Obokata 2014: Retraction Watch 2013-03-10,
  Crossref 2014-01-29; also Séralini, Raoult, Mehra NEJM, Wolfe-Simon), and
  the event date differs from the notice's Crossref date for 4 of 17
  comparable events (NEJM Mehra retraction: 2020-06-04 vs 2020-06-25). Both
  values are kept as `conflicting`; Crossref `published` may be a print or an
  online date.
- Event-type names are not self-explanatory: Retraction Watch classifies the
  2004 Lancet notice "Retraction of an interpretation" (Wakefield paper) as a
  **Correction**; the retraction is the 2010 notice (NC-01).
- Retraction Watch states that expressions of concern and corrections "are
  not as comprehensive as retractions" (README). Its coverage of retractions
  is not complete either; absence of a record is never evidence of no
  retraction.

### 4.4 Terms (verified)

The GitLab repository states no license. Crossref's statement (blog,
2025-01-29): "While Crossref metadata is freely available to reuse without a
license, if you make use of the Retraction Watch retraction metadata in a
published work, we kindly request that you provide a citation to the source."
Stage 01 commits only selected fields of inspected records, with the source
cited (`data/README.md`). **Recommendation:** cite the source in the app and
the final report; re-check the terms before redistributing a full copy.

### 4.5 Result

PASS: authoritative records with original DOI, notice DOI, event type, date,
record id, snapshot commit and hash were obtained for real papers, and the
notices were checked in Crossref. Limitations: §4.2, §4.3.

## 5. Gate 01-B — Wikipedia citation discoverability

### 5.1 Method (verified behavior)

M1 queries the external-links table (`list=exturlusage`, namespace 0), M2
queries the search index (`list=search`, `insource:"<DOI>"`, namespace 0).
Every page either method returns is fetched at its latest revision (revid,
timestamp, sha1, wikitext) and the DOI is located in the wikitext.

### 5.2 Method pitfalls found (verified)

1. **M1 misses every template citation unless the slash is encoded.** The
   citation templates render DOI links as
   `https://doi.org/10.1016%2FS0140-6736(97)11096-0`. The query
   `doi.org/10.1016/S0140-6736(97)11096-0` returned 0 pages on English
   Wikipedia; the `%2F` form returned the citing pages. The table is also
   case-sensitive (lower-case query: fewer pages).
2. **M2 cannot be batched.** An `OR` of several `insource:"…"` phrases
   returned 0 hits even for DOIs that single queries find.
3. Raw `dx.doi.org` / plain-slash `doi.org` links: 0 pages for the purposive
   set in both languages.

The first run of M1 used the plain form and was discarded (§11).

### 5.3 Identifier versus mention (verified)

Finding a DOI string in an article does not mean the article cites that
paper. Each occurrence is classified by its markup: identifier uses
(`|doi=` or the Arabic alias `|دوي=`, `{{doi}}`, a doi.org or publisher
`/doi/` link, or "DOI:" text in a bare reference) count; occurrences inside
another field do not. Observed false positives that substring matching would
have counted:

- 4 English articles (Surgisphere, Sapan Desai, Scientific misconduct, List
  of scientific misconduct incidents) cite the **retraction notice**
  `10.1056/NEJMc2021225`, whose title contains "DOI: 10.1056/NEJMoa2007621".
  Counting them as citations of the retracted paper would confuse the notice
  with the paper.
- 1 Arabic article (كليرترب) contains the Lancet Surgisphere DOI only inside
  the title field of an unrelated, malformed citation (U-01).

Missed by DOI search entirely: references that carry no DOI at all (title
only, PMID only, or a publisher URL such as the Lancet's PII-based links).
Older references may give the DOI only as "DOI:" text (§7.4).

### 5.4 Results for the purposive set (verified, `data/purposive_discovery.json`)

| | English | Arabic |
|---|---|---|
| Papers cited (of 10) | 10 | 3 (Wakefield 1998, Obokata 2014, Wolfe-Simon 2011) |
| Article–paper citation pairs | 52 (46 articles) | 11 (11 articles) |
| … with `{{Retracted}}` at the reference | 49 | 4 |
| Found by M1 / M2 | 51 / 52 | 9 / 11 |
| Found only by M2 | 1 (publisher URL) | 2 (a `{{vcite journal}}` reference; one unexplained) |
| Found only by M1 | 0 | 0 |
| Mention-only pages (not counted) | 4 | 1 |

All 154 responses the run used were HTTP 200; no search was incomplete.

### 5.5 Result

PASS: real original-paper citations are discoverable with documented API
methods and pinned to exact revisions. M2 with confirmation and
identifier classification is the more complete method; M1 needs the encoded
form. Neither is a census (§8).

## 6. Gate 01-C — Positive and negative examples

All cases are real; none is synthetic. Full provenance in the manifest.

| Case | Type | What it shows |
|---|---|---|
| POS-01 | positive | Wakefield et al., Lancet 1998, `10.1016/S0140-6736(97)11096-0` → retraction 2010-02-06 (record 4036, notice `10.1016/S0140-6736(10)60175-4`) → cited in en "MMR vaccine" and ar "لقاح الحصبة والنكاف والحصبة الألمانية" at pinned revisions, with revision-history timelines (§7.4). |
| POS-02 | positive | Obokata et al., Nature 2014, `10.1038/nature12968` → retraction 2014-07-02 (record 2081, notice `10.1038/nature13598`) → cited in en "Haruko Obokata" and ar "هاروكو أوبوكاتا". |
| POS-03 | positive | Wolfe-Simon et al., Science 2011, `10.1126/science.1197258` → expression of concern 2011-06-03, retraction 2025-07-24 (record 66335, notice `10.1126/science.adu5488`) → cited in en "Felisa Wolfe-Simon", "Arsenic" and ar "فيليسا وولف سيمون", "زرنيخ". |
| NC-01 | event type | Same Wakefield DOI: record 17269 is a **Correction** (2004-03-06) although its notice is titled "Retraction of an interpretation". A correct system reports 2004 as a correction and 2010 as the retraction. |
| NC-01b | event type | Lesné et al., Nature 2006: record 54372 (Expression of concern, 2022) gives the paper's own DOI as its notice DOI; it is not a separate notice. |
| NC-02 | extraction | Three pinned revisions in which the Wakefield DOI does not occur: en "MMR vaccine" and ar "لقاح الحصبة والنكاف والحصبة الألمانية" just before the first citing revision, and the ar article linked from en "Causes of autism". A separate plain-substring count finds 0 occurrences of the DOI suffix, PMID 9500320 and the Lancet PII in each. The en revision names Wakefield 9 times without an identifier (discussed, not cited by DOI); the ar MMR revision is a trivial negative. Extraction must report no citation there; nothing is claimed about other revisions. |
| NC-03 | absence | Watson & Crick, Nature 1953, `10.1038/171737a0`: no Retraction Watch record (as original or as notice) and no `updated-by` in Crossref. Reported as `not_found_in_checked_sources`, status `uncertain`, never "not retracted". |
| NC-04 | notice citation | The 4 English articles found for the NEJM Mehra paper in which its DOI occurs only inside a citation of the retraction notice `10.1056/NEJMc2021225` (Retraction Watch record 23530 names it as the notice). Each must be reported as `doi_present` but not cited (§5.3). Other articles may cite the notice without the original DOI. |
| U-01 | unresolved | Arabic mention of the Lancet Surgisphere DOI inside a malformed citation's title. |
| U-02 | unresolved | Date conflicts between Retraction Watch and Crossref: 5 of 10 original publication dates and 4 of 17 event dates (§4.3); both values kept as `conflicting`. |
| U-03 | unresolved | Publisher-deposited Crossref event types for the Lancet Surgisphere paper contradict the notices. |

PASS: the full chain is verified for three papers in both languages, and each
negative-control proposition (event type, extraction, absence, notice
citation) has a real, pinned example. Positive-case retraction events are
`verified_fact` from the pinned snapshot with a resolving notice; the
independence of each confirmation is stated per event (§4.2).

## 7. Gate 01-D — English and Arabic

### 7.1 Discoverability (verified)

Arabic Wikipedia cites 3 of the 10 purposive papers (11 citing articles), all
found with the same methods. The random sample found no cited DOI in
either language (§8.1), so it cannot show whether Arabic cites fewer
retracted papers than English; the 3-of-10 contrast comes from the purposive
set, which the AI executor chose and which is not representative.

### 7.2 Comparison at pinned revisions (verified, `data/followups/crosswiki_*.json`)

For the 3 papers cited in both languages, every citing article was followed
through its interlanguage link and the linked article's latest revision was
checked:

- All 11 Arabic citing articles have an English counterpart, and all 11
  English counterparts cite the same DOI.
- Of the 33 English article–paper pairs (32 articles) for these 3 papers,
  11 have no linked Arabic article, 11 have one that does not cite the DOI,
  and 11 have one that does. Over all 10 purposive papers: 52 English
  article–paper pairs (46 articles), 20 without an Arabic article, 21 whose
  Arabic article does not cite the DOI, 11 whose Arabic article does.
- Within the 11 pairs that both cite the paper: both references carry
  `{{Retracted}}` in 4; only the English one in 6; neither in 1; only the
  Arabic one in 0. No linked article failed to load.

So linked articles often do not share citations, and in 6 of the 11 pairs
that both cite the paper the retraction marking differs. These are differences between two named
revisions, not statements about either language edition as a whole.

### 7.3 Arabic-specific findings (verified)

- Arabic citations use the template `استشهاد بدورية محكمة` with Arabic
  parameter names (`عنوان`, `صحيفة`, `الأخير1`…), mixed with English names in
  the same template; the DOI parameter appears as `doi` and as the alias
  `دوي`. One article uses `{{vcite journal}}`, which M1 did not find.
- **The retraction markup does not render.** 14 Arabic articles transclude
  `{{Retracted}}` (English name), but `قالب:Retracted` does not exist on
  Arabic Wikipedia (API: `missing`), so readers see a red template link, not a
  warning. The localized template `قالب:مصدر مسحوب` exists but has 0
  transclusions in articles (`data/followups/ar_templates_info.json`,
  `ar_embeddedin_retracted.json`, `ar_embeddedin_masdar_mashub.json`). A
  wikitext-level "marked" flag therefore overstates what Arabic readers see.
- RetractionBot does not edit Arabic Wikipedia: its global account's home
  wiki is English Wikipedia (1,673 edits), it is not attached to Arabic
  Wikipedia, and it has 0 Arabic contributions
  (`data/followups/prior_art_retractionbot_*.json`).
- Titles, template names and parameter names are right-to-left Arabic text
  mixed with Latin DOIs; the probe handled them as Unicode strings without
  error. No Arabic-Indic digits appeared in the DOIs observed.

### 7.4 Timeline probe (verified revisions; first-revision dates are bisection results)

| Article | Citation first present as identifier | Retracted-family template first at the reference | Retraction (Retraction Watch) |
|---|---|---|---|
| en "MMR vaccine" (2,253 revisions) | rev 153717252, 2007-08-26 (as "DOI:" text; template `doi=` later) | rev 483915164, 2012-03-25, `{{Retracted paper}}` (778 days after the retraction); the revision before already says the Lancet "fully retracted the original paper" in article prose | 2010-02-06 |
| ar "لقاح الحصبة والنكاف والحصبة الألمانية" (93 revisions) | rev 18121799, 2016-01-27 | same revision (2,181 days after the retraction), but the template does not render on Arabic Wikipedia (§7.3) | 2010-02-06 |

Bisection assumes that a citation or marker, once added, stays; 4 later
revisions were spot-checked per search with no violation. In English the
paper was cited before the retraction; a retraction template
(`{{Retracted paper}}`; the marker check matches the `{{Retracted…` family)
reached the reference 778 days after it, but the preceding revision
483589591 already said in article prose "''[[The Lancet]]'' fully retracted
the original paper", followed by a citation of the retraction notice
(`{{Retracted`: 0 occurrences; quoted context with offsets in
`data/followups/en_mmr_retraction_text_check.json`).
When that sentence first appeared was not measured, so 778 days is the delay
of the reference marker, not of the first warning to readers. In Arabic the
citation arrived after the retraction already carrying the marker
(hypothesis, not tested: translated from the English article, which had the
marker since 2012). An older form of
the English reference linked the paper by publisher URL with "DOI:" as plain
text; any reference without the DOI is invisible to this method, so a "first
cited" date is the first DOI-bearing revision, not necessarily the first
citation. No reason for any edit is inferred.

### 7.5 Result

PASS for feasibility of English–Arabic comparison at the level of named
articles and revisions. Not shown: that Arabic has enough cited retracted
papers for rates or survival statistics; the sample found no citation in
either language and cannot settle it (§8.1).

## 8. Gate 01-E — Coverage limitations

### 8.1 Random sample S (verified, `data/sample_S_discovery.json`)

Population: Retraction Watch "Retraction" records with an original DOI,
de-duplicated by DOI: 61,868 DOIs (snapshot 2026-10-23). 200 drawn with seed
20261026. Method: M2 with confirmation and identifier classification, latest
revisions, retrieved 2026-10-26.

| | English | Arabic |
|---|---|---|
| DOIs searched (M2) | 200 | 200 |
| Searches complete | 200 | 200 |
| Search hits of any kind | 0 | 0 |
| DOIs with a confirmed citation | 0 | 0 |
| Share, 95% Clopper–Pearson interval | 0 (0 to 0.0183) | 0 (0 to 0.0183) |

The cross-language follow-up of S (PROTOCOL.md §4) had no citing article to
follow (`data/followups/crosswiki_S_*.json`, 0 rows).

**Inference:** at most about 1.8% of DOIs in this population are cited with
their DOI in a current article version on either wiki (95% upper bound, for
this method and date). In this frame and by this method, DOI-cited retracted
papers are rare (at most about 1.8%), so random sampling is a poor way to find cases: a census of the
61,868 DOIs with single-DOI search at the measured rate (§8.2) would take
about 6.6 days per wiki. Stage 03 should use a bulk source (database dumps
of external links or wikitext) for discovery and keep the live API for
pinning and confirmation.

These figures describe this population, method and date only. They are not
the prevalence of retracted citations in Wikipedia.

### 8.2 API limits (verified, `data/rate-limit/`)

Requests from this environment to Wikipedia received HTTP 429 after runs of 1
to 6 successful requests (the very first request was already refused): 28 of 40 requests succeeded in 258 s, about 6.5 successful
requests per minute. Of the 12 responses with 429, 5 carried
`x-envoy-ratelimited` and `Retry-After` of 16–51 s, and 7 carried
`Retry-After: 1` without that header. Whether the limit is applied by
Wikimedia or by this environment's egress proxy was not determined; a
deployment elsewhere may see different limits. The probe
honors `Retry-After`, retries at most 6 times and records failures as
`unavailable`. Throughput, not correctness, is the constraint: the 200-DOI
sample took about 65 minutes (first response cached 18:44 UTC per the local
cache, run finished 19:49 UTC; 400 searches, 496 attempts including 96
retries, `data/run-logs/sample_S_discovery_first_run_log.json`), while other
probe runs shared the egress.

### 8.3 Limitations

1. M1 and M2 see only the latest revision state of their indexes; history
   needs revision-by-revision fetching.
2. DOI search misses references without a DOI (title-only, PMID-only,
   publisher URLs with PIIs).
3. M1 depends on the exact rendered URL form (encoding, case).
4. M2 depends on the search index, which can lag edits; it cannot be batched.
5. Identifier classification is rule-based (§5.3); unusual markup can be
   misclassified (one Arabic M1 miss is unexplained).
6. Reference reuse (`<ref name=…/>`) and transclusion: a citation counted once
   per article, not per use; templates transcluded from other pages were not
   expanded.
7. Nonstandard templates (`vcite journal`, `doi-inline`) and mixed-language
   parameters exist.
8. Retraction Watch is incomplete, especially for corrections and concerns;
   absence is `not_found_in_checked_sources`.
9. Several events per paper and shared notices (§4.3).
10. Date conflicts between sources (§4.3).
11. Publisher-deposited Crossref event types are unreliable (§4.2).
12. Rate limits on Wikipedia requests from this environment (§8.2).
13. Arabic counts are small; no Arabic rate can be estimated precisely.
14. Purposive set P is chosen for visibility and is not representative.
15. Interlanguage links connect articles, not claims; an absent citation in a
    linked article is not a missing correction.
16. Wikitext markers (`{{Retracted}}`) can differ from what readers see
    (§7.3), and warnings written in article prose are not detected (§7.4).
17. All Wikipedia observations are of revisions current on 2026-10-26 and will
    change.
18. A citation of a retraction notice written as bare text (no template,
    DOI in prose) could still be classified as a citation of the paper; only
    template and URL forms were observed and tested.
19. The executor's same-model review (§10) and the purposive choice of cases
    are not independent checks.

## 9. Gate 01-F — Reproducibility and source references

- `EVIDENCE_MANIFEST.json`: every case with original DOI, events, notice
  check, Crossref record, Wikipedia language, title, revid, sha1, timestamp,
  retrieval time, method, epistemic status and limitation; plus the
  aggregates quoted here. Built by `scripts/build_manifest.py` from the data
  files only.
- `scripts/stage01_probe.py`: all retrieval and classification (standard
  library, cached responses). `stage01_probe.py verify` re-fetches, without
  the cache, every pinned revision in the manifest (cases, timelines and
  sample observations), every notice DOI (including NC-04's) and the NC-03
  Crossref record, and compares sha1, DOI presence, identifier use, Crossref
  status and `updated-by`. Result of the run before handoff
  (`data/verify_result.json`, 2026-10-27T11:37Z): 35 checks of 20 distinct
  revisions and 9 distinct Crossref works, **0 mismatches**, for the
  manifest with SHA-256 `222753c10b2cc243c4c1182dbf8178bc836ee6eeaf1673c3157096dcacf7a741`.
- `scripts/reproduce.sh` re-derives every data file from the response cache
  in order; all committed data files were produced by it with the committed
  scripts (§11 item 9).
- Wikipedia text is limited to one reference per observation (CC BY-SA 4.0,
  attributed in `data/README.md`). The Retraction Watch CSV is not
  committed; its commit, blob id and SHA-256 are.
- Exact commands: §14.

PASS.

## 10. AI use and review

- The executor is an AI coding agent. It chose the purposive papers from its
  own background knowledge (a prioritization; each was then checked in the
  sources). It wrote the protocol, scripts and documents.
- A research subagent of the same model did the prior-art and deadline desk
  research (CREATIVE_FEASIBILITY.md); its key claims about published papers
  were re-checked in Crossref by the executor.
- An adversarial review by a same-model subagent tried to falsify the main
  conclusions and the code. It raised 18 findings; each finding and what was
  done about it is in [ADVERSARIAL_REVIEW.md](ADVERSARIAL_REVIEW.md). The
  ones that changed results: the marker check missed `{{Retracted}}` placed
  after the citation template (English marked pairs 47 → 49; cross-wiki
  marker split corrected), the Crossref back-link was not independent of
  Retraction Watch (§4.2 rewritten), the 778-day figure measured the
  template, not the first warning (§7.4), NC-03 used a notice DOI (replaced;
  the notice case became NC-04), and the first recommendation did not apply
  the pre-registered criteria explicitly (§12). It is not an independent
  review.
- A second same-model subagent then checked every number and
  cross-reference against the regenerated data (QA pass, also in
  ADVERSARIAL_REVIEW.md). Its 11 issues were fixed before the evidence
  commit; the main one: the third RESCOPE trigger of the protocol applies,
  so the recommendation is RESCOPE (§12).
- No AI output is the source of any retraction fact or citation observation.
  AI functions worth testing in Stage 06: classifying citation context
  (supports a claim / historical mention / discusses the retraction), with
  abstention; flagging identifier-versus-mention cases that the rules leave
  unclear; cross-language comparison of the claim a citation supports. None
  was tested here.

## 11. Deviations from the protocol

1. **M1 query form (before any sample result):** the protocol's
   `doi.org/<DOI>` form returns nothing for template citations (§5.2). M1 now
   queries the `%2F` form (as given and lower-case) plus the plain
   `doi.org` and `dx.doi.org` forms. The first purposive run was discarded.
2. **Sample S uses M2 only (before any sample result):** M1 needs 3–4 queries
   per DOI per wiki, which at about 6.5 requests per minute would have added
   about 3–4 hours for S (about 5 hours with M2); on the purposive set M1 found no citation that M2
   missed (§5.4). M1 was kept for the purposive set.
3. **Identifier classification added (after the purposive run, before the
   sample results):** substring confirmation counted citations of a
   retraction notice as citations of the paper (§5.3). The protocol's
   "contains the DOI" test is kept as `doi_present`; "confirmed" now also
   requires an identifier use.
4. **Arabic `{{Retracted}}` rendering check** added after observing the
   English template name in Arabic wikitext (§7.3).
5. **Classifier corrections after the adversarial review (before any sample
   result was read):** DOI boundary, reference span, citation fields
   containing `{{!}}` or wikilinks, "DOI:" text references, the Arabic `دوي`
   alias, and markers placed after the citation template. The sample job had
   started with the earlier code; its responses were cached and its output
   was re-derived with the final code (item 9).
6. **Timeline probe extended:** besides the first citing revision, the first
   revision with `{{Retracted}}` at the reference was also bisected, and a
   substring check was added for retraction wording in the prose (§7.4). Both
   timelines concern the same paper in two languages (the protocol allows at
   most 2 cases).
7. **Controls:** NC-03 first used the NEJM retraction notice DOI, which is a
   notice, not a paper; it was replaced by a well-known unretracted paper
   (Watson & Crick 1953) and the notice case became NC-04, a control the
   protocol did not list. NC-02 gained an independent substring check
   (`absence-check`).
8. **Tooling names:** the protocol's `scripts/verify_manifest.py` is the
   `verify` command of `scripts/stage01_probe.py`; the commands
   `absence-check` and `api-query` (read-only `action=query`) and
   `scripts/reproduce.sh` were added. The protocol points to "§9" for
   deviations; they are recorded here, in §11.
9. **Re-derivation:** the scripts changed after data collection (items 3, 5,
   7). Every data file was therefore re-derived from the response cache with
   the final scripts by `scripts/reproduce.sh`, so the committed code produces
   the committed data. Cached responses keep their original retrieval
   times.

## 12. Gate 01-G — Blockers and recommendation

**Critical blockers: none.** Data, APIs and both languages work.

Against the decision criteria fixed in PROTOCOL.md §7 before data
collection:

- **GO conditions, all met:** 01-A to 01-F pass; verified English positive
  cases exist (§6); Arabic is feasible for detection (11 confirmed Arabic
  citations) and for comparison (11 linked pairs compared at pinned
  revisions, §7.2); no data-terms blocker (§4.4).
- **RESCOPE triggers:** Arabic is feasible (first trigger not met); no data
  term restricts the planned use (second not met); but **a method limitation
  forces a narrower claim than the research question** (third met). The
  question asks how consistently and how quickly language editions respond.
  The methods tested find DOI-bearing citations only, and such citations are
  rare: 0 of 200 random retracted DOIs in either language (§8.1), 3 of 10
  purposive papers in Arabic (§7.1). Consistency and speed can therefore be
  shown per paper and per pinned article pair (§7.2, §7.4), not estimated
  as rates for an edition.
- **STOP triggers:** not met; every gate has real evidence.

The protocol does not say which outcome wins when GO's conditions and a
RESCOPE trigger hold together. The executor reads RESCOPE as the more
specific rule, because it was written for exactly this case: the core chain
works but the claim must be narrower. A reader who weighs the GO conjunction
first would reach GO; the scope below would then stand as advice.

| Area | Finding | Impact |
|---|---|---|
| Data access | Open, pinned, citable (§4) | none |
| Real examples | Full chain in both languages (§6) | none |
| Language | Arabic cites 3 of 10 purposive papers (English 10); the random sample found none in either language; Arabic markup does not render (§7, §8.1) | Arabic results are case studies |
| Science | No prevalence claims possible from these samples; markers in wikitext ≠ reader view; several events per paper | narrower claims; event history needed |
| APIs | ~6.5 requests/min (§8.2) | precomputed, cached demo; bounded live queries |
| Dependencies | Standard library sufficed; Stage 03 may use dumps for bulk work | none now |
| Prior art | English detection and persistence already covered (RetractionBot; Shi et al. 2026) | CITERIFT must lead with cross-language evidence |
| Deadline | 2026-11-21 23:59 EST (Devpost rules, verified); 8 stages left | scope must stay small |

**Recommendation: RESCOPE** (advisory; the owner decides). Narrower scope:

1. Core claim: a source-backed, revision-pinned **comparison of how English
   and Arabic Wikipedia cite and mark the same retracted papers**, with
   Evidence Passports, not a global rate.
2. English is the detection baseline; Arabic is analyzed for every paper
   found cited in English (and vice versa), and reported as named cases with
   counts, numerator and denominator.
3. Event history per paper (correction, concern, retraction, reinstatement)
   instead of a single status, and "marked in wikitext" kept distinct from
   "visible to readers".
4. A demo over precomputed, cached investigations, with retrieval times
   shown; live queries bounded.
5. No claim of novelty for English-only detection or persistence analysis.

Points 1, 2 and 3 follow from the method limitation above. Points 4 and 5
rest on findings outside the pre-registered criteria (rate limits from this
environment, §8.2; prior art, CREATIVE_FEASIBILITY.md §1) and are the
executor's additional judgment.

## 13. Impact on later stages (recommendations)

- **Stage 02:** event list per paper; notice-versus-original DOI handling,
  including 13,700 records where they are equal; snapshot pinning;
  publisher-deposited types not trusted.
- **Stage 03:** identifier-versus-mention classification (§5.3); encoded-URL
  M1; Arabic aliases (`دوي`) and mixed parameters; consider dumps for bulk
  extraction to avoid rate limits.
- **Stage 04:** v1 contract holds one `retraction_status`; store events in a
  Stage-04-owned schema that references v1 (docs/data-contracts.md), not by
  editing v1. Investigation MAESTRO requirements: MAESTRO_DESIGN_BRIEF.md.
- **Stage 06:** test the AI roles in §10, with abstention.
- **Stage 07:** cross-wiki comparison and timelines (§7.2, §7.4) as specified.
- **Stage 08:** distinguish "marked in wikitext" from "visible warning".

## 14. Reproduction

All data files, the manifest and the live re-verification are produced, in
order, by [`scripts/reproduce.sh`](scripts/reproduce.sh)
(`scripts/reproduce.sh <retraction_watch.csv> <cache-dir>`, run from the
repository root). Equivalent commands:

```bash
# 1. Retraction Watch snapshot (not committed)
curl -o rw.csv https://gitlab.com/crossref/retraction-watch-data/-/raw/a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4/retraction_watch.csv
sha256sum rw.csv   # 2f116e9f...0a655

# 2. Probe (cache directory outside the repository)
S=docs/verification/stage-01/scripts/stage01_probe.py; D=docs/verification/stage-01/data; C=/tmp/citerift-cache
python3 -I $S --cache $C rw-profile --csv rw.csv --out $D/rw_profile.json
python3 -I $S --cache $C sample --csv rw.csv --out $D/sample_S.json
python3 -I $S --cache $C lookup --csv rw.csv --dois $(python3 -c "import json;print(' '.join(json.load(open('$D/purposive_dois.json'))))") 10.1056/NEJMc2021225 --out $D/purposive_lookup.json
python3 -I $S --cache $C lookup --csv rw.csv --dois 10.1038/171737a0 --out $D/followups/nc3_lookup.json
python3 -I $S --cache $C discover --dois-file $D/purposive_dois.json --methods m1,m2 --out $D/purposive_discovery.json
python3 -I $S --cache $C discover --dois-file $D/sample_S.json --methods m2 --out $D/sample_S_discovery.json
python3 -I $S --cache $C crosswiki --discovery $D/purposive_discovery.json --src en --dst ar --out $D/followups/crosswiki_en_to_ar.json
python3 -I $S --cache $C crosswiki --discovery $D/purposive_discovery.json --src ar --dst en --out $D/followups/crosswiki_ar_to_en.json
#   (and the same two for $D/sample_S_discovery.json into crosswiki_S_*.json)
python3 -I $S --cache $C first-revision --wiki en --title "MMR vaccine" --doi "10.1016/S0140-6736(97)11096-0" --what cited --out $D/followups/timeline_en_mmr_cited.json
#   (and --what marked; and --wiki ar --title "لقاح الحصبة والنكاف والحصبة الألمانية")
#   absence-check and api-query follow-ups: see scripts/reproduce.sh

# 3. Manifest and re-verification
python3 -I docs/verification/stage-01/scripts/build_manifest.py --out docs/verification/stage-01/EVIDENCE_MANIFEST.json
python3 -I $S --cache $C/verify-refresh --refresh verify --manifest docs/verification/stage-01/EVIDENCE_MANIFEST.json --out $D/verify_result.json
```

A rerun on a later date sees newer revisions and a newer snapshot; the
`verify` command checks the pinned revisions, which do not change.
