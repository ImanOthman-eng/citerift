"""Reviewer finding A-02 (owner decision D-083): how often bib-1's author rule agrees by accident, and how many
Stage 02 records carry a designation word in their own title.

Read-only and descriptive; it sets no threshold (bib-1 has none). Three measurements over the pinned Stage 02 index:

1. ``pairs``: ``PAIRS`` seeded random pairs (a, b) of events whose record author strings are both present and differ.
   Record a's ``;``-separated full names are cited as author values against record b. Counted: the pairs whose author
   verdict is AGREE under the first-draft rule (spec of ``59f2ad0``, 4.1: some name word of any cited value is a
   name word of the record, given names and particles included), under the amended rule (spec 4.1: every comparable
   cited value shares a record surname word), and under the amended rule with only the first name of a cited (a
   single commenter);
2. ``designation_in_record_title``: events whose record title holds a word of ``DW`` or a phrase of ``DP`` (such a
   retracted work cited with its own title is EQUAL and unaffected; cited with a shortened title, the word is not an
   extra word either; the count bounds the population where the lexicon touches a record);
3. ``single_author_records``: events whose record lists exactly one author (a citation that lists the co-authors the
   record omits gives CONFLICT: a stated recall cost).

Usage: ``uv run python author_coincidence.py INDEX.sqlite OUT.json``.
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fc_provenance import provenance

from citerift.investigation import bibliographic as B
from citerift.retraction.query import Index

SEED = 20261119
PAIRS = 20000
_ET_AL = re.compile(r"\bet\.?\s*al\b\.?")


def first_draft_words(value: str) -> set[str]:
    """Name words of the first draft (``59f2ad0``): no particle removal, no initials removal, every name word."""
    return {w for w in B.words(_ET_AL.sub(" ", B.fold(value))) if len(w) >= 2 and not w.isdecimal()}


def first_draft_agree(cited: list[str], record: str) -> bool:
    a_c = set().union(*(first_draft_words(v) for v in cited))
    a_r = set().union(*(first_draft_words(p) for p in record.split(";")))
    return bool(a_c & a_r)


def main() -> int:
    path, target = Path(sys.argv[1]), Path(sys.argv[2])
    with Index(path) as index:
        ids = [r[0] for r in index.conn.execute("SELECT event_id FROM event ORDER BY event_id")]
        events = {i: index.event_by_id(i) for i in ids}
    with_authors = [i for i in ids if (events[i] or {}).get("authors")]
    rng = random.Random(SEED)  # noqa: S311 - a seeded sample, not a secret
    counts = {"first_draft": 0, "amended": 0, "amended_one_commenter": 0}
    drawn = 0
    while drawn < PAIRS:
        a, b = rng.sample(with_authors, 2)
        ra, rb = events[a]["authors"], events[b]["authors"]  # type: ignore[index]
        if ra == rb:
            continue
        drawn += 1
        cited = [p.strip() for p in ra.split(";") if p.strip()]
        counts["first_draft"] += first_draft_agree(cited, rb)
        counts["amended"] += B.authors_verdict(cited, rb) == "AGREE"
        counts["amended_one_commenter"] += B.authors_verdict(cited[:1], rb) == "AGREE"
    designated = 0
    for i in ids:
        title = (events[i] or {}).get("title")
        if not title:
            continue
        w = B.words(title)
        joined = " " + " ".join(w) + " "
        if set(w) & B.DESIGNATION_WORDS or any(f" {p} " in joined for p in B.DESIGNATION_PHRASES):
            designated += 1
    single = sum(1 for i in with_authors if len([p for p in events[i]["authors"].split(";") if p.strip()]) == 1)  # type: ignore[index]
    report: dict[str, Any] = {
        "seed": SEED,
        "pairs": PAIRS,
        "events": len(ids),
        "events_with_authors": len(with_authors),
        "agree_by_accident": counts,
        "designation_in_record_title": designated,
        "single_author_records": single,
        "provenance": provenance(Path(__file__), path),
    }
    target.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "provenance"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
