"""Build EVIDENCE_MANIFEST.json and the aggregate counts of FEASIBILITY_REPORT.md from the Stage 01 data files.

No network access: every fact is copied from a file under ../data, which stage01_probe.py produced. The case list
(which observation plays which role) is the curated part and is written out below.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

NATURE = {
    "Retraction": "retracted",
    "Correction": "correction",
    "Expression of concern": "expression_of_concern",
    "Reinstatement": "reinstated",
}
# Crossref update types as publishers deposit them, mapped to the event types above.
PUBLISHER_TYPE = {
    "retraction": "retracted",
    "correction": "correction",
    "erratum": "correction",
    "expression_of_concern": "expression_of_concern",
}
WAKEFIELD = "10.1016/S0140-6736(97)11096-0"
OBOKATA = "10.1038/nature12968"
ARSENIC = "10.1126/science.1197258"
SURGISPHERE_LANCET = "10.1016/S0140-6736(20)31180-6"
MEHRA_NEJM = "10.1056/NEJMoa2007621"
LESNE = "10.1038/nature04533"
NEJM_NOTICE = "10.1056/NEJMc2021225"
WATSON_CRICK = "10.1038/171737a0"
MMR_EN, MMR_AR = "MMR vaccine", "لقاح الحصبة والنكاف والحصبة الألمانية"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rw_date(value: str) -> str:
    """Retraction Watch dates are 'M/D/YYYY H:MM'; the time part is 0:00 in all but one record and is dropped."""
    return datetime.strptime(value.split(maxsplit=1)[0], "%m/%d/%Y").date().isoformat()


def compare_dates(rw_iso: str, crossref_parts: list[list[int]]) -> dict[str, Any]:
    """Compare a Retraction Watch date with Crossref date-parts at the coarser of the two precisions."""
    parts = crossref_parts[0]
    cr = "-".join(f"{x:02d}" if i else str(x) for i, x in enumerate(parts))
    return {"retraction_watch": rw_iso, "crossref": cr, "agree": rw_iso.startswith(cr)}


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact binomial interval by bisection on the binomial CDF (standard library only)."""

    def cdf(x: int, p: float) -> float:
        return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(x + 1))

    def solve(f: Any) -> float:
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return (lo + hi) / 2

    lower = 0.0 if k == 0 else solve(lambda p: 1 - cdf(k - 1, p) < alpha / 2)
    upper = 1.0 if k == n else solve(lambda p: cdf(k, p) > alpha / 2)
    return round(lower, 6), round(upper, 6)


