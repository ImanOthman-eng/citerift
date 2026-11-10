"""Check the Stage 02 world abstraction (``stage02_abstraction``) against the real Stage 02 engine.

For each of the 192 worlds a synthetic Retraction Watch source is written (synthetic 10.5555 test prefix, never
real records), a real index is built with ``citerift.retraction.store.build`` and the three queries of a PAIR
candidate are run with the real ``Index.gather``. The results are mapped to the abstract values of the reference
model and compared with what the abstraction predicts:

- the lookup states of Q1(d), Q1(p) and Q2 (facts F-1, F-5, F-6);
- the witness bits and the co-naming bit, recomputed here from the real events by the rule of SPEC 6.5 (direct
  events only), which also checks F-5 and F-7 on every world;
- the projection shape of each lookup is within the Stage 02 contract (F-2, F-3, F-4);
- proposition P2 (kappa = INCOMPATIBLE iff Q2 is ambiguous_identity) on every world.

This module reads Stage 02 (an accepted engine); it never imports Stage 04 production code. It does not modify
Stage 02; the synthetic sources and indexes live in a temporary directory.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dt1_reference as R
import stage02_abstraction as A

from citerift.retraction.query import Index, projection_of
from citerift.retraction.source import parse_receipt
from citerift.retraction.store import build

HEADER = [
    "Record ID",
    "Title",
    "Subject",
    "Institution",
    "Journal",
    "Publisher",
    "Country",
    "Author",
    "URLS",
    "ArticleType",
    "RetractionDate",
    "RetractionDOI",
    "RetractionPubMedID",
    "OriginalPaperDate",
    "OriginalPaperDOI",
    "OriginalPaperPubMedID",
    "RetractionNature",
    "Reason",
    "Paywalled",
    "Notes",
]
D = "10.5555/s4.cand"
P = "4000001"


def _row(rid: int, od: str = "", op: str = "", nd: str = "", np_: str = "") -> dict[str, str]:
    out = {h: "" for h in HEADER}
    out.update(
        {
            "Record ID": str(rid),
            "Title": f"Synthetic title {rid}",
            "Journal": "Synthetic Journal",
            "Author": "A Tester",
            "RetractionDate": "3/12/2015 0:00",
            "OriginalPaperDate": "6/15/2010 0:00",
            "RetractionNature": "Retraction",
            "OriginalPaperDOI": od,
            "OriginalPaperPubMedID": op,
            "RetractionDOI": nd or f"10.5555/s4.notice.{rid}",
            "RetractionPubMedID": np_,
        }
    )
    return out


def rows_for(w: A.World) -> list[dict[str, str]]:
    rows = [_row(1, od="10.5555/s4.filler", op="4999999")]  # keeps every source non-empty and unrelated
    if w.coname:
        rows.append(_row(10, od=D, op=P))
    if w.d_null:
        rows.append(_row(11, od=D))
    if w.d_other:
        rows.append(_row(12, od=D, op="4000002"))
    if w.p_null:
        rows.append(_row(13, op=P))
    for k in range(w.p_other):
        rows.append(_row(20 + k, od=f"10.5555/s4.other.{k}", op=P))
    if w.nd:
        rows.append(_row(30, od="10.5555/s4.orig.nd", nd=D))
    if w.np:
        rows.append(_row(31, od="10.5555/s4.orig.np", np_=P))
    return rows


def _csv(rows: list[dict[str, str]]) -> bytes:
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=HEADER, lineterminator="\n")
    wr.writeheader()
    wr.writerows(rows)
    return "﻿".encode() + buf.getvalue().encode("utf-8")


def _receipt(data: bytes) -> Any:
    blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest()
    return parse_receipt(
        {
            "receipt_version": "1.0.0",
            "source_id": "retraction-watch",
            "repository": "https://example.invalid/s4/rw",
            "commit": "0" * 40,
            "path": "retraction_watch.csv",
            "url": "https://example.invalid/s4/rw/retraction_watch.csv",
            "expected_bytes": len(data),
            "expected_sha256": hashlib.sha256(data).hexdigest(),
            "git_blob_sha1": blob,
            "readme_generated_on": "2026-01-01",
            "acquired_at": "2026-01-01T00:00:00Z",
            "attribution": "Synthetic test data (10.5555 test prefix); not Retraction Watch records",
        }
    )


def abstract(ev: Any) -> R.Lookup:
    """Map a real gather result to the reference model's abstract lookup value."""
    proj = projection_of(ev)
    state = ev.state
    if proj is None:
        return (state, "none", False)
    st = proj["retraction_status"]
    status, value = st["status"], st["value"]
    reasons = proj["basis"].get("reasons", [])
    if status == "verified_fact":
        shape = f"vf:{value}" if value is not None else "vf:null"
    elif status == "conflicting":
        shape = "conf" if value is None else "conf:valued"
    elif status == "uncertain" and value is None:
        shape = {"notice_only": "unc:notice", "ambiguous_identity": "unc:ambiguous", "no_record": "unc:gap"}.get(
            state, "unc:bridge_only" if "BRIDGE_ONLY_SUPPORT" in reasons else "unc"
        )
    elif status == "uncertain" and value == "not_found_in_checked_sources" and state == "no_record":
        shape = "unc:not_found"
    elif status == "uncertain":
        shape = "unc:valued"
    else:
        shape = f"status:{status}"
    pmid_events = {e["event_id"] for e in ev.events if e.get("matched_by") == "pmid"}
    collision = any(
        i.get("code") == "PMID_ROLE_COLLISION" and pmid_events & set(i.get("event_ids", [])) for i in ev.issues
    )
    return (state, shape, bool(collision))


