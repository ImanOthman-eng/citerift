"""Stage 04 Step 13: the evaluation frames, exposure exclusion and strata (PREREGISTRATION.md section 3).

Inputs (all hashed in the output):

- the Stage 01 dump scans of arwiki and enwiki (``stage01_census.py dump-scan`` on the pinned 2026-10-01 dumps; the
  Arabic one equals the committed ``stage-01/data/census/ar_scan.json`` except ``generated_at``; the English one is
  re-derived by the same unchanged script, E-10);
- the Step 12 exposure manifest (``freeze/exposure/EXPOSURE_MANIFEST.json``, article level);
- the Stage 03 listed tier, produced by the Stage 03 rule at the evidence commit ``bdeeac1`` and checked against the
  ``listed.output_sha256`` the exposure manifest recorded (E-02: adopted, wiki-agnostic, over-inclusive).

Frame member: a namespace-0, non-redirect page of the scan (it has at least one external link to the DOI or PMID of a
Retraction Watch record, original paper or notice). Stratum S1: at least one linked record of nature ``Retraction``
reached through the original paper's identifier; S2: every other frame member. Exclusion: the page's (wiki, page_id)
or (wiki, normalized title) is in the exposure manifest, or its page id or title is in the listed tier (any wiki).

Only identities, strata and counts are computed (E-14): nothing is fetched and no article content is read.

Run from the repository root:

    python -P docs/verification/stage-04/evaluation/tools/s13_frame.py --ar-scan A --en-scan E --listed L --out F
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s13_common import EVALUATION, LANGUAGES, REPO, digest, file_sha256, norm_title, read_json, write_json

FORMAT = "citerift-stage04-eval-frame/1"
EXPOSURE = REPO / "docs/verification/stage-04/freeze/exposure/EXPOSURE_MANIFEST.json"
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
                excluded.append({**row, "reasons": reasons})
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
    ap = argparse.ArgumentParser(description="Stage 04 Step 13 evaluation frames")
    ap.add_argument("--ar-scan", type=Path, required=True)
    ap.add_argument("--en-scan", type=Path, required=True)
    ap.add_argument("--listed", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    manifest = read_json(EXPOSURE)
    listed_sha = file_sha256(a.listed)
    if listed_sha != manifest["listed"]["output_sha256"]:
        sys.exit(f"the listed tier {listed_sha} is not the one the exposure manifest recorded")
    scans = {"ar": read_json(a.ar_scan), "en": read_json(a.en_scan)}
    exclude_listed = bool(read_json(EVALUATION / "PARAMETERS.json")["frame"]["exclude_listed_tier"])
    frames = build(scans, manifest, read_json(a.listed), exclude_listed)
    result = {
        "format": FORMAT,
        "inputs": {
            "ar_scan_sha256": file_sha256(a.ar_scan),
            "en_scan_sha256": file_sha256(a.en_scan),
            "exposure_manifest_sha256": file_sha256(EXPOSURE),
            "listed_tier_sha256": listed_sha,
            "generator_sha256": file_sha256(Path(__file__)),
        },
        "member_rule": "namespace 0, not a redirect, in the 2026-10-01 dump scan (link to an RW original or notice "
        "DOI/PMID); S1: a linked record of nature Retraction through the original identifier; S2: otherwise",
        "exclusion_rule": "exposure manifest (wiki, page_id) or (wiki, normalized title)"
        + ("; listed tier page id or normalized title in any wiki" if exclude_listed else "")
        + " (listed-tier matches are always recorded)",
        "exclude_listed_tier": exclude_listed,
        "frames": frames,
    }
    write_json(a.out, result)
    for wiki in LANGUAGES:
        print(wiki, frames[wiki]["counts"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
