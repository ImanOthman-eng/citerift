# Stage 01 Feasibility Report — Independent Feasibility Investigation

CITERIFT — Created and Directed by EVE TELOS · IM.
Investigation run on 2026-10-26 (UTC); data files re-derived from the
response cache and live re-verification run on 2026-10-27. Research protocol fixed beforehand in
[PROTOCOL.md](PROTOCOL.md) (commit `c26d2d9`, pushed before any Wikipedia
query). Machine-readable evidence: [EVIDENCE_MANIFEST.json](EVIDENCE_MANIFEST.json).

**Corrective pass, 2026-10-27.** At the owner's request (directive "Stage 01
Excellence Upgrade", message `cmsg_018VCB51nDHP6HXmLU4ea5yPBWBK4PLfVSRHeA5DdXjWLz`)
the stage returned to `IN_PROGRESS` for one bounded correction cycle. It
found and fixed two defects in failure handling (one changed the recorded
Arabic sample result), corrected a prior-art figure, added a close
competitor, a clean-cache reproduction and a rendered-warning check. What
changed, with before and after values, is in §15; sections that changed say
so.

**Strengthening pass, 2026-10-27.** With the owner's approval before
acceptance (message `cmsg_018VCB51nDHP6HXmLU4ea5yPS6zrHggGn25MJPgeq5XsHC`)
the stage returned to `IN_PROGRESS` again for four additions: a census of
every Retraction Watch DOI and PMID in Arabic Wikipedia, cross-wiki
divergence counts, the Arabic warning gap, and two credibility fixes (the
Stage 01 tests now run in CI; the disputed Shi et al. median is dropped).
Results are in §16; sections whose statements the census changes say so.

Labels used below: **verified** = read from the cited primary source in this
run and re-checkable; **inference** = the executor's reasoning;
**hypothesis** = not tested; **recommendation** = advice to the owner.

## 1. Summary