def witnesses(ev: Any, d: str, p: str) -> tuple[bool, bool]:
    """(witness present, co-naming event present) among the direct events, by the rule of SPEC 6.5."""
    wit = coname = False
    for e in ev.events:
        if e.get("linked_via") is not None:
            continue
        if e.get("matched_by") == "doi" and e["original_doi"] == d and e["original_pmid"] not in (p, None):
            wit = True
        if e.get("matched_by") == "pmid" and e["original_pmid"] == p and e["original_doi"] not in (d, None):
            wit = True
        if e["original_doi"] == d and e["original_pmid"] == p:
            coname = True
    return wit, coname


def check_world(w: A.World, tmp: Path) -> dict[str, Any]:
    data = _csv(rows_for(w))
    src = tmp / "source.csv"
    src.write_bytes(data)
    index_path = build(src, _receipt(data), tmp / "index").index_path
    with Index(index_path) as ix:
        qd, qp, q2 = ix.gather(doi=D), ix.gather(pmid=P), ix.gather(doi=D, pmid=P)
        events_fresh = all(a is not b for a in qd.events for b in q2.events)  # F-7: no shared event objects
    ad, ap, a2 = abstract(qd), abstract(qp), abstract(q2)
    wd, cd = witnesses(qd, D, P)
    wp, cp = witnesses(qp, D, P)
    w2, _ = witnesses(q2, D, P)
    real_sig = (ad[0], ap[0], a2[0], wd, wp, w2, cd or cp)
    model_sig = A.signature(w, True, True, True)
    problems = []
    if real_sig != model_sig:
        problems.append({"signature": {"real": real_sig, "model": model_sig}})
    for name, lk in (("Q1(d)", ad), ("Q1(p)", ap), ("Q2", a2)):
        if not R.well_formed(lk):
            problems.append({"projection_outside_contract": [name, lk]})
    kappa_incompatible = wd or wp or w2
    if kappa_incompatible != (a2[0] == "ambiguous_identity"):
        problems.append({"P2": [kappa_incompatible, a2[0]]})
    if not events_fresh:
        problems.append({"F-7": "event objects shared between queries"})
    case = R.Case("CITED", "PAIR", frozenset(), False, ad, ap, a2, wd, wp, w2, cd or cp)
    inv = A.invalid_reasons(case)
    if inv:
        problems.append({"abstraction_rejects_real_case": inv})
    dec = R.decide(case)
    return {
        "world": w.__dict__,
        "lookups": [list(ad), list(ap), list(a2)],
        "signature": list(real_sig),
        "decision": {"rule": dec["rule"], "class": dec["class"], "reasons": dec["reasons"]},
        "problems": problems,
    }


CASES = Path(__file__).resolve().parents[1] / "stage02" / "cases"
CASE_FIELDS = {
    "id": "Record ID",
    "nature": "RetractionNature",
    "od": "OriginalPaperDOI",
    "op": "OriginalPaperPubMedID",
    "nd": "RetractionDOI",
    "np": "RetractionPubMedID",
    "rd": "RetractionDate",
    "pd": "OriginalPaperDate",
}