class Data:
    def __init__(self, root: Path) -> None:
        d = root / "data"
        self.lookup = {r["doi"]: r for r in load(d / "purposive_lookup.json")["results"]}
        self.lookup.update({r["doi"]: r for r in load(d / "followups/nc3_lookup.json")["results"]})
        self.absence = {w: load(d / f"followups/nc2_absence_check_{w}.json")["checks"] for w in ("en", "ar")}
        self.source = load(d / "purposive_lookup.json")["source"]
        self.discovery = load(d / "purposive_discovery.json")
        self.sample = load(d / "sample_S.json")
        self.sample_discovery = load(d / "sample_S_discovery.json")
        self.sample_errors = load(d / "run-logs/sample_S_search_errors_first_run.json")["responses"]
        self.cross = {
            "ar>en": load(d / "followups/crosswiki_ar_to_en.json")["rows"],
            "en>ar": load(d / "followups/crosswiki_en_to_ar.json")["rows"],
            "S:ar>en": load(d / "followups/crosswiki_S_ar_to_en.json")["rows"],
            "S:en>ar": load(d / "followups/crosswiki_S_en_to_ar.json")["rows"],
        }
        self.timeline = {
            (w, what): load(d / f"followups/timeline_{w}_mmr_{what}.json")
            for w in ("en", "ar")
            for what in ("cited", "marked")
        }

    def obs(self, doi: str, wiki: str, title: str) -> dict[str, Any]:
        for r in self.discovery["results"]:
            if r["doi"] == doi and r["wiki"] == wiki:
                for o in r["observations"]:
                    if o["title"] == title:
                        return o
        raise KeyError((doi, wiki, title))

    def events(self, doi: str) -> list[dict[str, Any]]:
        """Events as Retraction Watch records them, with what Crossref adds and how independent that is.

        Epistemic status follows PROTOCOL.md §2: verified_fact when the record names the event type and the
        original DOI and its notice DOI, if any, resolves in Crossref as a separate work. Crossref `update-to`
        links with source "retraction-watch" repeat the same data and are not independent; links with source
        "publisher" are, and confirm the event type only when their type matches it. A resolving notice with a
        publisher-deposited title is weaker independent support. Dates are not compared when the notice DOI is the
        original DOI.
        """
        lk = self.lookup[doi]
        notices = {n["doi"].lower(): n for n in lk["crossref_notices"]}
        out = []
        for rec in sorted(lk["retraction_watch"], key=lambda r: rw_date(r["RetractionDate"])):
            notice_doi = rec["RetractionDOI"].strip()
            has_notice = notice_doi.lower() not in ("", "unavailable")
            same = notice_doi.lower() == doi.lower()
            n = notices.get(notice_doi.lower())
            back = [
                {"type": u.get("type"), "source": u.get("source")}
                for u in ((n or {}).get("update_to") or [])
                if (u.get("DOI") or "").lower() == doi.lower()
            ]
            ev: dict[str, Any] = {
                "retraction_watch_record_id": rec["Record ID"],
                "event_type": NATURE[rec["RetractionNature"]],
                "event_type_as_recorded": rec["RetractionNature"],
                "date_retraction_watch": rw_date(rec["RetractionDate"]),
                "notice_doi": notice_doi if has_notice else None,
                "notice_doi_equals_original_doi": same,
                "crossref_notice": (
                    {
                        "status": n["status"],
                        "type": n.get("type"),
                        "title_as_deposited": n.get("title"),
                        "published": n.get("published"),
                        "update_to_original": back,
                        "retrieved_at": n["retrieved_at"],
                        "url": n["url"],
                    }
                    if n
                    else None
                ),
            }
            resolves = n is not None and n["status"] == 200
            publisher = {PUBLISHER_TYPE.get(x["type"], x["type"]) for x in back if x["source"] == "publisher"}
            ev["independent_confirmation"] = (
                "publisher_update_to_link"
                if ev["event_type"] in publisher
                else "publisher_update_to_link_with_other_type"
                if publisher
                else "notice_exists_with_publisher_title"
                if resolves and not same
                else "none"
            )
            if n is not None and n.get("published") and not same:
                ev["date_comparison"] = compare_dates(ev["date_retraction_watch"], n["published"])
            if same:
                ev["epistemic_status"] = "uncertain"
                ev["reason"] = "notice DOI equals the original DOI; no separate notice exists to check"
            elif has_notice and not resolves:
                ev["epistemic_status"] = "uncertain"
                ev["reason"] = "notice DOI does not resolve in Crossref"
            else:
                ev["epistemic_status"] = "verified_fact"
                if not has_notice:
                    ev["reason"] = "no notice DOI given; Retraction Watch record only"
            out.append(ev)
        return out

    def original_date(self, doi: str) -> dict[str, Any]:
        rec = self.lookup[doi]["retraction_watch"]
        cr = self.lookup[doi]["crossref_original"].get("published")
        if not rec or not cr:
            return {"epistemic_status": "unavailable", "reason": "no date in one of the sources"}
        cmp = compare_dates(rw_date(rec[0]["OriginalPaperDate"]), cr)
        if cmp["agree"]:
            return {"value": cmp["crossref"], "epistemic_status": "verified_fact", **cmp}
        return {
            "value": None,
            "epistemic_status": "conflicting",
            "alternatives": [
                {"value": cmp["retraction_watch"], "source": "Retraction Watch OriginalPaperDate"},
                {"value": cmp["crossref"], "source": "Crossref published"},
            ],
        }

    def crossref_original(self, doi: str) -> dict[str, Any]:
        c = self.lookup[doi]["crossref_original"]
        return {
            "status": c["status"],
            "title": c.get("title"),
            "published": c.get("published"),
            "updated_by": c.get("updated_by"),
            "retrieved_at": c["retrieved_at"],
            "url": c["url"],
        }


def wp(o: dict[str, Any], method: str, **extra: Any) -> dict[str, Any]:
    keep = ("wiki", "title", "pageid", "revid", "timestamp", "sha1", "retrieved_at", "revision_url")
    out = {k: o[k] for k in keep if k in o}
    out.update(
        {
            "doi_present": o.get("doi_present", o.get("confirmed")),
            "cited_as_identifier": o["confirmed"],
            "occurrence_roles": o.get("occurrence_roles"),
            "retracted_template_at_reference": o.get("marked"),
            "discovery_method": method,
            "epistemic_status": "verified_fact",
        }
    )
    out.update(extra)
    return out


