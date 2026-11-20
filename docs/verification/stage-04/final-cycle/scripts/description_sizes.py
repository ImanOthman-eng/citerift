"""Development measurement of the cited descriptions bib-1 reads (owner decision D-083, items 8 and 11; reviewer
findings A-08 and E-02; read-only, descriptive).

Usage: ``uv run python description_sizes.py <output .json>`` (committed as ``../lows/description_sizes.json``; it holds
sizes, counts and times, no citation text).

Over every development bundle with a committed source artifact (the 232 Step 13 development revisions, the 80 articles
of evaluation 1 and the 100 articles of evaluation 2, all design-exposed), the Stage 03 extractor
(``citerift.wiki.extract.extract_bundle``, default configuration, isolated worker as in production) gives the units.
For every ``citation_template`` unit, its source span is decoded and given to ``bibliographic.cited_object`` exactly as
NORMALIZE does (``adapters/normalize.cited_description``). Recorded:

- the source size of each unit in code points, against the spec 2.1 step 1 bound (``MAX_SOURCE_CODE_POINTS``);
- the committed description's total code points and its largest number of values in one family, against the step 6
  bounds (``MAX_TOTAL_CODE_POINTS``, ``MAX_VALUES``);
- per page, the process time of all ``cited_object`` calls (the bib-1 share of NORMALIZE), median, p95 and maximum;
- a crafted unit just under the step 1 bound (the nesting shape of reviewer finding E-02), to show the per-unit worst
  case the bound still admits.

No label, adjudication or score of either campaign is read. The counts set no threshold. The output records the
provenance of ``fc_provenance`` (reviewer finding D-03). Times depend on the machine and are recorded with it; run the
tool alone.
"""

from __future__ import annotations

import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fc_provenance import finish, start
from survey_pairs import bundles

from citerift.investigation import bibliographic as B
from citerift.wiki.extract import extract_bundle


def p95(xs: list[float]) -> float:
    s = sorted(xs)
    return s[max(0, -(-95 * len(s) // 100) - 1)]


def crafted(n: int) -> dict[str, Any]:
    src = "{{cite journal|title=" + "[[a|{{b|[[c|" * n + "}}"
    t0 = time.process_time()
    c = B.cited_object(src, "en")
    return {
        "nesting": n,
        "code_points": len(src),
        "cpu_s": round(time.process_time() - t0, 3),
        "cited_object": c is not None,
    }


def main() -> None:
    prov = start(Path(__file__))
    target = Path(sys.argv[1]).resolve()
    pages: list[dict[str, Any]] = []
    skipped: list[str] = []
    for tag, bundle in bundles():
        cap = json.loads((bundle / "capture.json").read_text(encoding="utf-8"))
        art = bundle / "artifacts" / cap["source"]["artifact"] if cap.get("source") else None
        if art is None or not art.exists():
            skipped.append(bundle.name)
            continue
        wiki = bundle.name.split("-", 1)[0]
        doc = extract_bundle(bundle)
        if "units" not in doc:
            skipped.append(bundle.name)
            continue
        data = art.read_bytes()
        src_max = desc_max = values_max = n = described = 0
        over_source = 0
        cpu = 0.0
        for unit in doc["units"]:
            if unit.get("kind") != "citation_template":
                continue
            span = unit["source"]
            try:
                text = data[span["byte_start"] : span["byte_end"]].decode("utf-8")
            except UnicodeDecodeError:
                continue
            n += 1
            src_max = max(src_max, len(text))
            over_source += len(text) > B.MAX_SOURCE_CODE_POINTS
            t0 = time.process_time()
            c = B.cited_object(text, wiki)
            cpu += time.process_time() - t0
            if c is None:
                continue
            described += 1
            values = [*c.titles, *c.authors, c.periodical, c.date, c.year, c.volume, c.issue, c.pages]
            desc_max = max(desc_max, sum(len(v) for v in values if v is not None))
            values_max = max(values_max, len(c.titles), len(c.authors))
        pages.append(
            {
                "set": tag,
                "bundle": bundle.name,
                "citation_template_units": n,
                "with_description": described,
                "largest_unit_code_points": src_max,
                "units_over_source_bound": over_source,
                "largest_description_code_points": desc_max,
                "most_values_in_one_family": values_max,
                "bib1_cpu_s": round(cpu, 4),
            }
        )
    times = [p["bib1_cpu_s"] for p in pages]
    summary = {
        "pages": len(pages),
        "bundles_skipped": skipped,
        "citation_template_units": sum(p["citation_template_units"] for p in pages),
        "with_description": sum(p["with_description"] for p in pages),
        "largest_unit_code_points": max(p["largest_unit_code_points"] for p in pages),
        "units_over_source_bound": sum(p["units_over_source_bound"] for p in pages),
        "largest_description_code_points": max(p["largest_description_code_points"] for p in pages),
        "most_values_in_one_family": max(p["most_values_in_one_family"] for p in pages),
        "bounds": {
            "MAX_SOURCE_CODE_POINTS": B.MAX_SOURCE_CODE_POINTS,
            "MAX_TOTAL_CODE_POINTS": B.MAX_TOTAL_CODE_POINTS,
            "MAX_VALUES": B.MAX_VALUES,
        },
        "bib1_cpu_s_per_page": {
            "median": round(statistics.median(times), 4),
            "p95": round(p95(times), 4),
            "max": round(max(times), 4),
        },
        "crafted_under_source_bound": [crafted(400), crafted(1300)],
        "machine": {"cpus": os.cpu_count(), "python": platform.python_version(), "platform": platform.platform()},
    }
    finish(prov, Path(__file__))
    doc_out = {"summary": summary, "pages": pages, "provenance": prov}
    target.write_text(json.dumps(doc_out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
