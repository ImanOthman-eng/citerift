"""Select the pinned real reviewed cases (gate 02-C) and write the attributed CI fixture.

Method (stated in TEST_RESULTS.md): cases are chosen deterministically by class from the pinned snapshot. For each
query, the related records are located with the independent streaming oracle's key maps (query keys in both
roles, plus the one-hop bridge keys of SPECIFICATION.md 10.3), read with the standard csv module, and given to the
prebuild policy simulator, which produces the expected outcome without engine code. The engine's answer on the
full index is recorded beside it. The agent then reviewed every case's rows against the specification; there is
no human adjudication.

The fixture keeps only selected fields of at most 120 records (docs/sources-and-attribution.md); other columns are
empty. Its records are attributed to Retraction Watch via Crossref.

Run: python docs/verification/stage-02/scripts/real_cases.py --csv CSV --oracle ORACLE.json --index INDEX \
  --out-cases tests/stage02/fixtures/real_cases.json --out-csv tests/stage02/fixtures/rw_real_subset.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from citerift.retraction.query import lookup

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "simulations" / "stage02"))
import policy_simulator as sim  # the independent reference model, not engine code

FIXTURE_FIELDS = (
    "Record ID",
    "Title",
    "Journal",
    "Publisher",
    "RetractionDate",
    "RetractionDOI",
    "RetractionPubMedID",
    "OriginalPaperDate",
    "OriginalPaperDOI",
    "OriginalPaperPubMedID",
    "RetractionNature",
)
MAX_RECORDS = 120
PER_CLASS = 2
MAX_CLOSURE = 4


class Corpus:
    def __init__(self, csv_path: Path, oracle: dict[str, Any]):
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            self.header = next(reader)
            self.rows = {i: dict(zip(self.header, r, strict=True)) for i, r in enumerate(reader, 1)}
        self.oracle = oracle
        self.d = {o: sim.doi_key(r["OriginalPaperDOI"]) for o, r in self.rows.items()}
        self.p = {o: sim.pmid_key(r["OriginalPaperPubMedID"]) for o, r in self.rows.items()}
        self.invalid = [
            o
            for o, r in self.rows.items()
            if sim.doi_invalid_raw(r["OriginalPaperDOI"])
            or sim.doi_invalid_raw(r["RetractionDOI"])
            or sim.pmid_invalid_raw(r["OriginalPaperPubMedID"])
            or sim.pmid_invalid_raw(r["RetractionPubMedID"])
        ]

    def roles(self, scheme: str, key: str | None) -> dict[str, list[int]]:
        if key is None:
            return {"original": [], "notice": []}
        entry = self.oracle[scheme].get(key, {"original": [], "notice": []})
        return {"original": list(entry["original"]), "notice": list(entry["notice"])}

    def closure(self, doi: str | None, pmid: str | None) -> list[int]:
        qd = sim.doi_key(doi) if doi else None
        qp = sim.pmid_key(pmid) if pmid else None
        out: set[int] = set()
        rd, rp = self.roles("doi", qd), self.roles("pmid", qp)
        out |= set(rd["original"] + rd["notice"] + rp["original"] + rp["notice"])
        if qd and not qp:
            secondary = {self.p[o] for o in rd["original"]} - {None}
            if len(secondary) == 1:
                out |= set(self.roles("pmid", secondary.pop())["original"])
        if qp and not qd:
            dois = {self.d[o] for o in rp["original"]} - {None}
            if len(dois) == 1:
                out |= set(self.roles("doi", dois.pop())["original"])
        keys = [k for k in (qd, qp) if k]
        for o in self.invalid:
            r = self.rows[o]
            fields = [
                r[c] for c in ("OriginalPaperDOI", "RetractionDOI", "OriginalPaperPubMedID", "RetractionPubMedID")
            ]
            if any(k in f.lower() for k in keys for f in fields):
                out.add(o)
        return sorted(out)

    def case_rows(self, ordinals: list[int]) -> list[dict[str, str]]:
        out = []
        for o in ordinals:
            r = self.rows[o]
            out.append(
                {
                    "id": r["Record ID"],
                    "nature": r["RetractionNature"],
                    "od": r["OriginalPaperDOI"],
                    "op": r["OriginalPaperPubMedID"],
                    "nd": r["RetractionDOI"],
                    "np": r["RetractionPubMedID"],
                    "rd": r["RetractionDate"],
                    "pd": r["OriginalPaperDate"],
                }
            )
        return out


def natures(c: Corpus, ords: list[int]) -> list[str]:
    return sorted(c.rows[o]["RetractionNature"] for o in ords)


def originals_by_doi(c: Corpus) -> Iterator[tuple[str, list[int]]]:
    for key in sorted(c.oracle["doi"]):
        orig = c.oracle["doi"][key]["original"]
        if orig:
            yield key, orig


def classes(c: Corpus) -> dict[str, Callable[[], Iterator[dict[str, Any]]]]:
    def by_doi(pred: Callable[[str, list[int]], bool]) -> Iterator[dict[str, Any]]:
        for key, orig in originals_by_doi(c):
            if pred(key, orig):
                yield {"doi": key}

    def single(nature: str) -> Callable[[str, list[int]], bool]:
        return lambda k, o: natures(c, o) == [nature] and not c.oracle["doi"][k]["notice"]

    def day(o: int) -> int | None:
        parts = c.rows[o]["RetractionDate"].split("/")
        return int(parts[1]) if len(parts) == 3 else None

    def notice_only() -> Iterator[dict[str, Any]]:
        for key in sorted(c.oracle["doi"]):
            e = c.oracle["doi"][key]
            if not e["original"] and len(e["notice"]) == 1:
                yield {"doi": key}

    def shared_notice() -> Iterator[dict[str, Any]]:
        for key in sorted(c.oracle["doi"]):
            e = c.oracle["doi"][key]
            if not e["original"] and len({c.d[o] for o in e["notice"]}) >= 2:
                yield {"doi": key}

    def notice_also_original() -> Iterator[dict[str, Any]]:
        for key in sorted(c.oracle["doi"]):
            e = c.oracle["doi"][key]
            if e["original"] and e["notice"]:
                yield {"doi": key}

    def pmid_many_dois() -> Iterator[dict[str, Any]]:
        for key in sorted(c.oracle["pmid"]):
            o = c.oracle["pmid"][key]["original"]
            if len({c.d[x] for x in o} - {None}) > 1:
                yield {"pmid": key}

    def doi_many_pmids() -> Iterator[dict[str, Any]]:
        for key, orig in originals_by_doi(c):
            if len({c.p[o] for o in orig} - {None}) > 1:
                yield {"doi": key}

    def doi_bridge() -> Iterator[dict[str, Any]]:
        for key in sorted(c.oracle["pmid"]):
            o = c.oracle["pmid"][key]["original"]
            ds = {c.d[x] for x in o} - {None}
            if len(ds) == 1 and o:
                d2 = next(iter(ds))
                if any(c.p[x] is None for x in c.oracle["doi"][d2]["original"]):
                    yield {"pmid": key}

    def dual_compatible() -> Iterator[dict[str, Any]]:
        for key, orig in originals_by_doi(c):
            ps = {c.p[o] for o in orig} - {None}
            if len(ps) == 1:
                yield {"doi": key, "pmid": next(iter(ps))}

    def dual_incompatible() -> Iterator[dict[str, Any]]:
        pairs = [(k, c.p[o[0]]) for k, o in originals_by_doi(c) if len(o) == 1 and c.p[o[0]]]
        for (k1, _p1), (_k2, p2) in itertools.pairwise(pairs):
            yield {"doi": k1, "pmid": p2}

    def pmid_only_anchor() -> Iterator[dict[str, Any]]:
        for key in sorted(c.oracle["pmid"]):
            o = c.oracle["pmid"][key]["original"]
            if o and all(c.d[x] is None for x in o):
                yield {"pmid": key}

    def year(raw: str) -> int | None:
        parts = raw.split(" ", 1)[0].split("/")
        return int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else None

    def historical() -> Iterator[dict[str, Any]]:
        # Queried by the original identifier when the record has one, so the date reaches the projection;
        # otherwise by the notice DOI, which checks only that the event keeps the date (class name says so).
        for o in sorted(c.rows):
            r = c.rows[o]
            years = [year(r[f]) for f in ("OriginalPaperDate", "RetractionDate")]
            if any(y is not None and y < 1900 for y in years):
                nd = sim.doi_key(r["RetractionDOI"])
                if c.d[o]:
                    yield {"doi": c.d[o]}
                elif c.p[o]:
                    yield {"pmid": c.p[o]}
                elif nd:
                    yield {"doi": nd}

    def no_original_ids() -> Iterator[dict[str, Any]]:
        for o in sorted(c.rows):
            r = c.rows[o]
            nd = sim.doi_key(r["RetractionDOI"])
            if c.d[o] is None and c.p[o] is None and nd and r["RetractionNature"] in sim.TYPES:
                yield {"doi": nd}

    def invalid_identifier() -> Iterator[dict[str, Any]]:
        # Only keys found in no role: the lookup is then no_record, and the invalid occurrence must turn it into a
        # coverage gap (review finding: a key that is a notice elsewhere tested the notice path instead).
        for o in c.invalid:
            r = c.rows[o]
            if sim.pmid_invalid_raw(r["OriginalPaperPubMedID"]):
                key = r["OriginalPaperPubMedID"].lstrip("0")
                if sim.pmid_key(key) and key not in c.oracle["pmid"]:
                    yield {"pmid": key}
            for col in ("RetractionDOI", "OriginalPaperDOI"):
                if sim.doi_invalid_raw(r[col]):
                    key = sim.doi_key(r[col][r[col].find("10.") :].strip())
                    if key and key not in c.oracle["doi"]:
                        yield {"doi": key}

    def sequence_on_shared_notice() -> Iterator[dict[str, Any]]:
        # Two RW records of different types under one notice DOI with different dates (SPECIFICATION.md 16, C-12).
        for key, orig in originals_by_doi(c):
            notices = {sim.doi_key(c.rows[o]["RetractionDOI"]) for o in orig}
            dates = {c.rows[o]["RetractionDate"][:10] for o in orig}
            if (
                len(orig) == 2
                and len(set(natures(c, orig))) == 2
                and len(notices) == 1
                and None not in notices
                and len(dates) == 2
                and all(day(o) != 1 for o in orig)
            ):
                yield {"doi": key}

    def same_signature() -> Iterator[dict[str, Any]]:
        for key, orig in originals_by_doi(c):
            sigs = [
                (c.rows[o]["RetractionNature"], c.rows[o]["RetractionDOI"].lower(), c.rows[o]["RetractionDate"][:10])
                for o in orig
            ]
            if len(set(sigs)) < len(sigs) and len({tuple(c.rows[o].values()) for o in orig}) == len(orig):
                yield {"doi": key}

    absent = c.oracle["absent_keys"]
    return {
        "retraction_single": lambda: by_doi(single("Retraction")),
        "correction_single": lambda: by_doi(single("Correction")),
        "concern_single": lambda: by_doi(single("Expression of concern")),
        "reinstatement_with_retraction": lambda: by_doi(
            lambda k, o: "Reinstatement" in natures(c, o) and "Retraction" in natures(c, o)
        ),
        "reinstatement_without_retraction": lambda: by_doi(
            lambda k, o: "Reinstatement" in natures(c, o) and "Retraction" not in natures(c, o)
        ),
        "concern_then_retraction": lambda: by_doi(
            lambda k, o: natures(c, o) == ["Expression of concern", "Retraction"]
        ),
        "retraction_and_correction": lambda: by_doi(lambda k, o: natures(c, o) == ["Correction", "Retraction"]),
        "mixed_non_retraction": lambda: by_doi(lambda k, o: natures(c, o) == ["Correction", "Expression of concern"]),
        "notice_equals_original": lambda: by_doi(
            lambda k, o: len(o) == 1 and sim.doi_key(c.rows[o[0]]["RetractionDOI"]) == k
        ),
        "notice_only": notice_only,
        "shared_notice": shared_notice,
        "notice_also_original_elsewhere": notice_also_original,
        "pmid_names_several_dois": pmid_many_dois,
        "doi_with_divergent_pmids": doi_many_pmids,
        "doi_cooccurrence_bridge": doi_bridge,
        "dual_query_compatible": dual_compatible,
        "dual_query_incompatible": dual_incompatible,
        "pmid_only_original": pmid_only_anchor,
        "day_one_retraction_date": lambda: by_doi(lambda k, o: natures(c, o) == ["Retraction"] and day(o[0]) == 1),
        "two_retraction_dates": lambda: by_doi(
            lambda k, o: (
                natures(c, o) == ["Retraction", "Retraction"]
                and len({c.rows[x]["RetractionDate"][:10] for x in o}) == 2
            )
        ),
        "historical_date_event_via_notice_query": historical,
        "no_original_identifiers": no_original_ids,
        "invalid_identifier_relevance": invalid_identifier,
        "same_event_signature": same_signature,
        "sequence_on_shared_notice": sequence_on_shared_notice,
        "absent_doi": lambda: iter([{"doi": absent["doi"][0]}, {"doi": absent["doi"][1]}]),
        "absent_pmid": lambda: iter([{"pmid": absent["pmid"][0]}]),
    }


def absent_classes(c: Corpus) -> dict[str, str]:
    """Targeted classes with no instance in the pinned snapshot, with the count that shows it."""
    rows = list(c.rows.values())
    identical = len(rows) - len({tuple(r.values()) for r in rows})
    ids = [r["Record ID"] for r in rows if r["Record ID"]]
    pmid_only_sharing = sum(
        1
        for key, e in c.oracle["pmid"].items()
        if any(c.d[o] is None for o in e["original"]) and any(c.d[o] is not None for o in e["original"])
    )
    secondary_bridge = 0
    for _key, orig in originals_by_doi(c):
        sec = {c.p[o] for o in orig} - {None}
        if len(sec) == 1 and any(c.d[o] is None for o in c.oracle["pmid"][next(iter(sec))]["original"]):
            secondary_bridge += 1
    historical_with_ids = sum(
        1
        for o, r in c.rows.items()
        if (c.d[o] or c.p[o])
        and any(
            (y := r[f].split(" ", 1)[0].split("/")[-1]).isdigit() and int(y) < 1900
            for f in ("OriginalPaperDate", "RetractionDate")
        )
    )
    return {
        "historical_date_with_original_identifier": f"{historical_with_ids} pre-1900 records with an original DOI or "
        "PMID; the 1756 record is reached only through its notice DOI",
        "identical_duplicate": f"{identical} identical records in the snapshot",
        "record_id_reused": f"{len(ids) - len(set(ids))} repeated Record IDs in the snapshot",
        "pmid_cooccurrence_bridge": f"{secondary_bridge} DOIs with a PMID-only partner record "
        f"({pmid_only_sharing} PMIDs shared by DOI and DOI-less records)",
    }


def expected(c: Corpus, query: dict[str, str], ordinals: list[int]) -> dict[str, Any]:
    case = {"rows": c.case_rows(ordinals), "query": query}
    ev = sim.gather(case)
    r = sim.reduce(ev)
    return {
        "state": r["state"],
        "status": r["status"],
        "value": r["value"],
        "date_status": r["date_status"],
        "date_value": r["date_value"],
        "events": len(ev.rw),
        "identity": r["identity"],
        "record_ids": sorted(a.event_id.split("#")[0] for a in ev.rw if a.event_id),
        "reasons": sorted(r["reasons"]),
    }


def engine(index: Path, query: dict[str, str]) -> dict[str, Any]:
    out = lookup(index, query.get("doi"), query.get("pmid"), page_size=100)
    proj = out["projection"] or {}
    status = proj.get("retraction_status") or {}
    date = proj.get("retraction_date") or {}
    return {
        "state": out["lookup_state"],
        "status": status.get("status"),
        "value": status.get("value"),
        "date_status": date.get("status"),
        "date_value": date.get("value"),
        "events": out["total_event_count"],
        "identity": out["identity"]["status"],
        "record_ids": sorted(e["record_id"] for e in out["events"]),
        "reasons": sorted((proj.get("basis") or {}).get("reasons", [])),
        "role": out["identifier_role"],
        "evidence_digest": out["evidence_digest"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--oracle", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out-cases", type=Path, required=True)
    ap.add_argument("--out-csv", type=Path, required=True)
    args = ap.parse_args(argv)
    c = Corpus(args.csv, json.loads(args.oracle.read_text(encoding="utf-8")))
    chosen: list[dict[str, Any]] = []
    used: set[int] = set()
    seen: set[str] = set()  # a query is used by one class only
    for name, gen in classes(c).items():
        taken = 0
        for query in gen():
            sig = json.dumps(query, sort_keys=True)
            if sig in seen:
                continue
            seen.add(sig)
            ords = c.closure(query.get("doi"), query.get("pmid"))
            if not 0 < len(ords) <= MAX_CLOSURE and not name.startswith("absent"):
                continue
            used |= set(ords)
            exp = expected(c, query, ords)
            got = engine(args.index, query)
            # Reason codes: the simulator's are a subset (it names fewer), as in the frozen-case tests.
            agree = all(exp[k] == got[k] for k in exp if k != "reasons") and set(exp["reasons"]) <= set(got["reasons"])
            chosen.append(
                {
                    "id": f"R{len(chosen) + 1:02d}",
                    "class": name,
                    "query": query,
                    "record_ids": sorted(c.rows[o]["Record ID"] for o in ords),
                    "source_records": [f"record={o}" for o in ords],
                    "expected_simulator": exp,
                    "engine_full_index": got,
                    "agree": agree,
                }
            )
            taken += 1
            if taken == PER_CLASS:
                break
    if len(used) > MAX_RECORDS:
        sys.stderr.write(f"{len(used)} records exceed the {MAX_RECORDS}-record fixture limit\n")
        return 1
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(c.header)
    for o in sorted(used):
        writer.writerow([c.rows[o][h] if h in FIXTURE_FIELDS else "" for h in c.header])
    data = ("﻿" + buf.getvalue()).encode("utf-8")
    args.out_csv.write_bytes(data)
    manifest = {
        "fixture": args.out_csv.name,
        "fixture_sha256": hashlib.sha256(data).hexdigest(),
        "fixture_bytes": len(data),
        "fixture_records": len(used),
        "fixture_fields": list(FIXTURE_FIELDS),
        "attribution": "Retraction Watch data via Crossref (https://gitlab.com/crossref/retraction-watch-data), "
        "commit a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4; selected fields of at most 120 records; other columns "
        "left empty. Cited as the source requests; not a redistribution of the dataset.",
        "method": "Classes chosen deterministically; related records located with the independent oracle; expected "
        "outcomes from the prebuild policy simulator; engine answers from the full index; agent review of each "
        "case against SPECIFICATION.md. No human adjudication.",
        "cases": chosen,
        "classes_covered": sorted({x["class"] for x in chosen}),
        "classes_absent_in_snapshot": absent_classes(c),
        "agree": sum(x["agree"] for x in chosen),
        "total": len(chosen),
    }
    args.out_cases.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "cases": len(chosen),
                "agree": manifest["agree"],
                "records": len(used),
                "classes": len(manifest["classes_covered"]),
            }
        )
    )
    for x in chosen:
        if not x["agree"]:
            print(
                "DISAGREE",
                x["id"],
                x["class"],
                x["query"],
                json.dumps(
                    {
                        k: (x["expected_simulator"][k], x["engine_full_index"][k])
                        for k in x["expected_simulator"]
                        if x["expected_simulator"][k] != x["engine_full_index"][k]
                    }
                ),
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