def probe_stage02_cases(tmp: Path) -> dict[str, Any]:
    """Run the frozen Stage 02 policy and tension cases (synthetic rows) through the real gather and record which
    abstract lookup values the real engine produces; each must be within the Stage 02 contract. Cases that need a
    Crossref bundle, supersessions or an unavailable index are skipped and counted."""
    seen: dict[str, list[str]] = {}
    outside: list[Any] = []
    skipped: list[str] = []
    ran = 0
    for name in ("policy_cases.json", "tension_cases.json"):
        for case in json.loads((CASES / name).read_text(encoding="utf-8"))["cases"]:
            if case.get("crossref") or case.get("supersessions") or case.get("index_unavailable"):
                skipped.append(case["id"])
                continue
            rows = [_row(1, od="10.5555/s4.filler", op="4999999")]
            for r in case["rows"]:
                base = {
                    h: v
                    for h, v in _row(0).items()
                    if h not in CASE_FIELDS.values() or h in ("RetractionDate", "OriginalPaperDate", "RetractionNature")
                }
                base.update({CASE_FIELDS[k]: v for k, v in r.items()})
                base["Title"] = f"Synthetic title {r['id']}"
                rows.append(base)
            data = _csv(rows)
            sub = tmp / f"case-{case['id']}"
            sub.mkdir()
            (sub / "source.csv").write_bytes(data)
            index_path = build(sub / "source.csv", _receipt(data), sub / "index").index_path
            q = case["query"]
            with Index(index_path) as ix:
                lk = abstract(ix.gather(doi=q.get("doi"), pmid=q.get("pmid")))
            ran += 1
            seen.setdefault("|".join(str(x) for x in lk), []).append(case["id"])
            if not R.well_formed(lk) and lk[0] != "invalid_query":
                outside.append([case["id"], list(lk)])
    # Extra probes for values the frozen cases do not show: a PMID role collision (one PMID for the original and
    # its notice) and a reinstatement, alone and after a retraction (no supersession link is ever passed by Stage 04).
    reinstated = {
        **_row(41, od="10.5555/s4.r2"),
        "RetractionNature": "Reinstatement",
        "RetractionDate": "5/12/2016 0:00",
    }
    extra = {
        "X-collision-pmid": ([_row(40, od="10.5555/s4.c1", op="4100001", np_="4100001")], {"pmid": "4100001"}),
        "X-collision-doi": ([_row(40, od="10.5555/s4.c1", op="4100001", np_="4100001")], {"doi": "10.5555/s4.c1"}),
        "X-reinstatement-alone": (
            [{**_row(41, od="10.5555/s4.r1"), "RetractionNature": "Reinstatement"}],
            {"doi": "10.5555/s4.r1"},
        ),
        "X-retraction-then-reinstatement": ([_row(42, od="10.5555/s4.r2"), reinstated], {"doi": "10.5555/s4.r2"}),
    }
    for pid, (rows, q) in extra.items():
        data = _csv([_row(1, od="10.5555/s4.filler", op="4999999"), *rows])
        sub = tmp / f"probe-{pid}"
        sub.mkdir()
        (sub / "source.csv").write_bytes(data)
        index_path = build(sub / "source.csv", _receipt(data), sub / "index").index_path
        with Index(index_path) as ix:
            lk = abstract(ix.gather(doi=q.get("doi"), pmid=q.get("pmid")))
        ran += 1
        seen.setdefault("|".join(str(x) for x in lk), []).append(pid)
        if not R.well_formed(lk):
            outside.append([pid, list(lk)])
    return {
        "cases_run": ran,
        "cases_skipped": sorted(skipped),
        "values_seen": dict(sorted(seen.items())),
        "outside_contract": outside,
    }


def run(out: Path | None = None) -> dict[str, Any]:
    started = time.monotonic()
    results = []
    with tempfile.TemporaryDirectory(prefix="s4-conformance-") as tmp:
        for i, w in enumerate(A.worlds()):
            sub = Path(tmp) / f"w{i:03d}"
            sub.mkdir()
            results.append(check_world(w, sub))
        probes = probe_stage02_cases(Path(tmp))
    seen_values = sorted({tuple(lk) for r in results for lk in r["lookups"]})
    seen_sigs = {tuple(r["signature"]) for r in results}
    full_avail_sigs = {A.signature(w, True, True, True) for w in A.worlds()}
    summary = {
        "worlds": len(results),
        "worlds_with_problems": sum(1 for r in results if r["problems"]),
        "problems": [r for r in results if r["problems"]][:10],
        "distinct_signatures_seen": len(seen_sigs),
        "distinct_signatures_model_all_available": len(full_avail_sigs),
        "signatures_equal": seen_sigs == full_avail_sigs,
        "abstract_values_seen": [list(v) for v in seen_values],
        "rules_seen": sorted({r["decision"]["rule"] for r in results}),
        "classes_seen": sorted({str(r["decision"]["class"]) for r in results}),
        "stage02_case_probes": probes,
        "elapsed_s": round(time.monotonic() - started, 1),
    }
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "stage02_conformance.json").write_text(
            json.dumps({"summary": summary, "worlds": results}, indent=1, sort_keys=True) + "\n"
        )
    return summary


if __name__ == "__main__":
    s = run(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    print(json.dumps({k: v for k, v in s.items() if k != "abstract_values_seen"}, indent=1))
    bad = s["worlds_with_problems"] or not s["signatures_equal"] or s["stage02_case_probes"]["outside_contract"]
    raise SystemExit(1 if bad else 0)
