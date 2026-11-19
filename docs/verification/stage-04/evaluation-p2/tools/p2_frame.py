"""Stage 04 P2: the evaluation frames, exposure exclusion and strata (P2 PREREGISTRATION.md section 3).

Derived from the historical ``evaluation/tools/s13_frame.py`` (unchanged); the differences are the exposure manifest
(v2, pinned by SHA-256 in ``PARAMETERS.json``), the exclusion audit (the sources of the manifest records each excluded
page matched) and the no-overlap proof written into ``FRAME.json``.

Inputs (all hashed in the output; the scans and the listed tier are the historical P's committed files, read only):

- the Stage 01 dump scans of arwiki and enwiki (``stage-01/data/census/ar_scan.json``; ``evaluation/frame/en_scan.json``
  re-derived for the historical P by the same unchanged Stage 01 script, E-10);
- the exposure manifest v2 (``freeze-2/exposure/EXPOSURE_MANIFEST.json``, article level, D-076);
- the Stage 03 listed tier (``evaluation/frame/listed_tier.json``), checked against the ``listed.output_sha256`` the
  exposure manifest v2 recorded; recorded, not applied (D-070, kept by D-076).

Frame member: a namespace-0, non-redirect page of the scan (it has at least one external link to the DOI or PMID of a
Retraction Watch record, original paper or notice). Stratum S1: at least one linked record of nature ``Retraction``
reached through the original paper's identifier; S2: every other frame member. Exclusion: the page's (wiki, page_id)
or (wiki, normalized title) is in the exposure manifest, or its page id or title is in the listed tier (any wiki).

Only identities, strata and counts are computed (E-14): nothing is fetched and no article content is read.

Run from the repository root:

    python -P docs/verification/stage-04/evaluation-p2/tools/p2_frame.py \
        --out docs/verification/stage-04/evaluation-p2/frame/FRAME.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from p2_common import (
    LANGUAGES,
    PARAMETERS,
    REPO,
    digest,
    exposure_check,
    file_sha256,
    norm_title,
    read_json,
    write_json,
)

FORMAT = "citerift-stage04-eval-frame/2"
AR_SCAN = REPO / "docs/verification/stage-01/data/census/ar_scan.json"
EN_SCAN = REPO / "docs/verification/stage-04/evaluation/frame/en_scan.json"
LISTED = REPO / "docs/verification/stage-04/evaluation/frame/listed_tier.json"
EXCLUSION_ORDER = ("exposure_page_id", "exposure_title", "exposure_title_other_wiki", "listed_page_id", "listed_title")
EXPOSURE_REASONS = ("exposure_page_id", "exposure_title", "exposure_title_other_wiki")


def applying(reasons: list[str], exclude_listed: bool) -> list[str]:
    """The reasons that exclude: exposure-manifest reasons always, listed-tier reasons only when adopted."""
    return [r for r in reasons if exclude_listed or r in EXPOSURE_REASONS]


def stratum(page: dict[str, Any]) -> str:
    for rec in page["records"]:
        if rec["nature"] == "Retraction" and any(v["side"] == "original" for v in rec["via"]):
            return "S1"
    return "S2"


def exposure_keys(manifest: dict[str, Any]) -> tuple[set[tuple[str, int]], set[tuple[str, str]]]:
    ids: set[tuple[str, int]] = set()
    titles: set[tuple[str, str]] = set()
    for a in manifest["articles"]:
        if a["page_id"] is not None:
            ids.add((a["wiki"], int(a["page_id"])))
        for t in a["titles"]:
            titles.add((a["wiki"], norm_title(a["wiki"], t)))
    return ids, titles


def exclusion(
    wiki: str,
    page: dict[str, Any],
    exp_ids: set[tuple[str, int]],
    exp_titles: set[tuple[str, str]],
    listed_ids: set[int],
    listed_titles: dict[str, set[str]],
) -> list[str]:
    """Every exclusion reason that applies, in EXCLUSION_ORDER."""
    title = norm_title(wiki, page["title"])
    out = []
    if (wiki, page["page_id"]) in exp_ids:
        out.append("exposure_page_id")
    if (wiki, title) in exp_titles:
        out.append("exposure_title")
    elif any(norm_title("en", title) == norm_title("en", t) for w, t in exp_titles if w != wiki):
        out.append("exposure_title_other_wiki")  # the other language's article of an exposed one (same title)
    if page["page_id"] in listed_ids:
        out.append("listed_page_id")
    if title in listed_titles[wiki]:
        out.append("listed_title")
    return out


def matched_sources(wiki: str, page: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    """Exclusion audit: the sources of every exposure-manifest record the page matches (page id or title, this wiki or
    the other one)."""
    title = norm_title("en", norm_title(wiki, page["title"]))
    out: set[str] = set()
    for a in manifest["articles"]:
        same_id = a["wiki"] == wiki and a["page_id"] is not None and int(a["page_id"]) == page["page_id"]
        same_title = any(norm_title("en", norm_title(a["wiki"], t)) == title for t in a["titles"])
        if same_id or same_title:
            out.update(a.get("sources") or [])
    return sorted(out)


def overlap(frames: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """No-overlap proof: frame members against every exposure-manifest record, by (wiki, page id), by (wiki,
    normalized title) and by normalized title in the other wiki. Every count must be 0."""
    exp_ids, exp_titles = exposure_keys(manifest)
    any_title = {norm_title("en", t) for _, t in exp_titles}
    out: dict[str, Any] = {}
    for wiki in LANGUAGES:
        members = frames[wiki]["frame"]
        out[wiki] = {
            "members": len(members),
            "page_id_overlap": sum(1 for m in members if (wiki, m["page_id"]) in exp_ids),
            "title_overlap": sum(1 for m in members if (wiki, norm_title(wiki, m["title"])) in exp_titles),
            "any_wiki_title_overlap": sum(
                1 for m in members if norm_title("en", norm_title(wiki, m["title"])) in any_title
            ),
        }
    campaign = [a for a in manifest["articles"] if "S04-CAMPAIGN-80" in (a.get("sources") or [])]
    in_frame = [
        f"{a['wiki']}:{a['page_id']}"
        for a in campaign
        if a["page_id"] is not None and any(m["page_id"] == int(a["page_id"]) for m in frames[a["wiki"]]["frame"])
    ]
    out["campaign_articles"] = len(campaign)
    out["campaign_articles_in_frame"] = in_frame
    out["passed"] = not in_frame and all(
        out[w][k] == 0 for w in LANGUAGES for k in ("page_id_overlap", "title_overlap", "any_wiki_title_overlap")
    )
    return out


def build(
    scans: dict[str, dict[str, Any]], manifest: dict[str, Any], listed: dict[str, Any], exclude_listed: bool
) -> dict[str, Any]:
    exp_ids, exp_titles = exposure_keys(manifest)
    listed_ids = {int(i) for i in listed["page_ids"]}
    listed_titles = {w: {norm_title(w, t) for t in listed["titles"]} for w in LANGUAGES}
    out: dict[str, Any] = {}
    for wiki in LANGUAGES:
        scan = scans[wiki]
        if scan["wiki"] != wiki:
            raise ValueError(f"the {wiki} scan names wiki {scan['wiki']!r}")
        members, excluded = [], []
        counts: dict[str, Any] = {"scan_pages": len(scan["pages"]), "namespace0_non_redirect": 0}
        for page in scan["pages"]:
            if page["ns"] != 0 or page["redirect"]:
                continue
            counts["namespace0_non_redirect"] += 1
            row = {"page_id": page["page_id"], "title": page["title"], "stratum": stratum(page)}
            reasons = exclusion(wiki, page, exp_ids, exp_titles, listed_ids, listed_titles)
            if applying(reasons, exclude_listed):
                excluded.append({**row, "reasons": reasons, "exposure_sources": matched_sources(wiki, page, manifest)})
            else:
                members.append({**row, "listed_only": True} if reasons else row)
        by_stratum = {s: sum(1 for m in members if m["stratum"] == s) for s in ("S1", "S2")}
        before = {s: by_stratum[s] + sum(1 for e in excluded if e["stratum"] == s) for s in ("S1", "S2")}
        first_reason = {r: sum(1 for e in excluded if e["reasons"][0] == r) for r in EXCLUSION_ORDER}
        members.sort(key=lambda m: m["page_id"])
        excluded.sort(key=lambda m: m["page_id"])
        out[wiki] = {
            "counts": {
                **counts,
                "before_exclusion_by_stratum": before,
                "excluded": len(excluded),
                "excluded_by_first_reason": first_reason,
                "frame_by_stratum": by_stratum,
                "frame": len(members),
                "listed_only_kept": sum(1 for m in members if m.get("listed_only")),
                "listed_only_kept_by_stratum": {
                    s: sum(1 for m in members if m.get("listed_only") and m["stratum"] == s) for s in ("S1", "S2")
                },
            },
            "dump_run": scan["dumps"],
            "retraction_watch": scan["retraction_watch"],
            "frame": members,
            "frame_digest": digest(members),
            "excluded": excluded,
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 04 P2 evaluation frames")
    ap.add_argument("--ar-scan", type=Path, default=AR_SCAN)
    ap.add_argument("--en-scan", type=Path, default=EN_SCAN)
    ap.add_argument("--listed", type=Path, default=LISTED)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    exposure = exposure_check()
    manifest = read_json(exposure)
    listed_sha = file_sha256(a.listed)
    if listed_sha != manifest["listed"]["output_sha256"]:
        sys.exit(f"the listed tier {listed_sha} is not the one the exposure manifest recorded")
    scans = {"ar": read_json(a.ar_scan), "en": read_json(a.en_scan)}
    exclude_listed = bool(read_json(PARAMETERS)["frame"]["exclude_listed_tier"])
    frames = build(scans, manifest, read_json(a.listed), exclude_listed)
    result = {
        "format": FORMAT,
        "inputs": {
            "ar_scan_sha256": file_sha256(a.ar_scan),
            "en_scan_sha256": file_sha256(a.en_scan),
            "exposure_manifest_sha256": file_sha256(exposure),
            "listed_tier_sha256": listed_sha,
            "generator_sha256": file_sha256(Path(__file__)),
        },
        "member_rule": "namespace 0, not a redirect, in the 2026-10-01 dump scan (link to an RW original or notice "
        "DOI/PMID); S1: a linked record of nature Retraction through the original identifier; S2: otherwise",
        "exclusion_rule": "exposure manifest v2 (wiki, page_id) or (wiki, normalized title), or a normalized title of "
        "the other wiki's exposed article"
        + ("; listed tier page id or normalized title in any wiki" if exclude_listed else "")
        + " (listed-tier matches are always recorded)",
        "exclude_listed_tier": exclude_listed,
        "frames": frames,
        "overlap_check": overlap(frames, manifest),
    }
    if not result["overlap_check"]["passed"]:
        sys.exit(f"exposure overlap: {result['overlap_check']}")
    write_json(a.out, result)
    for wiki in LANGUAGES:
        print(wiki, frames[wiki]["counts"])
    print("overlap", result["overlap_check"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