| Gate | Result | Key evidence |
|---|---|---|
| 01-A Retraction data accessibility | PASS | §4: pinned snapshot (git blob + SHA-256), 73,356 records; 17 of 19 purposive events have a resolving, separate Crossref notice; 4 have publisher confirmation of link and type |
| 01-B Wikipedia citation discoverability | PASS | §5: 63 confirmed citations in pinned revisions (52 en, 11 ar) for 10 purposive DOIs; two method pitfalls found and corrected |
| 01-C Positive and negative examples | PASS | §6: 3 positive cases in both languages; 5 negative controls (2 event type, extraction, absence, notice citation); 3 unresolved cases kept apart |
| 01-D Initial cross-language feasibility | PASS | §7, §16: census of Arabic Wikipedia: 198 citations of 158 retracted papers in 157 articles; 170 of the 198 show readers no retraction warning; of 249 English article–paper pairs with an Arabic counterpart, 175 are not carried and none of the 46 English-marked citations carried to Arabic shows warning wording there |
| 01-E Coverage limitations | PASS | §8, §16.7: random-sample result with complete and unavailable searches separated, exact intervals; dump census validated against live discovery (19 of 20 identical); 21 + 8 documented limitations |
| 01-F Reproducibility and source references | PASS | §9: manifest, scripts, 101 deterministic tests run in CI (`tests/stage01/`), sha1-checked dumps, live re-verification (35 checks of 20 revisions and 9 Crossref works, 0 mismatches), clean-cache reproduction of a positive case end-to-end and a negative control's lookups, 0 mismatches |
| 01-G Blockers and recommendation | PASS | §12, §16.8: **RESCOPE** under the pre-registered criteria (GO's conditions are also met; the narrower-claim trigger still applies, now to timing only) |

**Recommendation (advisory): RESCOPE**, applying the decision criteria fixed
in PROTOCOL.md §7. Every GO condition is met: every gate passes, English
positive cases are verified, and Arabic is feasible for detection and
comparison. The third RESCOPE trigger is met as well: a method limitation
forces a narrower claim than the research question ("How consistently and
how quickly do different Wikipedia language editions respond to scientific
paper retractions?"). The first version of this paragraph said that
consistency and speed could be shown only per paper and per named article
pair, because a random sample of 200 retracted DOIs found no citation in
either language (§8.1). The census of §16 removes half of that limitation:
**consistency is now measured for the whole Arabic edition** (lower bounds
for link-bearing citations: 198 citations of 158 retracted papers, 86% of
them without a visible warning, and 175 of 249 English citations not
carried to the article's Arabic counterpart). **Speed** still cannot be measured as an edition
rate from this evidence (it needs every citation's history), so the
narrower-claim trigger still applies, to timing. The protocol does
not rank the two outcomes; the executor reads RESCOPE as the more specific
rule. The owner decides. The narrower scope is in §12. Two further findings,
outside the criteria, support the same scope: (1) for English Wikipedia, retraction
flagging, persistence analysis and a daily sentence-level list with AI
readings already exist (RetractionBot; Shi et al. 2026; Retraction Tracker
for Wikipedia), so the distinct contribution is the cross-language
comparison;
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

### 4.4 Terms: access, reuse and redistribution (verified; revised 2026-10-27)

The GitLab repository states no license. Crossref's statement (blog,
2025-01-29): "While Crossref metadata is freely available to reuse without a
license, if you make use of the Retraction Watch retraction metadata in a
published work, we kindly request that you provide a citation to the source."
Three uses are kept apart:

- **Access:** the CSV is publicly downloadable; Stage 01 downloaded it once,
  pinned it by commit, blob id and SHA-256, and keeps it outside the
  repository.
- **Metadata reuse:** Stage 01 commits only selected fields of the records it
  inspected (the 200 sample records, the purposive and control records), with
  the source cited (`data/README.md`); Crossref's statement covers this kind
  of reuse with attribution.
- **Redistribution of the full dataset:** not done, and not assumed to be
  permitted: the statement above does not expressly address republishing the
  whole file, and the repository states no license. The full CSV is never
  committed; reproduction downloads it from the source (§14).

Other parties make their own statements (for example, the Retraction Tracker
labels the data CC0, CREATIVE_FEASIBILITY.md §1); Stage 01 does not rely on
them. **Recommendation:** cite the source in the app and the final report;
ask Crossref or the Center for Scientific Integrity before redistributing a
full copy or a large derived extract.

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

All 154 responses the run used were HTTP 200, and none of the 86 search
responses (M1 and M2) carried an API error body (re-checked 2026-10-27 with
the stricter completeness test of §15); no search was incomplete.

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
  Arabic one in 0.
- Every interlanguage lookup returned a complete answer: en→ar 32 linked and
  20 with no link, ar→en 11 linked; no lookup failed and no answer was
  malformed; every linked article loaded (`link_status` and `dst_status` in
  the data files). Until 2026-10-27 the code would have counted a failed
  lookup as "no linked article"; it now keeps request failures, malformed
  answers, missing source pages and redirects apart, and the counts above
  are unchanged under the new code (§15).

So linked articles often do not share citations, and in 6 of the 11 pairs
that both cite the paper the retraction marking differs. These are differences between two named
revisions, not statements about either language edition as a whole.

### 7.3 Arabic-specific findings (verified)

- Arabic citations use the template `استشهاد بدورية محكمة` with Arabic
  parameter names (`عنوان`, `صحيفة`, `الأخير1`…), mixed with English names in
  the same template; the DOI parameter appears as `doi` and as the alias
  `دوي`. One article uses `{{vcite journal}}`, which M1 did not find.
- **The retraction markup does not render as a warning (checked in two
  rendered revisions).** 14 Arabic articles transclude `{{Retracted}}`
  (English name), but `قالب:Retracted` does not exist on Arabic Wikipedia
  (API: `missing`). The localized template `قالب:مصدر مسحوب` exists but has
  0 transclusions in articles (`data/followups/ar_templates_info.json`,
  `ar_embeddedin_retracted.json`, `ar_embeddedin_masdar_mashub.json`). In
  the first version of this report the consequence for readers was inferred;
  on 2026-10-27 it was checked in the rendered parser output
  (`action=parse`) of the pinned revisions of two Arabic articles and their
  English counterparts (`data/followups/render_check_*.json`). In Arabic
  "هاروكو أوبوكاتا" (rev 76190003) and "لقاح الحصبة والنكاف والحصبة الألمانية"
  (rev 72523566) the citing reference shows a link to the missing page
  "قالب:Retracted" and no retraction wording. In English "Haruko Obokata"
  (rev 1372543632) and "MMR vaccine" (rev 1381772671) it ends with
  "(Retracted, see doi: …, PMID …, Retraction Watch)". A wikitext-level
  "marked" flag therefore overstates what Arabic readers are shown, at least
  in these two articles. The check covers the desktop parser HTML only, not
  the mobile view, skins or gadgets, and not the other 12 articles.
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
| ar "لقاح الحصبة والنكاف والحصبة الألمانية" (93 revisions) | rev 18121799, 2016-01-27 | same revision (2,181 days after the retraction), but the marker names a template that does not exist on Arabic Wikipedia; the current revision renders it as a link to a missing page (§7.3) | 2010-02-06 |

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
articles and revisions. The first version said "not shown: that Arabic has
enough cited retracted papers for rates or survival statistics". The census
of §16 (2026-10-27) shows enough for edition-level counts: 158 retracted
papers cited in 157 Arabic articles (lower bounds), with marking, rendered
warnings and carrying measured for all of them. Survival statistics are
still not shown: they need each citation's history.

## 8. Gate 01-E — Coverage limitations

### 8.1 Random sample S (verified, `data/sample_S_discovery.json`; corrected 2026-10-27)

Population: Retraction Watch "Retraction" records with an original DOI,
de-duplicated by DOI: 61,868 DOIs (snapshot 2026-10-23). 200 drawn with seed
20261026 (simple random sample without replacement, `random.Random(seed).sample`;
PROTOCOL.md calls it systematic; 200 distinct DOIs, all starting `10.`). Method:
M2 with confirmation and identifier classification, latest revisions.

**Estimand.** The share of frame DOIs for which an M2 search of the main
namespace finds a page whose latest revision uses the DOI as an identifier.
It is a rate *discoverable by this method*, not the prevalence of citations
to retracted research: references without a DOI, DOIs the search index does
not match, and non-Retraction events are outside it (§8.3).

**Correction.** In the first run (2026-10-26) 7 Arabic searches received
HTTP 200 with the MediaWiki error `cirrussearch-too-busy-error` instead of
results; the probe recorded them as complete searches with no hits. They
were unavailable observations (`data/run-logs/sample_S_search_errors_first_run.json`).
After the fix (§15) those 7 searches, and only those, were sent again on
2026-10-27; all 7 returned a stated total of 0 hits
(`data/run-logs/sample_S_search_retry_2026-10-27.json`). The other 393
searches are the first run's cached answers. Provenance: the committed
`sample_S_discovery.json` was re-derived after the re-send, so its own
`request_log` shows all 400 searches as served from the cache; the re-send
is recorded only in the two run logs, which were extracted from the session's
response cache by one-off commands that are not committed (that cache is not
preserved, §9.1).

| | English | Arabic, first run (2026-10-26) | Arabic, after re-sending 7 (2026-10-26/27) |
|---|---|---|---|
| DOIs searched (M2) | 200 | 200 | 200 |
| Searches complete (stated total) | 200 | 193 | 200 |
| Searches unavailable | 0 | 7 | 0 |
| DOIs with a confirmed citation | 0 | 0 | 0 |
| Share, exact 95% Clopper–Pearson interval | 0 (0 to 0.0183), n = 200 | 0 (0 to 0.0189), n = 193 | 0 (0 to 0.0183), n = 200 |

For k = 0 the upper end of the exact two-sided 95% interval is
1 − 0.025^(1/n) (equivalently a one-sided 97.5% bound; a one-sided 95% bound
would be 0.0149 for n = 200 and 0.0154 for n = 193). The first-run Arabic
figure as originally reported ("200 complete, 0 to 0.0183") was wrong in
its denominator; the conclusion is unchanged. The Arabic n = 200 result
mixes search dates: 193 searches from 2026-10-26 and 7 from 2026-10-27.

The cross-language follow-up of S (PROTOCOL.md §4) had no citing article to
follow (`data/followups/crosswiki_S_*.json`, 0 rows).

**Inference:** for this frame, method and date, at most about 1.8% (Arabic
first run: 1.9%) of DOIs are discoverable as cited in either edition (upper
end of the two-sided 95% interval). The two editions are not compared with these numbers: both are 0
of 200, and the intervals say nothing about which edition cites more, nor
about the editions as wholes. Random sampling is therefore a poor way to
find cases: a census of the 61,868 DOIs with single-DOI search at the
measured rate (§8.2) would take about 6.6 days per wiki. Stage 03 should use
a bulk source (database dumps of external links or wikitext) for discovery
and keep the live API for pinning and confirmation.

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
13. Arabic counts are small; no Arabic rate can be estimated precisely from
    the sample. (Superseded for link-bearing citations by the census, §16,
    which has its own limitations, §16.7.)
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
20. MediaWiki reports some overload conditions as HTTP 200 with an error
    body (`cirrussearch-too-busy-error`, `maxlag`); a client that checks only
    the HTTP status records them as "no hits". Fixed in the probe (§15);
    later stages must test for it.
21. The Arabic sample result combines searches from two dates (§8.1), and
    the rendered-warning check covers only the revisions inspected, in the
    desktop parser output (§7.3).

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
  (`data/verify_result.json`, 2026-10-27T18:18Z): 35 checks of
  20 distinct revisions and 9 distinct Crossref works,
  **0 mismatches**, for the manifest with SHA-256
  `e2e9fd48c1698df32f02772b7d687ad249768f5d949c18585352f11aaaf06305`
  (the manifest of the strengthening pass; it adds the census counts as
  aggregates, and the census's own revisions are pinned in
  `data/census/`, not re-verified by this command).
- `scripts/reproduce.sh` re-derives every data file from the response cache
  in order; all committed data files were produced by it with the committed
  scripts (§11 item 9). In the 2026-10-27 re-derivation every data file
  produced the same content as before except for run times, the new
  per-call `ok`/`api_error` fields, the new link-lookup states (same counts)
  and the 7 corrected Arabic sample searches (§8.1).
- **Failure handling is tested deterministically** (no network):
  `tests/stage01/` holds 101 tests of link lookups, search completeness, the
  HTTP client under 429, 5xx and error bodies, the cache, the
  rendered-reference check and the census (§16.6). Since 2026-10-27 they
  run in CI with the rest of the suite (`uv run pytest`); before, they lived
  in `docs/verification/stage-01/tests/` and were run explicitly only. How
  they relate to the defects is in §15.1.
- Wikipedia text is limited to one reference per observation and short
  rendered excerpts (CC BY-SA 4.0, attributed in `data/README.md`). The
  Retraction Watch CSV is not committed; its commit, blob id and SHA-256
  are (§4.4).
- Exact commands: §14.

### 9.1 What reproduces from where

| Starting point | What can be reproduced | Needs |
|---|---|---|
| Clean checkout only | Re-verification of every pinned revision, notice and Crossref record in the manifest (`verify`); the deterministic tests; reading every committed figure | network for `verify`; nothing for the tests |
| Clean checkout + the pinned Retraction Watch CSV | `rw-profile`, `sample` and the Retraction Watch side of `lookup`; any single case end-to-end with a fresh cache (§9.2) | the CSV (download, §14) and network; Wikipedia observations of the *latest* revision may differ on a later date |
| Clean checkout + CSV + the six 2026-10-01 dumps | the dump scans, interlanguage maps and dump-versus-API cross-check of §16 exactly (offline); the live confirmation, renders and histories again, as dated observations (about 630 requests) | the dumps (sha1 checked by the script) and network |
| Clean checkout + CSV + the original response cache | byte-for-byte re-derivation of every data file by `reproduce.sh` without network (except the final `verify`) | the cache, which lived in the session scratchpad and is **not** committed or preserved; without it a full rerun sends about 700 requests at the rates of §8.2 and observes newer revisions |

Revision-pinned facts (a DOI in revision *r*, its sha1) reproduce exactly
from a clean checkout. Facts about the *latest* revision, search-index
results and the cross-wiki follow-up are dated observations and reproduce
only as long as the articles and index do not change.

### 9.2 Clean-cache reproduction (2026-10-27)

`scripts/clean_reproduction.sh` reran one positive case (POS-02, Obokata
2014, English and Arabic) and one negative control (NC-03, Watson & Crick
1953) into an empty cache: Retraction Watch and Crossref lookups for both,
and M1 + M2 discovery with confirmation for POS-02 (15 requests in all, 12
of them for discovery, none from cache). NC-03 is a lookup control, so it has
no Wikipedia step. `scripts/compare_clean.py` compared them with the
committed data (`data/clean_reproduction.json`, 2026-10-27T13:22Z): 14 checks,
**0 mismatches**; the Retraction Watch records, Crossref status, title,
`updated-by` and notices agree for both cases; English finds the same 3
citing articles and Arabic the same 1, each confirmed and marked as
committed, at the same revision ids (no article had changed since
2026-10-26).

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
- In the corrective pass of 2026-10-27 the executor found the two
  failure-handling defects of §15 itself while auditing the code against the
  owner's list; consequential counts were then re-derived by separate code
  (raw cached responses tallied independently of the probe's classifiers).
  A same-model subagent then reviewed the changes from technical,
  scientific, creative and integration angles; its 18 findings (3 medium,
  15 low) were all handled (ADVERSARIAL_REVIEW.md). Same-model reviews are not independent scientific
  verification.
- No AI output is the source of any retraction fact or citation observation.
  AI functions worth testing in Stage 06: classifying citation context
  (supports a claim / historical mention / discusses the retraction), with
  abstention; flagging identifier-versus-mention cases that the rules leave
  unclear; cross-language comparison of the claim a citation supports. None
  was tested here. The evaluation plan (deterministic baseline, held-out
  human-labelled sets per language, sample sizes, abstention, a
  pre-registered gate) is CREATIVE_FEASIBILITY.md §5. For English, an AI
  reading of whether a passage relies on a retracted paper already exists
  (Retraction Tracker), so it is not a novelty claim.

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
   English template name in Arabic wikitext (§7.3): at first a template
   existence check; on 2026-10-27 a rendered check of four revisions
   (`render-check`).
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
10. **Corrective pass, 2026-10-27 (owner-requested, after the results were
    known):** the failure handling of searches and link lookups was
    corrected (§15). Because an error body is not an answer, the 7 Arabic
    sample searches that had received one were sent again, once, on
    2026-10-27; no other search was repeated. The first-run figures are
    reported beside the corrected ones (§8.1). PROTOCOL.md is unchanged and
    remains the record of the plan.
11. **Added checks (2026-10-27):** a rendered-reference check of four
    revisions (`render-check`, §7.3), a clean-cache reproduction of POS-02 and
    NC-03 (§9.2), deterministic failure-handling tests (§9), and a prior-art
    re-check (CREATIVE_FEASIBILITY.md §1). None changes a pre-registered
    criterion.
12. **Census (2026-10-27, owner-approved, after the results were known):**
    PROTOCOL.md §5 planned a random sample and live queries; the census adds
    a third method, the Wikimedia SQL dumps of 2026-10-01 scanned offline,
    with live confirmation of every candidate (§16.1). It was added after the
    sample's result was known, at the owner's request, and is reported beside
    the sample, not instead of it. The decision criteria (PROTOCOL.md §7) are
    unchanged; how the census bears on them is in §16.8.

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
  The methods tested find DOI-bearing citations only, and few are
  discoverable this way: 0 of 200 random Retraction records' DOIs in either
  language (§8.1, a rate discoverable by M2, not a prevalence), 3 of 10
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
| Language | Census: Arabic cites 158 retracted papers in 157 articles, 170 of 198 citations without a visible warning; no Arabic wikitext marker renders as warning text (§16) | edition-level counts possible (lower bounds); timing still per paper |
| Science | Census counts are lower bounds (link-bearing citations, §16.7); markers in wikitext ≠ reader view; several events per paper | bounded claims; event history needed |
| APIs | ~6.5 requests/min (§8.2) | precomputed, cached demo; bounded live queries |
| Dependencies | Standard library sufficed; Stage 03 may use dumps for bulk work | none now |
| Prior art | English detection, persistence and sentence-level AI readings already exist (RetractionBot; Shi et al. 2026; Retraction Tracker for Wikipedia) | CITERIFT must lead with cross-language and rendered-warning evidence |
| Deadline | 2026-11-21 23:59 EST (Devpost rules, verified); 8 stages left | scope must stay small |

**Recommendation: RESCOPE** (advisory; the owner decides). Narrower scope:

1. Core claim: a source-backed, revision-pinned **comparison of how English
   and Arabic Wikipedia cite and mark the same retracted papers**, with
   Evidence Passports, not a global rate.
2. English is the detection baseline; Arabic is analyzed for every paper
   found cited in English (and vice versa), and reported as named cases with
   counts, numerator and denominator. Since the census (§16), this includes
   edition-level counts for link-bearing citations (cited, marked, carried,
   visibly warned), stated as lower bounds; timing stays per paper.
3. Event history per paper (correction, concern, retraction, reinstatement)
   instead of a single status, and "marked in wikitext" kept distinct from
   "visible to readers".
4. A demo over precomputed, cached investigations, with retrieval times
   shown; live queries bounded.
5. No claim of novelty for English-only detection, persistence analysis or
   English sentence-level AI readings; novelty statements bounded to "not
   established in the reviewed evidence" (CREATIVE_FEASIBILITY.md §1).

Points 1, 2 and 3 follow from the method limitation above. Points 4 and 5
rest on findings outside the pre-registered criteria (rate limits from this
environment, §8.2; prior art, CREATIVE_FEASIBILITY.md §1) and are the
executor's additional judgment.

## 13. Impact on later stages (recommendations)

- **Stage 02:** event list per paper; notice-versus-original DOI handling,
  including 13,700 records where they are equal; snapshot pinning;
  publisher-deposited types not trusted.
- **Stage 03:** identifier-versus-mention classification (§5.3); encoded-URL
  M1; Arabic aliases (`دوي`) and mixed parameters; the dump scan of §16
  (`scripts/stage01_census.py`) shows bulk extraction from SQL dumps works
  (Arabic in under a minute, English in under five) and agrees with live M1;
  pair it with M2 or wikitext for citations that have no external link.
- **Stage 04:** v1 contract holds one `retraction_status`; store events in a
  Stage-04-owned schema that references v1 (docs/data-contracts.md), not by
  editing v1. Investigation MAESTRO requirements: MAESTRO_DESIGN_BRIEF.md.
- **Stage 06:** test the AI roles in §10 under the plan of
  CREATIVE_FEASIBILITY.md §5, with abstention; cut the label for a language
  that fails its gate.
- **Stage 07:** cross-wiki comparison and timelines (§7.2, §7.4) as specified.
- **Stage 08:** distinguish "marked in wikitext" from "visible warning",
  using the Visible Warning Integrity states (CREATIVE_FEASIBILITY.md §2.1);
  the census gives the Arabic baseline (§16.4).
- **All data stages:** treat MediaWiki error bodies under HTTP 200 as
  failures, keep "request failed" apart from "not found", and test both with
  injected responses (§15; `tests/`).

## 14. Reproduction

All data files, the manifest and the live re-verification are produced, in
order, by [`scripts/reproduce.sh`](scripts/reproduce.sh)
(`scripts/reproduce.sh <retraction_watch.csv> <cache-dir> [<dump-dir>]`, run
from the repository root; with a dump directory it also re-derives the
census of §16). Equivalent commands:

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

# 2b. Census (§16): the six 20261001 dumps named in stage01_census.py (DUMP_SHA1), e.g.
#   curl -O https://dumps.wikimedia.org/arwiki/20261001/arwiki-20261001-externallinks.sql.gz   (and page, langlinks; same for enwiki)
#   then the census block of scripts/reproduce.sh (dump-scan, confirm, render, crosscheck, langmap, crosswiki, summarize)

# 3. Manifest and re-verification
python3 -I docs/verification/stage-01/scripts/build_manifest.py --out docs/verification/stage-01/EVIDENCE_MANIFEST.json
python3 -I $S --cache $C/verify-refresh --refresh verify --manifest docs/verification/stage-01/EVIDENCE_MANIFEST.json --out $D/verify_result.json
```

A rerun on a later date sees newer revisions and a newer snapshot; the
`verify` command checks the pinned revisions, which do not change. Without
the original response cache (not committed, §9.1) a full rerun sends about
700 requests; the census adds about 630 more and the dump downloads (about
9.2 GB); on 2026-10-27 its live part took about 2.5 hours at the rate of
§8.2.

```bash
# Deterministic tests (no network); CI runs them with the whole suite
uv run pytest tests/stage01
# Bounded clean-cache reproduction of POS-02 and NC-03 (15 requests on 2026-10-27; WORK_DIR must be empty)
docs/verification/stage-01/scripts/clean_reproduction.sh rw.csv /tmp/citerift-clean
```

## 15. Corrective pass of 2026-10-27

Requested by the owner (directive "Stage 01 Excellence Upgrade", message
`cmsg_018VCB51nDHP6HXmLU4ea5yPBWBK4PLfVSRHeA5DdXjWLz`). Stage 01 was
returned from `VERIFIED_AWAITING_OWNER_ACCEPTANCE` to `IN_PROGRESS` with the
registered `external-agent` role through `citerift-gov` (the transition the
CLI allows for "defect found or owner requests changes"), corrected, and
re-verified. PROTOCOL.md is unchanged.

### 15.1 Defects found and fixed

| # | Defect | Effect on committed results | Fix and evidence |
|---|---|---|---|
| D1 | A MediaWiki error returned as HTTP 200 (`cirrussearch-too-busy-error`) was read as a complete search with 0 hits, and the error body was cached and served again. | **Changed a result:** 7 of 200 Arabic sample searches were unavailable but recorded as complete (§8.1). | Error bodies are failures; transient codes (`cirrussearch-too-busy-error`, `maxlag`, `ratelimited`) are retried like a 429; error bodies are never cached, and cached ones are fetched again; a search is complete only when it states an integer total. 17 tests (`tests/stage01/test_discovery_errors.py`). The 7 searches were sent again once; all 7 answered 0 hits. |
| D2 | A failed or malformed interlanguage-link request was read as "no linked article". | Latent: all 13 link responses used were complete (re-checked from the raw cached responses by separate code), so the cross-wiki counts are unchanged. | Lookups are batched (50 titles), follow continuation, map normalized titles back, and return `linked`, `no_link`, `source_missing`, `request_failed` or `malformed_response`; the linked article's fetch is `fetch_failed`, `article_missing`, `malformed_response`, `redirect`, `doi_not_found`, `doi_mention_only` or `doi_cited`. 29 tests including injected 429, 500 and 503 (`tests/stage01/test_crosswiki.py`). |
| D3 | M1 did not follow API continuation. | Latent: no M1 response used had a continuation. | Continuation followed; tested. |
| D4 | Shi et al.'s median was given as 5.8 years "in the published abstract", with arXiv v3 as the outlier. | Prior-art wording. | The Crossref-deposited abstract says 5.8 years (2,106 days); arXiv v1–v3 and the CSCW 2026 program say 3.68 years (1,344 days); the published full text was not readable from here. Both are now reported with sources (`data/followups/prior_art_shi_median_sources.json`). |
| D5 | The closest named competitor was listed from a search snippet only. | Prior-art completeness. | The Retraction Tracker for Wikipedia was opened and profiled from its about page and data file (CREATIVE_FEASIBILITY.md §1); novelty statements bounded to the reviewed evidence. |
| D6 | "Readers see a red template link, not a warning" was inferred, not observed. | Wording of §7.3. | Rendered check of two Arabic and two English revisions (§7.3); the inference held for those revisions. |
| D7 | Terms did not separate access, metadata reuse and redistribution. | Wording of §4.4. | §4.4 rewritten; the full CSV is not redistributed. |
| D8 | "Every data file re-derived" did not say what a clean checkout can reproduce. | Reproducibility claim. | §9.1 matrix and the clean-cache reproduction of §9.2. |
| D9 | Found by this pass's same-model review: an HTTP 200 body that is not JSON could be cached; attempts did not record API errors; the render check matched DOI prefixes and could read "RETRACTED" in a cited title as a warning. | None on committed results (no such response was used; the four render states are unchanged after the fix). | Only JSON answers are cached; each attempt records its API error; the render check uses the DOI boundary rule and skips the `<cite>` element. 4 more tests (61 in all). |

Against the probe of the previous evidence revision `562fe1a` (run on
2026-10-27 in a scratch copy): the discovery and client tests
(`tests/stage01/test_discovery_errors.py`) fail on behaviour, because that code
counted error bodies as answers, cached them and did not retry them. Most
link-lookup tests cannot run there at all, because that code had no lookup
states; the D2 defect was shown directly instead: given a failed request,
the old `crosswiki` returned a row with no linked title, which the old
counting classed as "no linked article". The render tests cover code that
did not exist.

### 15.2 Before and after

| Figure | Before (`562fe1a`) | After |
|---|---|---|
| Arabic sample: searches complete / unavailable | 200 / 0 | first run 193 / 7; after re-sending the 7, 200 / 0 |
| Arabic sample: 95% Clopper–Pearson upper bound | 0.0183 | first run 0.0189 (n = 193); after re-sending 0.0183 (n = 200, two search dates) |
| English sample | 200 complete, 0 cited, 0.0183 | unchanged |
| Cross-wiki en→ar: no link / not citing / citing | 20 / 21 / 11 | unchanged; plus 0 failed and 0 malformed lookups |
| Cross-wiki ar→en citing | 11 of 11 | unchanged |
| Purposive discovery | 63 confirmed citations | unchanged; all 86 search responses free of error bodies |
| Live re-verification | 35 checks, 0 mismatches | 35 checks of 20 revisions and 9 Crossref works, 0 mismatches |
| Deterministic tests | none | 61 |
| Prior-art median (Shi et al.) | 5.8 years, "published abstract" | sources disagree: 5.8 years (Crossref abstract) vs 3.68 years (arXiv, CSCW program) |

### 15.3 Decisions without a change

- **User-Agent:** kept as it is (`CITERIFT-Stage01-feasibility/0.1
  (https://github.com/ImanOthman-eng/citerift; read-only research; contact
  via GitHub issues)`). The Wikimedia Foundation User-Agent Policy (revision
  564705 of 2026-03-27, read 2026-10-27) asks scripts for "an informative
  User-Agent string with contact information". The string names the project,
  version and purpose, and its contact is the public repository's issue
  tracker, which is enabled (checked 2026-10-27). It contains no legal name.
  It does contain the repository owner's login, as part of the repository
  URL; docs/identity.md lists that login for ownership records, and the URL
  is also the project's public address. That is why RV-17 left the question
  to the owner. No reason to change it was found; the owner can still decide
  otherwise.
- **Recommendation:** still RESCOPE (advisory). The corrected sample result
  does not change it; the new prior art strengthens point 5 of §12.
- **Scope:** no change to the research question or the gates; no Stage 00
  file changed; no dependency added.

### 15.4 Remaining limitations of this pass

- The rendered check covers four revisions; it does not cover the mobile
  view, skins or gadgets, or the other 12 Arabic articles with the marker.
  Its Arabic warning stem (سحب) can also match unrelated words.
- The published full text of Shi et al. was not read. (Resolved on
  2026-10-27 by dropping the disputed median, §16.6.)
- The prior-art search is not exhaustive; "not established" claims are
  bounded to the works listed in CREATIVE_FEASIBILITY.md §1.
- The reviews of this pass were done by the same model as the executor and
  are not independent verification.

## 16. Strengthening pass of 2026-10-27: census, divergence and warning gap

At the owner's approval (message `cmsg_018VCB51nDHP6HXmLU4ea5yPS6zrHggGn25MJPgeq5XsHC`,
in reply to a proposal with four items) the stage returned to `IN_PROGRESS`
once more, before acceptance, to replace the "0 of 200" sample with a full
census of Arabic Wikipedia, to measure cross-wiki divergence with real
counts, to count the Arabic warning gap, and to fix two credibility points.
All counts below are in `data/census/census_summary.json`, computed by
`scripts/stage01_census.py summarize` from the committed census files.

### 16.1 Method (verified behavior)

1. **Identifiers.** Every DOI and PMID of the pinned Retraction Watch
   snapshot (73,356 records): the original paper's and the notice's, 112,483
   distinct DOIs and 63,012 distinct PMIDs. The headline counts use records
   whose nature is *Retraction*: 67,916 records, 65,643 of them with an
   original DOI or PMID, describing **62,575 distinct papers** (one paper
   can have several records). Expressions of concern, corrections and
   reinstatements are counted separately and never called retractions.
2. **Dump scan (offline).** The `externallinks` and `page` tables of the
   Wikimedia SQL dumps of 2026-10-01 for Arabic and English Wikipedia, each
   checked against the sha1 published in the run's `dumpstatus.json`. A page
   is a candidate when one of its external links resolves to a known
   identifier: a `doi.org` link, a DOI inside another URL (ending at the end
   of the URL or before `/ ? # & ;`, so a figure DOI such as `…0012345.g001`
   is not the paper), or a PubMed / Europe PMC link with the PMID. The
   externallinks table is what M1 queries live (§5.1), so this is M1 for all
   identifiers at once, with no request to Wikipedia.
3. **Live confirmation.** The current revision of every candidate article
   was read on 2026-10-27 (50 pages per request) and each record classified
   with the rules of §5.3: cited by identifier, mentioned only, or no longer
   present; marked by a `{{Retracted}}`-family template at the citation or
   not. A failed request is recorded as unknown, never as "not cited".
4. **Rendered check.** For each Arabic article–paper pair, the parser HTML
   of the pinned revision (`action=parse`, one request per article),
   classified as in §7.3; citations outside the footnotes (a "further
   reading" list, prose) are found too and labelled as such.
5. **Divergence.** Interlanguage links from the 2026-10-01 `langlinks`
   dumps, the linked article's page id from the other wiki's `page` dump,
   then both articles' current revisions read live. "Carried" means the
   linked article cites the same paper by *any* of its Retraction Watch
   identifiers (DOI or PMID). For every paper not carried, the linked
   article's first revision and the source article's revision in force at
   that moment were read.

All requests used the throttled client of §8.2 (one request per second at
most, retries on 429/5xx and on MediaWiki error bodies under HTTP 200):
633 answered requests (470 `action=query`, 163 `action=parse`) plus 298
retries after HTTP 429. One parse (Arabic "INF2") got no answer after its
retries in the first render run and was answered when re-sent
(`data/run-logs/census_render_first_run_failure.json`); no other request
failed, and no answer was an error body. The dumps themselves were
downloaded once from dumps.wikimedia.org (about 9.2 GB). Every census
file was then re-derived from the dumps and the response cache with the
committed script into an empty directory: all nine files are identical to
the committed ones except run times (the committed summary is that
re-derived one, made after a history category was renamed).

### 16.2 Validation of the dump method (verified, `data/census/dump_vs_api_crosscheck.json`)

For the 10 purposive papers in both languages, the dump scan and the live
M1/M2 discovery of 2026-10-26 (§5.4) found **identical article sets in 19 of
20 paper–language pairs**. The exception is Arabic "بول دافيس" for
Wolfe-Simon 2011: its revision of 2026-10-13 cites the DOI in a template
parameter, but no external link exists for it (M1 also missed it live;
only the search M2 found it). So the census inherits M1's blind spot,
citations whose identifier is not rendered as an external link, and on the
purposive set that blind spot was 1 of 63 confirmed citations. Citations
added after 2026-10-01 are also missed unless they existed in the dump.

### 16.3 Arabic Wikipedia census (verified, `data/census/ar_scan.json`, `ar_confirm.json`)

| | Count |
|---|---|
| Pages linking to any Retraction Watch identifier (dump) | 205 (195 articles, 10 user pages) |
| Articles read live on 2026-10-27 | 195, 0 failures |
| **Article–paper pairs citing a retracted paper (Retraction records), confirmed at the current revision** | **198** |
| …in distinct articles | **157** |
| …of distinct retracted papers | **158** (159 records) |
| …cited by DOI / by PMID only | 191 / 7 |
| Linked in the dump but no longer cited at the current revision | 1 |
| Pairs whose citation carries a `{{Retracted}}`-family template in wikitext | 23 |
| Expression of concern (pairs / articles / papers) | 25 / 22 / 18 |
| Correction (pairs) | 38 |
| Citations of a notice only (no citation of the paper) | 17 |

So the answer to the census question is **not zero**: Arabic Wikipedia
cites at least 158 retracted papers in 157 articles, about 0.25% of the
62,575 retracted papers with an identifier. The same scan of English
Wikipedia (dump only, not confirmed live article by article) finds 445
retracted papers in 432 articles (601 pairs, about 0.71%). Both are
consistent with the sample of §8.1 finding none in 200 draws (at 0.25% the
expected number of hits is 0.5; at 0.71% the probability of 0 hits is
about 0.24). These are lower bounds for link-bearing citations, not
prevalence of all citations (§16.7).

### 16.4 Warning gap in Arabic (verified, `data/census/ar_render.json`)

What a reader of the current revision sees next to each of the 198 Arabic
citations of a retracted paper (desktop parser HTML):

| Rendered state | Pairs | Where |
|---|---|---|
| No retraction wording | **148** | 122 in footnotes, 26 in lists outside the footnotes |
| Only a red link to the missing `قالب:Retracted` | **22** | 17 footnotes, 5 outside |
| Retraction wording shown | 26 | all in one article, "فضيحة شون" (a list of Schön's retracted papers, each followed by "(Retracted)") |
| Citation not found in the rendered HTML | 2 | one article, "2020 في العلوم" |
| Render failed | 0 | one failed and succeeded when re-sent |

**170 of the 198 pairs (86%) show no retraction warning to readers**, in
**155 of the 157 articles** and for **131 of the 158 papers**. Every one of
the 23 wikitext-marked Arabic citations renders as a link to the missing
template (22) or was not found in the render (1): **wikitext marking on
Arabic Wikipedia produced no visible warning text in any case inspected.**
Arabic Wikipedia has no working retraction template in use
(`قالب:Retracted` is missing; `قالب:مصدر مسحوب` exists with 0 article uses;
§7.3) and RetractionBot does not edit it. For the 25 expression-of-concern
pairs: 19 no wording, 4 red link only, 2 not found. The single article with
visible wording is about the retractions themselves; whether any other
article explains the retraction in its prose was not checked (§16.7).

### 16.5 Cross-wiki divergence (verified, `data/census/crosswiki_*.json`)

**English → Arabic.** 432 English articles cite a retracted paper (dump);
207 of them have an Arabic article (2026-10-01 langlinks), giving 261
article–paper pairs. In 12 of them the English article no longer cites the
paper at its current revision; the other **249** pairs:

| Category | Pairs |
|---|---|
| **Not carried**: the Arabic article does not cite the paper | **175 (70%)** |
| Carried, marked in both | 12 |
| Carried, **marked in English only** | **34** |
| Carried, marked in neither | 27 |
| Carried, marked in Arabic only | 1 |

Of the 46 carried citations that English marks as retracted, the Arabic
article carries the marker in wikitext in 12, and **in none does it show
retraction wording**: the 12 render as a link to the missing template, 31
show no wording, 1 was not found in the render and 2 are not in the Arabic
census (cited without a link). In no case observed does the English
warning reach Arabic readers.

For the 175 pairs not carried (136 Arabic articles), the Arabic article's
first revision and the English revision at that moment:

| What the histories show | Pairs |
|---|---|
| English added the citation after the Arabic article was created | 90 |
| English already cited the paper when the Arabic article was created; the Arabic first revision did not | 75 |
| The English article did not exist yet | 9 |
| The Arabic first revision cited the paper; it was **removed later** | 1 |

"Not carried" therefore mostly means "never there" rather than "removed":
only 1 of 175 was present at creation and later removed. Additions and
removals between creation and today were not inspected, so a citation added
and later removed in Arabic would be counted as never carried.

**Arabic → English.** 158 Arabic articles cite a retracted paper in the
dump (157 still do live); 155 have an English article, giving 196 pairs.
One Arabic article no longer cites the paper, and the 28 pairs of
"فضيحة شون" are unknown because its English link is a redirect (§16.7);
of the other **167** pairs, **96 (57%)** are not cited by the English
article, and 71 are:

| Category | Pairs |
|---|---|
| Not cited in English | 96 |
| Cited in both, **marked in English only** | 32 |
| Cited in both, marked in neither | 26 |
| Cited in both, marked in both | 12 |
| Cited in both, marked in Arabic only | 1 |

In Arabic, again, none of these 71 shows retraction wording: 13 render as a
link to the missing template, 57 show no wording, 1 was not found in the
render. For the 96 not cited in English, the English article's first
revision cited the paper in **20 pairs (19 article pairs, 16 papers): the
English article once cited the retracted paper and no longer does, while
the Arabic article still cites it, with no visible warning** (6 of them
render the red template link). Most are gene articles whose English first
revisions date from 2007–2008; when and why the English citations were
removed was not examined, and no link to the retraction is claimed. In 75 pairs the English first revision
did not cite the paper and the Arabic article did not exist yet; in 1 the
Arabic article existed without it.

These are differences between named, pinned revisions; they describe what
readers of each edition see, not why editors acted. No editor intent is
inferred.

### 16.6 Credibility fixes

- **Stage 01 tests now run in CI.** The 61 tests moved from
  `docs/verification/stage-01/tests/` to `tests/stage01/` (git history kept),
  where the repository's existing `testpaths = ["tests"]` and the `ci-gate`
  workflow collect them with every other test. No Stage 00 file changed:
  `pyproject.toml`'s `testpaths` could not be widened, because the Stage 00
  test-report plugin fixes the complete-run collection settings to
  `testpaths = ["tests"]` (`src/citerift/governance/pytest_report.py`,
  `COLLECTION_SETTINGS`), and `.github/workflows` is Stage 00 owned. 40 new
  tests cover the census code (dump parsing, identifier matching and its near
  misses, error bodies, missing and absent pages, failed renders, the
  divergence categories and the history step); the Stage 01 total is 101.
- **Shi et al.** The arXiv v3 full text was read: it reports a median of
  3.68 years (1,344 days) in its abstract, results and conclusion and never
  5.8 years; the published version's abstract (Crossref) says 5.8 years
  (2,106 days). The published full text is open access but the publisher's
  site refused this environment (HTTP 403), and getting around that was not
  attempted. **The disputed median is dropped from CITERIFT's claims**
  (CREATIVE_FEASIBILITY.md §1; sources in
  `data/followups/prior_art_shi_median_sources.json`). The other figures
  quoted (1,181 citations; 71.6%, 51.5%, 20.1%) are the same in both texts.

### 16.7 Limitations of the census

1. Link-based: citations whose identifier is not rendered as an external
   link (plain text, some templates, a title only) are missed; on the
   purposive set this was 1 of 63 (§16.2). The counts are lower bounds.
2. The dumps are of 2026-10-01; the live confirmation is of 2026-10-27.
   Citations added in between and absent from the dump are missed.
3. Retraction Watch is the only list of retracted papers; a paper it does
   not list is not counted.
4. The rendered check reads the desktop parser HTML; mobile view, skins and
   gadgets were not checked. Retraction wording written in the article's
   prose, away from the citation, is not detected; intentional citations
   (an article about the retraction) are not separated automatically.
5. Interlanguage links connect articles, not claims; a paper not carried may
   be irrelevant to the linked article's text. The history step reads two
   revisions per pair, not the whole history.
6. One linked English title is a redirect ("Jan Hendrik Schön", from
   "فضيحة شون"); its 28 pairs are kept as unknown rather than followed.
7. The English figures in §16.3 come from the dump scan only; English
   articles were read live only where they have an Arabic counterpart.
8. All checks and reviews of this pass were done by the same model as the
   executor and are not independent verification.

### 16.8 Effect on the findings and the recommendation (inference)

The census changes three statements of this report. §7.5's "not shown: that
Arabic has enough cited retracted papers for rates" no longer holds for
link-bearing citations: there are 158 papers in 157 articles, enough to
report edition-level counts with numerator and denominator. The warning gap
is no longer two inspected articles (§7.3) but 170 of 198 citations. And
cross-wiki divergence is measured over every English article that cites a
retracted paper and has an Arabic counterpart, not over 10 purposive papers.

The RESCOPE reading of §12 rested on "consistency and speed can be shown
per paper and per named article pair, not measured as rates for a language
edition". After the census, **consistency can be measured for the whole
Arabic edition** (lower bounds, link-bearing citations), so that part of
the narrower-claim trigger no longer applies. **Speed** (how quickly an
edition responds) still cannot be measured as an edition-level rate from
this evidence: it needs the revision history of every citation, which was
read here only at two points per pair. The executor therefore still reads
the third RESCOPE trigger as met, but more narrowly than before: the
scope can now include edition-level counts of citation, marking, carrying
and visible warnings for English and Arabic; timing remains per paper. The
recommendation stays **RESCOPE (advisory)**; the owner decides, and the
narrower scope in §12 is widened accordingly (§12, point 2).