def timeline_case(data: Data, wiki: str) -> dict[str, Any]:
    cited, marked = data.timeline[(wiki, "cited")], data.timeline[(wiki, "marked")]
    tl: dict[str, Any] = {"wiki": wiki, "title": cited["title"], "method": "bisection over the full revision list"}
    for name, t in (("first_cited", cited), ("first_marked", marked)):
        if t["found"]:
            tl[name] = {k: t["first"][k] for k in ("revid", "timestamp", "sha1", "revision_url")}
            tl[name]["previous_revision"] = (
                {k: t["before"][k] for k in ("revid", "timestamp", "sha1", "doi_present", "confirmed", "marked")}
                if t["before"]
                else None
            )
            tl[name]["monotonicity_spot_checks"] = t["monotonicity_spot_checks"]
            tl[name]["monotonicity_violations"] = t["monotonicity_violations"]
            tl[name]["revisions_in_history"] = t["revisions_in_history"]
        else:
            tl[name] = None
    tl["epistemic_status"] = "uncertain"
    tl["reason"] = (
        "first revisions are found by bisection, which assumes a citation or marker once added is never removed and "
        "re-added; only spot-checked"
    )
    return tl


def cases(data: Data) -> list[dict[str, Any]]:
    out = []
    pos = [
        ("POS-01", WAKEFIELD, [("en", MMR_EN), ("ar", MMR_AR)]),
        ("POS-02", OBOKATA, [("en", "Haruko Obokata"), ("ar", "هاروكو أوبوكاتا")]),
        (
            "POS-03",
            ARSENIC,
            [("en", "Felisa Wolfe-Simon"), ("ar", "فيليسا وولف سيمون"), ("en", "Arsenic"), ("ar", "زرنيخ")],
        ),
    ]
    for cid, doi, pages in pos:
        case: dict[str, Any] = {
            "case_id": cid,
            "role": "positive",
            "proposition": "original paper -> verified retraction event -> Wikipedia citation -> exact revision",
            "original_doi": doi,
            "synthetic": False,
            "retraction_events": data.events(doi),
            "crossref_original": data.crossref_original(doi),
            "original_publication_date": data.original_date(doi),
            "wikipedia": [wp(data.obs(doi, w, t), "M1+M2 discovery, confirmed in wikitext") for w, t in pages],
            "verification_method": (
                "Retraction Watch record in the pinned snapshot; notice DOI resolved in Crossref (independence of "
                "each event is stated in independent_confirmation); DOI found as an identifier in the wikitext of "
                "the pinned revision"
            ),
        }
        if doi == WAKEFIELD:
            case["timeline"] = [timeline_case(data, "en"), timeline_case(data, "ar")]
        out.append(case)

    out.append(
        {
            "case_id": "NC-01",
            "role": "negative_control_event_type",
            "proposition": "a correction or expression of concern must not be reported as the retraction",
            "original_doi": WAKEFIELD,
            "synthetic": False,
            "retraction_events": data.events(WAKEFIELD),
            "control": (
                "Record 17269 is a Correction (2004-03-06) whose Crossref notice is titled 'Retraction of an "
                "interpretation'; the retraction is record 4036 (2010-02-06). A system that keys on notice titles "
                "would date the retraction to 2004."
            ),
            "expected": {"17269": "correction", "4036": "retracted"},
            "wikipedia": [],
            "verification_method": "event types read from the Retraction Watch record and the Crossref notice",
        }
    )
    out.append(
        {
            "case_id": "NC-01b",
            "role": "negative_control_event_type",
            "proposition": "a record whose notice DOI equals the original DOI is not a separate notice",
            "original_doi": LESNE,
            "synthetic": False,
            "retraction_events": data.events(LESNE),
            "control": "Record 54372 (Expression of concern, 2022) gives the original DOI as its notice DOI.",
            "wikipedia": [],
            "verification_method": "Retraction Watch record compared with the Crossref record of the same DOI",
        }
    )
    nc2_wp = []
    absence = {c["revid"]: c for w in ("en", "ar") for c in data.absence[w]}
    pair = next(r for r in data.cross["en>ar"] if r["doi"] == WAKEFIELD and r["src"]["title"] == "Causes of autism")
    candidates = [
        (data.timeline[("en", "cited")]["before"], "revision preceding the first citing revision (bisection)"),
        (data.timeline[("ar", "cited")]["before"], "revision preceding the first citing revision (bisection)"),
        (
            pair["dst"],
            f"interlanguage link from en '{pair['src']['title']}' (rev {pair['src']['revid']})",
        ),
    ]
    for rev, how in candidates:
        check = absence[rev["revid"]]
        if check["sha1"] != rev["sha1"]:
            raise ValueError(f"absence check of revid {rev['revid']} is of different content")
        nc2_wp.append(
            {
                **{k: rev[k] for k in ("wiki", "title", "revid", "timestamp", "sha1") if k in rev},
                "revision_url": f"https://{rev['wiki']}.wikipedia.org/w/index.php?oldid={rev['revid']}",
                "doi_present": rev["doi_present"],
                "cited_as_identifier": rev["confirmed"],
                "discovery_method": how,
                "independent_substring_counts": check["counts"],
                "wikitext_length": check["length"],
                "epistemic_status": "verified_fact",
            }
        )
    out.append(
        {
            "case_id": "NC-02",
            "role": "negative_control_extraction",
            "proposition": "extraction must report no citation in a pinned revision that does not contain the DOI",
            "original_doi": WAKEFIELD,
            "synthetic": False,
            "wikipedia": nc2_wp,
            "control": (
                "The DOI matcher finds no occurrence of the DOI in each listed revision, and a separate plain "
                "substring count finds none of the needles listed in independent_substring_counts (DOI suffix, "
                "PMID, PII and the author's name in Latin and Arabic script). The English revision names Wakefield "
                "without any identifier, so the paper is discussed but not cited by DOI; the first Arabic revision "
                "predates any mention and is a trivial negative. Nothing is claimed about other revisions or about "
                "references to the paper that carry no DOI."
            ),
            "verification_method": "doi_positions on the full wikitext, plus absence-check substring counts",
        }
    )
    wc = data.lookup[WATSON_CRICK]
    out.append(
        {
            "case_id": "NC-03",
            "role": "negative_control_absence",
            "proposition": "a paper with no record in the checked sources is reported as "
            "'not_found_in_checked_sources' (uncertain), never as 'not retracted'",
            "original_doi": WATSON_CRICK,
            "synthetic": False,
            "retraction_status": {
                "value": "not_found_in_checked_sources",
                "epistemic_status": "uncertain",
                "checked_sources": [
                    "Retraction Watch snapshot, OriginalPaperDOI column",
                    "Retraction Watch snapshot, RetractionDOI column",
                    "Crossref REST updated-by of this DOI",
                ],
                "retraction_watch_records_as_original": len(wc["retraction_watch"]),
                "retraction_watch_records_as_notice": wc["retraction_watch_records_naming_it_as_notice"],
                "crossref_status": wc["crossref_original"]["status"],
                "crossref_title": wc["crossref_original"].get("title"),
                "crossref_updated_by": wc["crossref_original"].get("updated_by"),
                "crossref_retrieved_at": wc["crossref_original"]["retrieved_at"],
            },
            "wikipedia": [],
            "verification_method": "lookup in both sources; chosen as a well-known paper not expected to be retracted",
        }
    )
    notice = data.lookup[NEJM_NOTICE]
    mentions = [
        wp(o, "M1/M2 discovery for the original DOI; the DOI appears only inside a citation of the notice")
        for r in data.discovery["results"]
        if r["doi"] == MEHRA_NEJM and r["wiki"] == "en"
        for o in r["observations"]
        if not o["confirmed"]
    ]
    for m in mentions:
        m["checked_doi"] = MEHRA_NEJM
    out.append(
        {
            "case_id": "NC-04",
            "role": "negative_control_notice_citation",
            "proposition": "a citation of a retraction notice whose title contains the original DOI is not a "
            "citation of the retracted paper",
            "original_doi": MEHRA_NEJM,
            "notice_doi": NEJM_NOTICE,
            "synthetic": False,
            "notice": {
                "retraction_watch_records_naming_it_as_notice": notice["retraction_watch_records_naming_it_as_notice"],
                "retraction_watch_records_as_original": len(notice["retraction_watch"]),
                "crossref_title": notice["crossref_original"].get("title"),
                "crossref_update_to": notice["crossref_original"].get("update_to"),
                "crossref_retrieved_at": notice["crossref_original"]["retrieved_at"],
            },
            "wikipedia": mentions,
            "expected": "doi_present true, cited_as_identifier false for every listed revision",
            "finding": "These are the articles found by M1/M2 searches for the original DOI in which it occurs only "
            "in a citation of the notice; other articles may cite the notice without the original DOI.",
            "verification_method": "occurrence role of each DOI occurrence in the pinned wikitext",
        }
    )
    unresolved_ar = [
        o
        for r in data.discovery["results"]
        if r["doi"] == SURGISPHERE_LANCET and r["wiki"] == "ar"
        for o in r["observations"]
        if not o["confirmed"]
    ]
    out.append(
        {
            "case_id": "U-01",
            "role": "unresolved",
            "proposition": "is the Lancet paper cited on Arabic Wikipedia?",
            "original_doi": SURGISPHERE_LANCET,
            "synthetic": False,
            "wikipedia": [wp(o, "M2 search only") for o in unresolved_ar],
            "finding": "The DOI occurs as a doi.org URL inside the title field of an unrelated, malformed citation "
            "(pasted text). Classified as a mention, not a citation; a reader may judge otherwise.",
            "epistemic_status": "uncertain",
        }
    )
    purposive = sorted({r["doi"] for r in data.discovery["results"]})
    date_checks = [{"doi": d, **data.original_date(d)} for d in purposive]
    event_dates = [
        {"doi": d, "retraction_watch_record_id": ev["retraction_watch_record_id"], **ev["date_comparison"]}
        for d in purposive
        for ev in data.events(d)
        if "date_comparison" in ev and not ev["date_comparison"]["agree"]
    ]
    out.append(
        {
            "case_id": "U-02",
            "role": "unresolved",
            "proposition": "the original publication date and the notice date agree between Retraction Watch and "
            "Crossref",
            "synthetic": False,
            "epistemic_status": "conflicting",
            "original_publication_dates": date_checks,
            "conflicting_original_dates": [c["doi"] for c in date_checks if c["epistemic_status"] == "conflicting"],
            "event_date_disagreements": event_dates,
            "finding": "Where the sources disagree both values are kept; neither is chosen. Crossref 'published' "
            "may be the print or the online date.",
        }
    )
    out.append(
        {
            "case_id": "U-03",
            "role": "unresolved",
            "proposition": "event types and dates deposited by publishers in Crossref",
            "original_doi": SURGISPHERE_LANCET,
            "synthetic": False,
            "epistemic_status": "conflicting",
            "crossref_original": data.crossref_original(SURGISPHERE_LANCET),
            "finding": "Publisher-sourced updated-by entries list the retraction notice as an 'erratum' and a "
            "different DOI as a 'retraction' dated at publication, while the Retraction Watch-sourced entries "
            "give correction, expression of concern and retraction with distinct notices.",
        }
    )
    return out


