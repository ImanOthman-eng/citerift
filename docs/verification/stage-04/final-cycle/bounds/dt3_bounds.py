"""Final corrective cycle (owner decision D-083, items 8 and 13): the record, journal and blob bounds of engine 0.4.0
(table dt-3, Stage 04 schemas 5.0.0), with reviewer findings D-05, D-07, E-07, E-08 and E-09 of the final cycle.

The D-055 derivation (``review/step7/d055/bounds.py``, kept unchanged as the dt-2 record) is run here with the dt-3
maximal builders (``storage_bounds.py`` and ``part_ceiling.py`` of this directory, adapted copies of the historical
generators, which stay as they were at ``6663314``; D-07). Then:

1. **Evidence items (D-05, E-08).** dt-3 adds two evidence kinds. ``cited_bibliography`` (one per unit at most, built
   at the bib-1 code bound: 4,096 code points, 134 values, every code point 6 bytes of canonical JSON) raises the
   largest evidence item ``E_max``. ``lookup_record`` items, with the ``lookup_event`` item each refers to, are made
   for *every* event of a claim's deciding lookup (D-13a and D-14 claims; ``adapters/detector.py``), so their number
   is not bounded per claim as dt-2's ``W = 4`` witness events were: it is at most two items per event of every
   distinct deciding lookup observation (item ids are ``H(observation, pointer, kind)``, so a lookup shared by
   several candidates gives its items once). Both kinds are built by DETECT only, with value null, one ref and the
   pointer ``/events/k`` or ``/records/k``; their legal size is measured at the largest ``k``. ``E_L``, the events of
   one lookup, is at most the lookup evidence budget (16 MiB, schema maximum) over the fewest stored bytes charged
   for one event in the D-048 shape measurement (``closure/lookup_budget.json``, empty text fields). The journal
   bound is computed with these counts and sizes; ``E_L_at_journal_limit`` is the number of events per deciding
   lookup at which the bound would reach ``MAX_JOURNAL_BYTES`` (a run that would pass it is refused at the append:
   ``JOURNAL_TOO_LARGE``, fail closed).
2. **LOOKUP observation (E-07).** Observation v3 repeats each event's title and journal in ``records``. The
   observation bytes per charged byte (rho) are measured on the production ``observe`` with the D-048 shapes, with
   4,096 control characters (6 bytes of canonical JSON each, the D-048 convention) in each combination of Title,
   Journal and Author. No analytic bound is claimed for v3: how many times a title is repeated depends on the
   lookup's shape (a notice-only lookup repeats it more often), so the bound is the measured maximum with the largest
   intercept; an observation above the blob limit is ``BLOB_TOO_LARGE``, a ``STORAGE_ERROR`` (fail closed).
3. **Per-claim evidence set.** A D-13a or D-14 claim names the two items of every event of its deciding lookup: the
   evidence-set row is bounded per claim, not by every item of the run.
4. **Candidate inputs (E-09).** Schema 2.0.0 adds ``bibliography`` to every unit. Its increment is bounded by the
   source: a cleaned value is never longer than its source text, a template's own description leaves out every
   nested template (``strip_code``), so every source code point is in at most one description: at most
   ``6 * MAX_SOURCE_BYTES`` bytes of values plus the field names and nulls of 20,000 units. The terms of Step 8 (units,
   candidates, observation keys, queries) have no derived bound (a gap since Step 8, stated): an overflow is
   ``BLOB_TOO_LARGE``, a ``STORAGE_ERROR`` (fail closed).

Usage: ``uv run python dt3_bounds.py [--out bounds.json]`` (with the provenance of N-01).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
HIST = REPO / "docs" / "verification" / "stage-04" / "review" / "step7"
sys.path[:0] = [str(REPO / "tests" / "stage04"), str(HERE.parent)]

from fc_provenance import finish, start  # noqa: E402

from citerift.investigation import batches  # noqa: E402
from citerift.investigation.adapters.lookup import observe  # noqa: E402
from citerift.investigation.blobs import MAX_BLOB_BYTES  # noqa: E402
from citerift.investigation.canonical import canon  # noqa: E402
from citerift.investigation.journal import MAX_JOURNAL_BYTES  # noqa: E402
from citerift.retraction.query import Index  # noqa: E402
from citerift.wiki import capture as stage03_capture  # noqa: E402


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D055 = _load("d055_bounds", HIST / "d055" / "bounds.py")
LB = _load("closure_lookup_budget", HIST / "closure" / "lookup_budget.py")
SB = _load("fc_storage_bounds", HERE / "storage_bounds.py")
CEIL = _load("fc_part_ceiling", HERE / "part_ceiling.py")
# The D-055 derivation runs with the dt-3 builders (D-07): its module globals are rebound, its code is unchanged.
D055.SB, D055.SHA, D055.CEIL = SB, SB.SHA, CEIL
D055.D053.SB, D055.D053.SHA = SB, SB.SHA

LOOKUP_BUDGET_MAX = 16 * 1024 * 1024  # common.schema.json lookup_evidence_budget_bytes maximum (D-048)
TEXT_COMBINATIONS = (("Title",), ("Journal",), ("Author",), ("Title", "Journal"), ("Title", "Journal", "Author"))


def record_kinds() -> dict[str, Any]:
    return D055.record_kinds()


def lookup_v3(tmp: Path) -> dict[str, Any]:
    """rho of observation v3 over the D-048 shapes (n = 50 and 200), each text combination at 4,096 control
    characters; the fewest charged bytes per event (empty text) from the D-048 record."""
    out: dict[str, Any] = {}
    for shape, build in LB.SHAPES.items():
        for fields in TEXT_COMBINATIONS:
            pts = []
            for n in (50, 200):
                rows, doi, pmid = build(n, "")
                for r in rows:
                    r.update({f: LB.ESCAPED * 4096 for f in fields})
                idx = LB.S.build_rows(tmp / f"{shape}-{'-'.join(fields)}-{n}", rows)
                with Index(idx) as ix:
                    need = LB.needed(ix, doi, pmid)
                    pts.append((need, len(canon(observe(ix, {}, doi, pmid, need)))))
            (n1, o1), (n2, o2) = pts
            rho = (o2 - o1) / (n2 - n1)
            out[f"{shape}/{'+'.join(fields)}"] = {
                "points": pts,
                "rho": round(rho, 4),
                "intercept_bytes": round(o1 - rho * n1),
            }
    rho_max = max(v["rho"] for v in out.values())
    rho = rho_max
    d048 = json.loads((HIST / "closure" / "lookup_budget.json").read_text(encoding="utf-8"))
    intercept = max(d048["intercept_max_bytes"], *(v["intercept_bytes"] for v in out.values()))
    worst = round(rho * LOOKUP_BUDGET_MAX + intercept)
    per_event = min(
        v["at_200"]["needed"] / v["at_200"]["events"]
        for k, v in d048["shapes"].items()
        if k.endswith("/empty") and v["at_200"]["events"] > 0
    )
    return {
        "shapes": out,
        "rho_max_measured": rho_max,
        "rho_bound": rho,
        "rho_bound_note": "measured maximum over the D-048 shapes at 4,096-character fields; no analytic bound for v3",
        "intercept_max_bytes": intercept,
        "budget_max_schema": LOOKUP_BUDGET_MAX,
        "worst_observation_bytes": worst,
        "within_blob_limit": worst <= MAX_BLOB_BYTES,
        "blob_margin": round(MAX_BLOB_BYTES / worst, 2),
        "budget_max_from_blob_limit": int((MAX_BLOB_BYTES - intercept) / rho),
        "fewest_charged_bytes_per_event": round(per_event, 1),
        "E_L_events_per_lookup_max": int(LOOKUP_BUDGET_MAX // per_event),
    }


def per_event_item(kind: str, k: int) -> int:
    root = "/records/" if kind == "lookup_record" else "/events/"
    item = {"evidence_id": SB.SHA, "observation": SB.SHA, "pointer": f"{root}{k}", "kind": kind}
    return int(batches.item_bytes({**item, "refs": [SB.SHA], "value": None}))


def evidence_census(e_l: int, lookups: int, units: int) -> dict[str, Any]:
    d053 = json.loads((HIST / "d053" / "part_ceiling.json").read_text(encoding="utf-8"))
    sizes = dict(d053["rule_1_largest_item"]["item_bytes_by_kind_at_schema_maxima"])
    for kind in ("cited_bibliography", "lookup_record"):
        sizes[kind] = int(batches.item_bytes(SB._evidence(kind)))
    counts = {k: v for k, v in d053["rule_5_record_count"]["evidence_items_per_run_at_caps"].items()}
    witness = counts.pop("lookup_event (W = 4 per claim)")
    e_max = max(sizes.values())
    groups = {
        # every dt-2 kind at the dt-3 E_max (the d053 census; W = 4 witness events per claim kept for dt-2 claims)
        "dt-2 kinds (d053 census)": {"items": sum(counts.values()) + witness, "item_bytes": e_max},
        "cited_bibliography (one per unit)": {"items": units, "item_bytes": e_max},
        "lookup_event + lookup_record (two per event of every deciding lookup)": {
            "items": 2 * lookups * e_l,
            "item_bytes": max(per_event_item("lookup_event", e_l), per_event_item("lookup_record", e_l)),
        },
    }
    return {
        "item_bytes_by_kind_at_schema_maxima": sizes,
        "E_max": e_max,
        "E_L": e_l,
        "deciding_lookups_max": lookups,
        "groups": groups,
        "entry_bytes": sum(g["items"] * g["item_bytes"] for g in groups.values()),
        "items": sum(g["items"] for g in groups.values()),
    }


def journal(kinds: dict[str, Any], census: dict[str, Any]) -> dict[str, Any]:
    """The D-055 journal bound with the dt-3 evidence census: the D-055 rows of lookup references and candidate
    results unchanged, the evidence row recomputed from the census (same rigorous closed-part bound, SPEC 8.8 (d))."""
    sizes = D055.entry_sizes()
    sizes["maximal"]["evidence item"] = census["E_max"]
    j = D055.journal(kinds, sizes)
    c, env = batches.MAX_PART_BYTES, batches.BATCH_ENVELOPE
    rmax = j["largest_record_bytes_with_newline"]["evidence_batch_recorded"]
    per_closed = (c - census["E_max"] - env) // 2
    n = math.ceil(census["entry_bytes"] / per_closed) + 2
    row = {"entries": census["items"], "entry_bytes": census["entry_bytes"], "batch_records": n}
    row["record_bytes"] = n * rmax
    m = j["maximal"]
    m["batch_records_one_attempt_each_step"]["evidence item"] = row
    m["content_bytes_one_attempt_each_step"] = sum(
        r["record_bytes"] for r in m["batch_records_one_attempt_each_step"].values()
    )
    m["journal_bytes"] = j["fixed_total_bytes"] + j["A_max"] * m["content_bytes_one_attempt_each_step"]
    m["fraction_of_limit"] = round(m["journal_bytes"] / MAX_JOURNAL_BYTES, 5)
    m["headroom_factor"] = round(MAX_JOURNAL_BYTES / m["journal_bytes"], 1)
    m["proven_within_limit"] = m["journal_bytes"] <= MAX_JOURNAL_BYTES
    j["entries_per_run"]["evidence item"] = census["items"]
    j["evidence_census_dt3"] = census
    # Events per deciding lookup at which the maximal journal would reach the limit (all else at its maximum).
    other = m["journal_bytes"] - j["A_max"] * row["record_bytes"]
    per_event_bytes = (
        2
        * census["deciding_lookups_max"]
        * census["groups"]["lookup_event + lookup_record (two per event of every deciding lookup)"]["item_bytes"]
    )
    base = census["entry_bytes"] - census["E_L"] * per_event_bytes
    room = (MAX_JOURNAL_BYTES - other) / (j["A_max"] * rmax) - 2
    j["E_L_at_journal_limit"] = int((room * per_closed - base) / per_event_bytes)
    return j


def blobs(j: dict[str, Any], lk: dict[str, Any], census: dict[str, Any]) -> dict[str, Any]:
    rows = D055.blobs(j)
    c = batches.MAX_PART_BYTES
    sha_item = len(canon([SB.SHA, SB.SHA])) - len(canon([SB.SHA]))
    rows["LOOKUP observation (D-048)"] = {
        "bound_bytes": lk["worst_observation_bytes"],
        "why": "observation v3 (E-07): rho_bound x the 16 MiB schema maximum of the budget + the largest intercept",
        "basis": "measured, not proven: rho_bound is the measured maximum over the D-048 shapes (no analytic bound for "
        "v3; reviewer findings E-07 and F); above the blob limit the observation is BLOB_TOO_LARGE (fail closed)",
    }
    rows["evidence batch"] = {
        "bound_bytes": max(c, census["E_max"] + batches.BATCH_ENVELOPE),
        "why": "SPEC 8.8: a batch is cut at MAX_PART_BYTES; the largest legal dt-3 item fits one",
    }
    rows["evidence set (one claim)"] = {
        "bound_bytes": (2 * census["E_L"] + 64) * sha_item + 256,
        "why": "a D-13a or D-14 claim: two items per event of its deciding lookup plus at most 64 others",
    }
    manifest = rows["report manifest"]["bound_bytes"]
    extra_batches = math.ceil(census["entry_bytes"] / c) + 2
    rows["report manifest"] = {
        "bound_bytes": manifest + extra_batches * len(canon({"batch": SB.SHA, "count": SB.MAXINT})),
        "why": "the D-053 bound plus one reference per evidence batch of the dt-3 census",
    }
    bib = 6 * stage03_capture.MAX_SOURCE_BYTES + 20000 * len(
        canon({"bibliography": {k: None for k in ("titles", "authors", *SB.SINGLE_FIELDS)}})
    )
    rows["candidate inputs: bibliography increment of schema 2.0.0 (E-09)"] = {
        "bound_bytes": bib,
        "why": "every source code point is in at most one description (strip_code leaves out nested templates; "
        "cleaning never lengthens), at most 6 bytes each, plus field names and nulls of 20,000 units; the Step 8 "
        "terms of the blob have no derived bound (stated gap; an overflow is BLOB_TOO_LARGE, fail closed)",
    }
    for r in rows.values():
        r["within_limit"] = r["bound_bytes"] <= MAX_BLOB_BYTES
        r["fraction_of_limit"] = round(r["bound_bytes"] / MAX_BLOB_BYTES, 4)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "bounds.json")
    args = ap.parse_args()
    prov = start(Path(__file__))
    with tempfile.TemporaryDirectory() as d:
        lk = lookup_v3(Path(d))
    kinds = record_kinds()
    caps = D055.journal(kinds, D055.entry_sizes())["stage03_caps"]
    lookups = int(D055.journal(kinds, D055.entry_sizes())["entries_per_run"]["lookup reference"])
    census = evidence_census(lk["E_L_events_per_lookup_max"], lookups, caps["units (max_refs)"])
    j = journal(kinds, census)
    b = blobs(j, lk, census)
    result = {
        "decision": "D-083 (final corrective cycle); derivation of D-055 with the dt-3 builders",
        "journal_format": D055.JOURNAL_FORMAT,
        "report_version": D055.report.REPORT_VERSION,
        "limits": {
            "MAX_RECORD_BYTES": D055.MAX_RECORD_BYTES,
            "MAX_JOURNAL_BYTES": MAX_JOURNAL_BYTES,
            "MAX_BLOB_BYTES": MAX_BLOB_BYTES,
            "MAX_PART_BYTES": batches.MAX_PART_BYTES,
        },
        "record_kinds_max_bytes": kinds,
        "largest_record_bytes": max(v["bytes"] for v in kinds.values()),
        "record_limit_proven": all(v["bytes"] <= D055.MAX_RECORD_BYTES for v in kinds.values()),
        "journal": j,
        "journal_limit_proven": j["maximal"]["proven_within_limit"],
        "lookup_observation_v3": lk,
        "blobs": b,
        "blob_limit_proven_except_ACQUIRE_and_LOOKUP_observations": all(
            r["within_limit"] for k, r in b.items() if not k.startswith(("ACQUIRE", "LOOKUP observation"))
        ),
        "LOOKUP_observation_within_limit_measured": b["LOOKUP observation (D-048)"]["within_limit"],
        "ACQUIRE_observation": "conditional on the Step 8 representation (IF-7, see its row)",
        "total_storage": D055.total(j, b),
        "provenance": prov,
    }
    finish(prov, Path(__file__))
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {
        "journal_maximal": j["maximal"]["journal_bytes"],
        "headroom": j["maximal"]["headroom_factor"],
        "E_L": census["E_L"],
        "E_L_at_journal_limit": j["E_L_at_journal_limit"],
        "E_max": census["E_max"],
        "rho": lk["rho_bound"],
        "lookup_worst": lk["worst_observation_bytes"],
        "blobs_ok": result["blob_limit_proven_except_ACQUIRE_and_LOOKUP_observations"],
        "lookup_ok_measured": result["LOOKUP_observation_within_limit_measured"],
        "largest_record": result["largest_record_bytes"],
    }
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
