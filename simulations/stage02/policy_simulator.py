"""Stage 02 prebuild simulator: an executable reference model of the lookup, projection and tension policies.

Written before the engine (SPECIFICATION.md sections 6, 7, 10.3, 11) and kept separate from
``src/citerift/retraction``: it imports nothing from it. It runs the frozen synthetic cases in
``cases/policy_cases.json`` and ``cases/tension_cases.json`` and compares its outputs with the hand-written
expectations there. The engine is later tested against the same expectations, so a disagreement between
the two implementations shows up as a failed case in one of them.

Run: python simulations/stage02/policy_simulator.py --output sim.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
TYPES = {
    "Retraction": "retracted",
    "Expression of concern": "expression_of_concern",
    "Correction": "correction",
    "Reinstatement": "reinstated",
}
CROSSREF_TYPES = {
    "retraction": "retracted",
    "correction": "correction",
    "corrigendum": "correction",
    "erratum": "correction",
    "expression_of_concern": "expression_of_concern",
    "reinstatement": "reinstated",
}
RW = "retraction-watch"
DEFAULTS = {"op": "", "np": "", "nd": "", "od": "", "rd": "3/12/2015 0:00", "pd": "6/15/2010 0:00"}


def doi_key(raw: str) -> str | None:
    """Bare DOI only (the cases use no URL forms). ASCII case folding, no Unicode changes."""
    s = raw.strip()
    if s in ("", "unavailable", "Unavailable"):
        return None
    if not re.fullmatch(r"10\.[0-9]{4,9}(\.[0-9]+)*/.+", s, flags=re.ASCII | re.DOTALL):
        return None
    if any(unicodedata.category(c) in ("Cc", "Cf", "Cs", "Zs", "Zl", "Zp") for c in s):
        return None
    return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in s)


def doi_invalid_raw(raw: str) -> bool:
    s = raw.strip()
    return s not in ("", "unavailable", "Unavailable") and doi_key(s) is None


def pmid_key(raw: str) -> str | None:
    s = raw.strip()
    if not re.fullmatch(r"[1-9][0-9]{0,8}", s, flags=re.ASCII):
        return None
    return s


def pmid_invalid_raw(raw: str) -> bool:
    s = raw.strip()
    return s != "" and set(s) != {"0"} and pmid_key(s) is None


@dataclass
class Date:
    reported: str | None
    lo: dt.date | None
    hi: dt.date | None


def parse_date(raw: str) -> Date:
    m = re.fullmatch(r"([0-9]{1,2})/([0-9]{1,2})/([0-9]{4}) ([0-9]{1,2}):([0-9]{2})(:[0-9]{2} (AM|PM))?", raw)
    if not m:
        return Date(None, None, None)
    try:
        day = dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    except ValueError:
        return Date(None, None, None)
    if day.day == 1:
        return Date(day.isoformat(), None, None)
    return Date(day.isoformat(), day, day)


@dataclass
class Assertion:
    aid: str
    origin: str
    type: str | None  # None: untyped relation
    notice: str | None
    anchor: str
    event_id: str | None = None  # RW events only
    date: Date | None = None
    bridged: bool = False
    notice_ambiguous: bool = False


@dataclass
class Evidence:
    state: str
    identity: str
    rw: list[Assertion] = field(default_factory=list)
    crossref: list[Assertion] = field(default_factory=list)
    supersessions: list[tuple[str, str]] = field(default_factory=list)
    relevant_gap: bool = False
    sources: tuple[str, ...] = (RW,)
    anchor: str | None = None
    role: str = "none"


def build_rows(case: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for i, r in enumerate(case["rows"], start=1):
        row = {**DEFAULTS, **r, "ord": i}
        row["accepted"] = row["nature"] in TYPES
        row["d"] = doi_key(row["od"])
        row["p"] = pmid_key(row["op"])
        nd, npm = doi_key(row["nd"]), pmid_key(row["np"])
        if nd is not None and nd == row["d"]:
            nd = None
        if npm is not None and npm == row["p"]:
            npm = None
        row["n"] = f"doi:{nd}" if nd else (f"pmid:{npm}" if npm else None)
        rows.append(row)
    originals = {r["d"] for r in rows if r["accepted"] and r["d"]}
    for r in rows:
        r["n_amb"] = r["n"] is not None and r["n"].startswith("doi:") and r["n"][4:] in originals
        r["anchor"] = f"doi:{r['d']}" if r["d"] else (f"pmid:{r['p']}" if r["p"] else f"rec:{r['ord']}")
    return rows


def rw_assertion(r: dict[str, Any], bridged: bool = False) -> Assertion:
    return Assertion(
        aid=f"ev-{r['ord']}",
        origin=RW,
        type=TYPES[r["nature"]],
        notice=r["n"],
        anchor=r["anchor"],
        event_id=r["id"] + "#" + str(r["ord"]),
        date=parse_date(r["rd"]),
        bridged=bridged,
        notice_ambiguous=r["n_amb"],
    )


def gather(case: dict[str, Any]) -> Evidence:
    rows = build_rows(case)
    acc = [r for r in rows if r["accepted"]]
    q = case["query"]
    qd = doi_key(q["doi"]) if "doi" in q else None
    qp = pmid_key(q["pmid"]) if "pmid" in q else None
    if ("doi" in q and qd is None) or ("pmid" in q and qp is None):
        return Evidence("invalid_query", "none", sources=())
    if case.get("index_unavailable"):
        return Evidence("unavailable", "none", sources=())
    od = [r for r in acc if qd and r["d"] == qd]
    opm = [r for r in acc if qp and r["p"] == qp]
    notice = [r for r in acc if (qd and r["n"] == f"doi:{qd}") or (qp and r["n"] == f"pmid:{qp}")]
    ev = Evidence("no_record", "none")
    matched: list[tuple[dict[str, Any], bool]] = []
    if qd and qp:
        compatible = all(r["p"] in (qp, None) for r in od) and all(r["d"] in (qd, None) for r in opm)
        if not compatible:
            ev.state, ev.identity = "ambiguous_identity", "ambiguous"
            ev.rw = [rw_assertion(r) for r in {r["ord"]: r for r in od + opm}.values()]
            return ev
        matched = [(r, False) for r in od] + [(r, r["d"] is None) for r in opm if r not in od]
        ev.anchor = f"doi:{qd}"
    elif qd:
        matched = [(r, False) for r in od]
        secondary = {r["p"] for r in od} - {None}
        if len(secondary) == 1:
            q2 = secondary.pop()
            matched += [(r, True) for r in acc if r["p"] == q2 and r["d"] is None]
        ev.anchor = f"doi:{qd}"
    else:
        dois = {r["d"] for r in opm} - {None}
        if len(dois) > 1:
            ev.state, ev.identity = "ambiguous_identity", "ambiguous"
            ev.rw = [rw_assertion(r) for r in opm]
            return ev
        matched = [(r, False) for r in opm]
        if dois:
            d2 = dois.pop()
            matched += [(r, True) for r in acc if r["d"] == d2 and r["p"] is None]
            ev.anchor = f"doi:{d2}"
        else:
            ev.anchor = f"pmid:{qp}"
    if matched:
        ev.state = "matched"
        ev.identity = "bridged" if any(b for _, b in matched) else "exact"
        ev.rw = [rw_assertion(r, b) for r, b in matched]
        ev.role = "original_and_notice" if notice else "original"
        anchors = {r["anchor"] for r, _ in matched}
        sup = {(f"ev-{a}", f"ev-{b}") for a, b in case.get("supersessions", [])}
        id_to_ord = {r["id"]: r["ord"] for r in rows}
        ev.supersessions = [(f"ev-{id_to_ord[a]}", f"ev-{id_to_ord[b]}") for a, b in case.get("supersessions", [])]
        del sup
        for entry in case.get("crossref", []):
            ok = doi_key(entry["original"])
            if ok is None or f"doi:{ok}" not in anchors:
                continue
            for j, u in enumerate(entry["updated_by"]):
                nk = doi_key(u["DOI"])
                origin = RW if u.get("source") == RW else (u.get("source") or "unknown")
                ev.crossref.append(
                    Assertion(
                        aid=f"cr-{ok}-{j}",
                        origin=origin,
                        type=CROSSREF_TYPES.get(u["type"]),
                        notice=f"doi:{nk}" if nk and nk != ok else None,
                        anchor=f"doi:{ok}",
                    )
                )
        return ev
    if notice:
        ev.state, ev.role = "notice_only", "notice"
        ev.rw = [rw_assertion(r) for r in notice]
        return ev
    keys = [k for k in (qd, qp) if k]
    for r in rows:
        raw_fields = [r["od"], r["op"], r["nd"], r["np"]]
        if not r["accepted"] and any(k in f.lower() for k in keys for f in raw_fields):
            ev.relevant_gap = True
        invalid = [r["od"]] if doi_invalid_raw(r["od"]) else []
        invalid += [r["nd"]] if doi_invalid_raw(r["nd"]) else []
        invalid += [r["op"]] if pmid_invalid_raw(r["op"]) else []
        invalid += [r["np"]] if pmid_invalid_raw(r["np"]) else []
        if any(k in f.lower() for k in keys for f in invalid):
            ev.relevant_gap = True
    return ev


def before(a: Date | None, b: Date | None) -> bool:
    return bool(a and b and a.hi and b.lo and a.hi < b.lo)


def reduce(ev: Evidence) -> dict[str, Any]:
    """Projection policy of SPECIFICATION.md 11.1 (reference implementation)."""
    out: dict[str, Any] = {"state": ev.state, "status": None, "value": None, "date_status": None, "date_value": None}
    out["reasons"] = []
    out["alternatives"] = []
    out["support_observations"] = 0
    out["support_origins"] = []
    out["identity"] = ev.identity
    out["notice_links"] = sorted({a.notice for a in ev.rw if a.notice} if ev.state == "matched" else set())
    out["definite_orderings"] = []
    if ev.state == "invalid_query":
        return out
    if ev.state == "unavailable" or not ev.sources:
        out.update(state="unavailable", status="unavailable", identity="none", notice_links=[])
        out["reasons"] = ["NO_SOURCE_IN_VIEW"] if ev.state != "unavailable" else ["INDEX_UNAVAILABLE"]
        return out
    if ev.state == "ambiguous_identity":
        out.update(status="uncertain", reasons=["IDENTITY_AMBIGUOUS"])
        return out
    if ev.state == "notice_only":
        out.update(status="uncertain", reasons=["NOTICE_ONLY"])
        return out
    if ev.state == "no_record":
        if ev.relevant_gap:
            out.update(status="uncertain", reasons=["COVERAGE_GAP_RELEVANT_ROWS"])
        else:
            out.update(
                status="uncertain", value="not_found_in_checked_sources", reasons=["NOT_FOUND_IN_CHECKED_SOURCES"]
            )
        return out
    typed = [a for a in ev.rw + ev.crossref if a.type is not None]
    props: dict[str, set[str]] = {}
    for a in typed:
        props.setdefault(a.notice or a.aid, set()).add(a.type or "")
    conflict = {k for k, v in props.items() if len(v) > 1}
    clear = [a for a in typed if (a.notice or a.aid) not in conflict]
    rw_events = ev.rw
    out["definite_orderings"] = sorted(
        [a.aid, b.aid] for a in rw_events for b in rw_events if a is not b and before(a.date, b.date)
    )
    types = {a.type for a in typed}
    reins = [a for a in rw_events if a.type == "reinstated"]
    status = value = None
    reasons: list[str] = []
    if reins and types - {"reinstated"}:
        by_id = {a.aid: a for a in rw_events}
        linked = {}
        for r_id, t_id in ev.supersessions:
            if r_id in by_id and t_id in by_id and before(by_id[t_id].date, by_id[r_id].date):
                linked[r_id] = t_id
        superseded = set(linked.values())
        rest_retractions = [a for a in typed if a.type == "retracted" and a.aid not in superseded]
        if all(r.aid in linked for r in reins) and not rest_retractions:
            status, value = "verified_fact", "reinstated"
        else:
            status, reasons = "uncertain", ["REINSTATEMENT_UNLINKED"]
    elif any(a.type == "retracted" for a in clear):
        status, value = "verified_fact", "retracted"
        reasons = ["SOURCE_RECORDED_RETRACTION"] + (["CONFLICT_NOT_MATERIAL"] if conflict else [])
    elif conflict:
        status, reasons = "conflicting", ["SOURCE_TYPE_CONFLICT"]
        out["alternatives"] = sorted({t for k in conflict for t in props[k]})
    else:
        ctypes = {a.type for a in clear}
        if len(ctypes) == 1:
            status, value = "verified_fact", ctypes.pop()
        else:
            status, reasons = "uncertain", ["MIXED_CURRENT_EFFECT"]
    out.update(status=status, value=value, reasons=reasons)
    if value is not None:
        support = [a for a in clear if a.type == value]
        out["support_observations"] = len(support)
        out["support_origins"] = sorted({a.origin for a in support})
    if value == "retracted":
        dates = [a.date for a in clear if a.type == "retracted" and a.origin == RW and a.event_id is not None]
        if not dates:
            out.update(date_status="uncertain", date_value=None)
            out["reasons"].append("DATE_NOT_IN_CHECKED_SOURCES")
        elif any(d is None or d.reported is None for d in dates):
            out.update(date_status="uncertain", date_value=None)
            out["reasons"].append("DATE_UNKNOWN")
        elif len({d.reported for d in dates if d}) > 1:
            out.update(date_status="uncertain", date_value=None)
            out["reasons"].append("MULTIPLE_RETRACTION_DATES")
        else:
            d0 = dates[0] or Date(None, None, None)
            if d0.lo is None:
                out.update(date_status="uncertain", date_value=d0.reported)
                out["reasons"].append("DATE_PRECISION_UNJUSTIFIED")
            else:
                out.update(date_status="verified_fact", date_value=d0.reported)
    return out


def view(ev: Evidence, intervention: str) -> Evidence:
    """Intervention views of SPECIFICATION.md 11.2. Returns a new Evidence; the input is not changed."""
    new = Evidence(**{**ev.__dict__, "rw": list(ev.rw), "crossref": list(ev.crossref)})
    if intervention == "collapse_shared_origin":
        new.collapse = True  # type: ignore[attr-defined]
    elif intervention.startswith("exclude_origin:"):
        origin = intervention.split(":", 1)[1]
        new.rw = [a for a in ev.rw if a.origin != origin]
        new.crossref = [a for a in ev.crossref if a.origin != origin]
        new.sources = tuple(s for s in ev.sources if s != origin)
        if origin == RW:
            # Every Crossref relation sourced from Retraction Watch depends on that origin and was removed above.
            new.sources = ("crossref",) if new.crossref else ()
            if ev.state == "matched" and new.crossref:
                new.identity = "exact"
    elif intervention == "exclude_ambiguous_links":
        new.rw = [
            Assertion(**{**a.__dict__, "notice": None}) if a.notice_ambiguous else a for a in ev.rw if not a.bridged
        ]
        if ev.state == "matched" and new.identity == "bridged":
            new.identity = "exact"
    elif intervention == "require_temporal_bounds":
        new.rw = [
            Assertion(**{**a.__dict__, "date": Date(None, None, None)})
            if a.date is not None and a.date.lo is None and a.date.reported is not None
            else a
            for a in ev.rw
        ]
    return new


def result(ev: Evidence) -> dict[str, Any]:
    r = reduce(ev)
    if getattr(ev, "collapse", False):
        r["support_observations"] = len(r["support_origins"])
    return {
        "lookup_state": r["state"],
        "retraction_status.status": r["status"],
        "retraction_status.value": r["value"],
        "retraction_date.status": r["date_status"],
        "retraction_date.value": r["date_value"],
        "support.observations": r["support_observations"],
        "support.origins": r["support_origins"],
        "identity.status": r["identity"],
        "notice_links": r["notice_links"],
        "definite_orderings": r["definite_orderings"],
    }


def run_policy(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for case in cases:
        ev = gather(case)
        got = reduce(ev)
        got["events"] = len(ev.rw)
        exp = case["expected"]
        mismatches = []
        for key, want in exp.items():
            if key in ("dup_kinds", "quarantined"):
                continue  # ledger facts, checked by the engine tests
            if key == "reasons":
                missing = [x for x in want if x not in got["reasons"]]
                if missing:
                    mismatches.append(f"reasons missing {missing} (got {got['reasons']})")
                continue
            have = {"identity": got["identity"], "role": ev.role}.get(key, got.get(key))
            if have != want:
                mismatches.append(f"{key}: expected {want!r}, got {have!r}")
        out.append({"id": case["id"], "ok": not mismatches, "mismatches": mismatches})
    return out


def run_tension(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for case in cases:
        ev = gather(case)
        base = result(ev)
        mismatches = []
        for name, want in case["interventions"].items():
            changed = sorted(k for k, v in result(view(ev, name)).items() if base[k] != v)
            if changed != sorted(want):
                mismatches.append(f"{name}: expected {sorted(want)}, got {changed}")
        out.append({"id": case["id"], "classes": case["classes"], "ok": not mismatches, "mismatches": mismatches})
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    policy = json.loads((HERE / "cases" / "policy_cases.json").read_text(encoding="utf-8"))["cases"]
    tension = json.loads((HERE / "cases" / "tension_cases.json").read_text(encoding="utf-8"))["cases"]
    report = {
        "simulator": "simulations/stage02/policy_simulator.py",
        "synthetic": True,
        "policy": run_policy(policy),
        "tension": run_tension(tension),
    }
    report["summary"] = {
        "policy_cases": len(report["policy"]),
        "policy_failed": sum(not c["ok"] for c in report["policy"]),
        "tension_cases": len(report["tension"]),
        "tension_failed": sum(not c["ok"] for c in report["tension"]),
    }
    text = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    sys.stdout.write(json.dumps(report["summary"]) + "\n")
    for c in report["policy"] + report["tension"]:
        for m in c["mismatches"]:
            sys.stderr.write(f"{c['id']}: {m}\n")
    return 0 if not (report["summary"]["policy_failed"] or report["summary"]["tension_failed"]) else 1


if __name__ == "__main__":
    sys.exit(main())