def crosswiki_counts(rows: list[dict[str, Any]], dst: str) -> dict[str, Any]:
    """Classify each (paper, citing article) row by what its interlanguage link and linked article show.

    Failed or malformed lookups are counted as such and never as "no linked article" or "does not cite".
    """
    c: Counter[str] = Counter()
    for row in rows:
        link, status = row["link_status"], row.get("dst_status")
        if link == "no_link":
            c[f"no_{dst}_article_linked"] += 1
        elif link != "linked":
            c[f"link_lookup_{link}"] += 1
        elif status == "doi_cited":
            d = row["dst"]
            c[f"{dst}_cites_src_marked_{bool(row['src']['marked'])}_{dst}_marked_{bool(d['marked'])}"] += 1
        elif status == "doi_mention_only":
            c[f"{dst}_mentions_doi_only"] += 1
        elif status == "doi_not_found":
            c[f"{dst}_article_does_not_cite"] += 1
        else:
            c[f"linked_article_{status}"] += 1
    return {"rows": len(rows), **dict(sorted(c.items()))}


def aggregates(data: Data) -> dict[str, Any]:
    agg: dict[str, Any] = {}
    for wiki in ("en", "ar"):
        rs = [r for r in data.discovery["results"] if r["wiki"] == wiki]
        obs = [o for r in rs for o in r["observations"]]
        m1 = {(r["doi"], t) for r in rs for t in r["m1"]["titles"]}
        m2 = {(r["doi"], t) for r in rs for t in r["m2"]["titles"]}
        conf = {(r["doi"], o["title"]) for r in rs for o in r["observations"] if o["confirmed"]}
        agg[f"purposive_{wiki}"] = {
            "dois": len(rs),
            "dois_cited": sum(any(o["confirmed"] for o in r["observations"]) for r in rs),
            "citing_pairs": len(conf),
            "citing_pairs_with_retracted_template": sum(
                1 for r in rs for o in r["observations"] if o["confirmed"] and o.get("marked")
            ),
            "mention_only_pairs": sum(1 for o in obs if not o["confirmed"]),
            "found_by_m1": len(m1 & conf),
            "found_by_m2": len(m2 & conf),
            "m2_only": len((m2 - m1) & conf),
            "m1_only": len((m1 - m2) & conf),
            "all_searches_complete": all(r["complete"] for r in rs),
        }
    agg["crosswiki_en_to_ar"] = crosswiki_counts(data.cross["en>ar"], "ar")
    agg["crosswiki_ar_to_en"] = crosswiki_counts(data.cross["ar>en"], "en")
    agg["sample_crosswiki_en_to_ar"] = crosswiki_counts(data.cross["S:en>ar"], "ar")
    agg["sample_crosswiki_ar_to_en"] = crosswiki_counts(data.cross["S:ar>en"], "en")
    independence: Counter[str] = Counter()
    for doi in sorted({r["doi"] for r in data.discovery["results"]}):
        for ev in data.events(doi):
            independence[f"{ev['event_type']}:{ev['independent_confirmation']}"] += 1
    agg["purposive_event_independence"] = dict(sorted(independence.items()))
    frame = data.sample["records"][0]["frame_size"]
    for wiki in ("en", "ar"):
        rs = [r for r in data.sample_discovery["results"] if r["wiki"] == wiki]
        complete = [r for r in rs if r["complete"]]
        k = sum(any(o["confirmed"] for o in r["observations"]) for r in complete)
        # First run (2026-10-26): searches that received a MediaWiki error body were unavailable, not "no hits".
        unavailable_first = sorted({e["doi"] for e in data.sample_errors if e["wiki"] == wiki})
        n_first = len(rs) - len(unavailable_first)
        cited_first = [r for r in complete if r["doi"] not in unavailable_first]
        k_first = sum(any(o["confirmed"] for o in r["observations"]) for r in cited_first)
        dates = sorted({c["retrieved_at"][:10] for r in rs for c in r["m2"]["calls"]})
        agg[f"sample_{wiki}"] = {
            "population": "Retraction Watch Retraction records with an original DOI, de-duplicated by DOI",
            "estimand": (
                "share of frame DOIs for which an M2 insource search of the main namespace finds a page whose latest "
                "revision cites the DOI as an identifier; a rate discoverable by this method, not the prevalence of "
                "citations to retracted work"
            ),
            "frame_size": frame,
            "sampled": len(rs),
            "searches_complete": len(complete),
            "searches_unavailable": len(rs) - len(complete),
            "search_dates": dates,
            "dois_cited": k,
            "share": round(k / len(complete), 4) if complete else None,
            "clopper_pearson_95": clopper_pearson(k, len(complete)) if complete else None,
            "first_run": {
                "searches_complete": n_first,
                "searches_unavailable": len(unavailable_first),
                "unavailable_dois": unavailable_first,
                "dois_cited": k_first,
                "clopper_pearson_95": clopper_pearson(k_first, n_first) if n_first else None,
            },
            "mention_only_dois": sum(
                any(o["confirmed"] is False for o in r["observations"])
                and not any(o["confirmed"] for o in r["observations"])
                for r in complete
            ),
            "cited_dois": sorted(r["doi"] for r in complete if any(o["confirmed"] for o in r["observations"])),
            "observations": [
                {"doi": r["doi"], **wp(o, "M2 discovery, confirmed in wikitext")}
                for r in complete
                for o in r["observations"]
            ],
        }
    return agg


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    data = Data(a.root)
    manifest = {
        "schema": "citerift.stage01.evidence-manifest/1",
        "description": "Stage 01 inspected cases with provenance. Real data only; no synthetic records.",
        "generator": "docs/verification/stage-01/scripts/build_manifest.py",
        "synthetic": False,
        "epistemic_vocabulary": ["verified_fact", "model_inference", "uncertain", "unavailable", "conflicting"],
        "sources": {
            "retraction_watch": data.source,
            "crossref_rest_api": "https://api.crossref.org/works/{doi}",
            "wikipedia": "MediaWiki Action API of en.wikipedia.org and ar.wikipedia.org",
            "wikipedia_user_agent": data.discovery["user_agent"],
            "note": "retrieval times are recorded per observation (retrieved_at)",
        },
        "cases": cases(data),
        "aggregates": aggregates(data),
    }
    a.out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(manifest["aggregates"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
