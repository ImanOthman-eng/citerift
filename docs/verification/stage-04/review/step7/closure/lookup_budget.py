"""Derivation of the Stage 04 lookup evidence budget (owner decision D-048, Step 7 closure).

The budget ``B`` bounds the stored bytes of index rows one lookup reads (``Index.gather_bounded``, maintenance
A-02-001). This script derives a default for ``B`` from:

1. **The Stage 02 event representation.** An event row's stored bytes ``s`` (what the budget charges) and the
   canonical JSON its rows become in a Stage 04 lookup observation. The observation is assumed to be (Step 8 design
   condition, stated in STEP7_CLOSURE.md) the canonical JSON of the gathered ``Evidence`` without its derived
   ``evidence_set`` (rebuilt from the events), plus the Stage 02 projection: ``query, keys, state, identity, role,
   anchor, events, candidate_groups, notice_hits, issues, crossref, checked_sources, relevant_gap, projection``.
2. **Serialized size.** For every lookup shape Stage 02 produces (an exact DOI match with its secondary PMID, a PMID
   match, a notice-only match, an ambiguous pair, a PMID role collision, a no-record lookup with relevance hits),
   built on synthetic rows whose text is empty (the largest structure per stored byte) and on rows whose text is all
   characters that canonical JSON escapes (the largest escaping per stored byte), the observation size ``O`` and the
   bytes the lookup needs ``N`` are measured at two sizes. ``O`` is affine in the rows, so the slope
   ``rho = dO / dN`` and the intercept ``F`` describe every size of that shape.
3. **The post-D-047 storage model.** One lookup observation is one blob, ``MAX_BLOB_BYTES``. The default must satisfy
   ``rho_max * B + F_max <= MAX_BLOB_BYTES``.
4. **The query's memory.** The traced Python peak of ``gather_bounded`` per needed byte, at the same shapes.
5. **The pinned index (sanity only).** The largest ``N`` of any key of the pinned Retraction Watch index, and the
   headroom of the selected ``B`` over it.

Usage (from the repository root)::

    uv run python docs/verification/stage-04/review/step7/closure/lookup_budget.py --index PINNED.sqlite \
        [--out docs/verification/stage-04/review/step7/closure/lookup_budget.json]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO / "tests" / "stage02"))

import rde_support as S  # noqa: E402

from citerift.investigation.blobs import MAX_BLOB_BYTES  # noqa: E402
from citerift.investigation.canonical import canon  # noqa: E402
from citerift.investigation.lookup import DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES  # noqa: E402
from citerift.retraction import query  # noqa: E402
from citerift.retraction.identifiers import DOI_MAX_LENGTH  # noqa: E402
from citerift.retraction.query import Evidence, EvidenceBudgetExceeded, Index  # noqa: E402

MIB = 1024 * 1024
# Characters canonical JSON (ensure_ascii=False) writes as six bytes; Stage 02 keeps them in text fields if present.
ESCAPED = "\x01"
# A DOI suffix of characters canonical JSON writes as two bytes, repeated in several fields of a row.
LONG_DOI = "10.5555/" + '"\\' * ((DOI_MAX_LENGTH - len("10.5555/") - 8) // 2)  # room for a suffix "o<i>"


def observation(ev: Evidence) -> dict[str, Any]:
    return {
        "query": ev.query,
        "keys": ev.keys,
        "state": ev.state,
        "identity": ev.identity,
        "role": ev.role,
        "anchor": ev.anchor,
        "events": ev.events,
        "candidate_groups": ev.candidate_groups,
        "notice_hits": ev.notice_hits,
        "issues": ev.issues,
        "crossref": ev.crossref,
        "checked_sources": ev.checked_sources,
        "relevant_gap": ev.relevant_gap,
        "projection": query.projection_of(ev),
    }


def needed(ix: Index, doi: str | None, pmid: str | None) -> int:
    budget = 0
    while True:
        try:
            ix.gather_bounded(doi, pmid, budget_bytes=budget)
            return budget
        except EvidenceBudgetExceeded as exc:
            budget = exc.needed


TEXT_KINDS = {"empty": 0, "escaped": 64, "escaped_long": 4096}


def text(kind: str) -> str:
    return ESCAPED * TEXT_KINDS[kind]


# Lookup shapes: rows(n, text kind) -> (rows, doi, pmid). Text fields are Title, Journal, Author.
def _r(i: int, t: str, **v: str) -> dict[str, str]:
    return S.row(**{"Record ID": str(i + 1), "Title": t, "Journal": t, "Author": t, "RetractionDate": "", **v})


Shape = Callable[[int, str], tuple[list[dict[str, str]], str | None, str | None]]
SHAPES: dict[str, Shape] = {
    "doi_match_with_secondary_pmid": lambda n, t: (
        [
            _r(i, t, RetractionNature="Retraction", OriginalPaperDOI="10.5555/a", OriginalPaperPubMedID="9")
            for i in range(n)
        ]
        + [_r(n + i, t, RetractionNature="Correction", OriginalPaperPubMedID="9") for i in range(n)],
        "10.5555/a",
        None,
    ),
    "pmid_match_bridged_doi": lambda n, t: (
        [
            _r(i, t, RetractionNature="Retraction", OriginalPaperDOI="10.5555/a", OriginalPaperPubMedID="9")
            for i in range(n)
        ]
        + [
            _r(n + i, t, RetractionNature="Correction", OriginalPaperDOI="10.5555/a", OriginalPaperPubMedID="8")
            for i in range(n)
        ],
        None,
        "9",
    ),
    "notice_only": lambda n, t: (
        [
            _r(i, t, RetractionNature="Retraction", OriginalPaperDOI=f"10.5555/o{i}", RetractionDOI="10.5555/n")
            for i in range(n)
        ],
        "10.5555/n",
        None,
    ),
    "ambiguous_pair": lambda n, t: (
        [
            _r(i, t, RetractionNature="Retraction", OriginalPaperDOI="10.5555/a", OriginalPaperPubMedID="8")
            for i in range(n)
        ]
        + [
            _r(n + i, t, RetractionNature="Retraction", OriginalPaperDOI="10.5555/b", OriginalPaperPubMedID="9")
            for i in range(n)
        ],
        "10.5555/a",
        "9",
    ),
    "pmid_role_collision": lambda n, t: (
        [
            _r(
                i,
                t,
                RetractionNature="Retraction",
                OriginalPaperDOI="10.5555/a",
                OriginalPaperPubMedID="9",
                RetractionPubMedID="9",
            )
            for i in range(n)
        ],
        "10.5555/a",
        "9",
    ),
    "long_doi_notice_only": lambda n, t: (
        [
            _r(i, t, RetractionNature="Retraction", OriginalPaperDOI=LONG_DOI + f"o{i}", RetractionDOI=LONG_DOI)
            for i in range(n)
        ],
        LONG_DOI,
        None,
    ),
    "long_doi_match_with_collision": lambda n, t: (
        [
            _r(
                i,
                t,
                RetractionNature="Retraction",
                OriginalPaperDOI=LONG_DOI,
                OriginalPaperPubMedID="9",
                RetractionPubMedID="9",
            )
            for i in range(n)
        ],
        LONG_DOI,
        "9",
    ),
    "no_record_with_relevance_hits": lambda n, t: (
        [_r(i, t, RetractionNature="Retraction", OriginalPaperDOI=f"see 10.5555/z {t or 'x'}{i}") for i in range(n)]
        + [_r(n + i, t, RetractionNature="Bogus", OriginalPaperDOI="10.5555/z") for i in range(n)],
        "10.5555/z",
        None,
    ),
}


def measure(shape: str, kind: str, n: int, tmp: Path) -> dict[str, Any]:
    rows, doi, pmid = SHAPES[shape](n, text(kind))
    idx = S.build_rows(tmp, rows)
    with Index(idx) as ix:
        need = needed(ix, doi, pmid)
        tracemalloc.start()
        ev = ix.gather_bounded(doi, pmid, budget_bytes=need)
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        tracemalloc.start()
        size = len(canon(observation(ev)))
        enc_peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        plain = ix.gather(doi, pmid)
    return {
        "rows": len(rows),
        "state": ev.state,
        "events": len(ev.events),
        "issues": len(ev.issues),
        "needed": need,
        "observation_bytes": size,
        "gather_peak": peak,
        "encode_peak": enc_peak,
        "same_as_gather": canon(observation(plain)) == canon(observation(ev)),
    }


def shapes(tmp: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for shape in SHAPES:
        for kind in TEXT_KINDS:
            small = measure(shape, kind, 50, tmp / f"{shape}-{kind}-50")
            large = measure(shape, kind, 200, tmp / f"{shape}-{kind}-200")
            dn = large["needed"] - small["needed"]
            if dn <= 0 or large["events"] + large["issues"] == 0:
                raise SystemExit(f"shape {shape}/{kind} produced no evidence: {large}")
            rho = (large["observation_bytes"] - small["observation_bytes"]) / dn
            intercept = small["observation_bytes"] - rho * small["needed"]
            out[f"{shape}/{kind}"] = {
                "at_50": small,
                "at_200": large,
                "rho_observation_bytes_per_needed_byte": round(rho, 4),
                "intercept_bytes": round(intercept),
                "gather_peak_per_needed_byte": round(large["gather_peak"] / large["needed"], 3),
                "encode_peak_per_needed_byte": round(large["encode_peak"] / large["needed"], 3),
            }
    return out


def escaping_check(tmp: Path) -> dict[str, Any]:
    """Whether Stage 02 keeps a control character in a text field (if not, escaping cannot reach six bytes)."""
    idx = S.build_rows(tmp, [_r(0, ESCAPED * 8, RetractionNature="Retraction", OriginalPaperDOI="10.5555/c")])
    with Index(idx) as ix:
        title = ix.gather("10.5555/c").events[0]["title"]
    idx = S.build_rows(tmp / "doi", [_r(0, "", RetractionNature="Retraction", OriginalPaperDOI=LONG_DOI)])
    with Index(idx) as ix:
        events = ix.gather(LONG_DOI).events
    return {
        "control_characters_kept_in_text": ESCAPED in title,
        "two_byte_escapes_kept_in_doi": bool(events) and events[0]["original_doi"].endswith('"\\'),
    }


def at_default(tmp: Path, rho: float, intercept: int) -> dict[str, Any]:
    """A synthetic key whose lookup needs just over the default budget B: refused at B (no partial result); at the
    bytes it needs it succeeds, and its observation fits the bound rho * N + F and the blob limit."""
    budget = DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES
    one = measure("doi_match_with_secondary_pmid", "empty", 1, tmp / "one")
    per_key_row = one["needed"]  # one DOI row plus one PMID-only row
    k = budget // per_key_row + 2
    rows, doi, pmid = SHAPES["doi_match_with_secondary_pmid"](k, "")
    idx = S.build_rows(tmp / "big", rows)
    with Index(idx) as ix:
        need = needed(ix, doi, pmid)
        refused = False
        try:
            ix.gather_bounded(doi, pmid, budget_bytes=budget)
        except EvidenceBudgetExceeded:
            refused = True
        ev = ix.gather_bounded(doi, pmid, budget_bytes=need)
        size = len(canon(observation(ev)))
    return {
        "rows": len(rows),
        "needed": need,
        "needed_over_default": need > budget,
        "refused_at_default": refused,
        "events_at_needed": len(ev.events),
        "observation_bytes_at_needed": size,
        "within_rho_bound": size <= rho * need + intercept,
        "fits_blob_limit": size <= MAX_BLOB_BYTES,
    }


def pinned(index: Path) -> dict[str, Any]:
    """Every key of the pinned index: the largest bytes one lookup needs (sanity check of the default only)."""
    conn = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
    try:
        dois = {r[0] for r in conn.execute("SELECT original_doi FROM event WHERE original_doi IS NOT NULL")}
        dois |= {r[0] for r in conn.execute("SELECT notice_doi FROM event WHERE notice_doi IS NOT NULL")}
        pmids = {r[0] for r in conn.execute("SELECT original_pmid FROM event WHERE original_pmid IS NOT NULL")}
        pmids |= {r[0] for r in conn.execute("SELECT notice_pmid FROM event WHERE notice_pmid IS NOT NULL")}
        pairs = set(
            conn.execute(
                "SELECT original_doi, original_pmid FROM event "
                "WHERE original_doi IS NOT NULL AND original_pmid IS NOT NULL"
            )
        )
        rows = conn.execute(
            f"SELECT MIN(s), MAX(s), COUNT(*) FROM (SELECT {query._EVENT_BYTES} AS s "  # noqa: S608
            "FROM event e JOIN raw_record r ON r.ordinal = e.ordinal)"
        ).fetchone()
    finally:
        conn.close()
    best: dict[str, Any] = {"needed": -1}
    total = 0
    started = time.monotonic()
    biggest_observation = 0
    with Index(index) as ix:
        queries = [(d, None) for d in sorted(dois)] + [(None, p) for p in sorted(pmids)] + sorted(pairs)
        for doi, pmid in queries:
            need = needed(ix, doi, pmid)
            total += 1
            if need > best["needed"]:
                best = {"needed": need, "doi": doi, "pmid": pmid}
        ev = ix.gather(best["doi"], best["pmid"])
        biggest_observation = len(canon(observation(ev)))
        best["events"] = len(ev.events)
        best["observation_bytes"] = biggest_observation
        snapshot = ix.snapshot_id if hasattr(ix, "snapshot_id") else None
    return {
        "index": index.name,
        "snapshot_id": snapshot,
        "event_rows": rows[2],
        "event_row_stored_bytes_min_max": [rows[0], rows[1]],
        "lookups_measured": total,
        "seconds": round(time.monotonic() - started, 1),
        "largest_lookup": best,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out", default=str(Path(__file__).with_name("lookup_budget.json")))
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        esc = escaping_check(tmp / "esc")
        by_shape = shapes(tmp)
        rho_max = max(v["rho_observation_bytes_per_needed_byte"] for v in by_shape.values())
        f_max = max(v["intercept_bytes"] for v in by_shape.values())
        default = at_default(tmp / "default", rho_max, f_max)
    # Analytic bound: canonical JSON writes a stored text byte as at most 6 bytes (a control character as \u00XX),
    # and Stage 02 keeps control characters in text fields (``escaping``); every structural byte of a row is
    # measured above at a lower ratio. So no row costs more than 6 observation bytes per needed byte.
    rho_bound = max(6.0, rho_max)
    b_max = int((MAX_BLOB_BYTES - max(f_max, 0)) / rho_bound)
    selected = DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES
    peak_rate = max(v["gather_peak_per_needed_byte"] for v in by_shape.values())
    enc_rate = max(v["encode_peak_per_needed_byte"] for v in by_shape.values())
    pin = pinned(args.index)
    n_max = pin["largest_lookup"]["needed"]
    result = {
        "escaping": esc,
        "shapes": by_shape,
        "rho_max": rho_max,
        "rho_bound (analytic, >= rho_max)": rho_bound,
        "intercept_max_bytes": f_max,
        "MAX_BLOB_BYTES": MAX_BLOB_BYTES,
        "budget_max_from_blob_limit": b_max,
        "budget_max_from_blob_limit_mib": round(b_max / MIB, 3),
        "selected_budget": selected,
        "selected_budget_mib": selected / MIB,
        "selected_fits_blob_limit": rho_bound * selected + max(f_max, 0) <= MAX_BLOB_BYTES,
        "worst_observation_at_selected_bytes": round(rho_bound * selected + max(f_max, 0)),
        "blob_margin_at_selected": round(MAX_BLOB_BYTES / (rho_bound * selected + max(f_max, 0)), 2),
        "query_memory": {
            "gather_peak_per_needed_byte_max": peak_rate,
            "gather_peak_at_selected_bytes": round(peak_rate * selected),
            "encode_peak_per_needed_byte_max": enc_rate,
            "encode_peak_at_selected_bytes": round(enc_rate * selected),
        },
        "at_default_budget": default,
        "pinned": pin,
        "headroom_selected_over_pinned_max": round(selected / n_max, 2) if n_max > 0 else None,
    }
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "shapes"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
