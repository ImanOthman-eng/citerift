"""Stage 04 corrective cycle (D-071), item 2: read-only role-collision census of the pinned Stage 02 snapshot.

Reads one Stage 02 index (opened read-only, ``mode=ro``) and writes a JSON census of every identifier that the
snapshot gives in more than one publication-object role. Nothing is written to the index; no network; no clock in the
output. The frozen-engine column decides, for every colliding identifier, a synthetic citation that carries only that
identifier (eligibility CITED, shape DOI or PMID, no taint) with the frozen dt-1 code (loaded by its pinned git blob,
``../frozen_dt1.py``, never the working tree) and, beside it, with the working-tree table (dt-2), on the observation the
production LOOKUP adapter builds (``adapters.lookup.observe`` with the default evidence budget). It uses no holdout
label and no
evaluation result.

Collision kinds (identifier key = scheme + normalized value):

- ``same_record``: one source record gives the key as both its original and its notice identifier (Stage 02 import flag
  ``NOTICE_DOI_EQUALS_ORIGINAL`` / ``NOTICE_PMID_EQUALS_ORIGINAL``; the notice occurrence is kept in ``ident`` and the
  event's notice field is nulled, SPEC 6.3).
- ``cross_record``: the key is the original identifier of at least one event and the notice identifier of at least one
  other event (a lookup of the key is ``matched`` with ``identifier_role = original_and_notice`` and ``notice_hits``).

Usage: ``python role_collision_census.py INDEX.sqlite OUT.json``
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from citerift.investigation import dt1

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import frozen_dt1 as F1

from citerift.investigation.adapters.detector import lookup_view
from citerift.investigation.adapters.lookup import observe
from citerift.investigation.lookup import DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES
from citerift.retraction.query import Index

SCHEMES = ("doi", "pmid")
FLAG = {"doi": "NOTICE_DOI_EQUALS_ORIGINAL", "pmid": "NOTICE_PMID_EQUALS_ORIGINAL"}


def _ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def frozen_class(index: Index, scheme: str, key: str) -> dict[str, Any]:
    """The frozen dt-1 outcome of a citation carrying only this key, and what Stage 02 exposes in the lookup."""
    doi, pmid = (key, None) if scheme == "doi" else (None, key)
    obs = observe(index, {}, doi, pmid, DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES)
    lk = lookup_view(obs)
    role = dt1.Q1_DOI if scheme == "doi" else dt1.Q1_PMID
    cand = dt1.Candidate("CITED", None, scheme.upper(), doi, pmid, (), False, ((role, lk),))
    out = F1.decide(cand)
    new = dt1.decide(cand)
    res = obs["result"]
    return {
        "rule": out.rule,
        "class": out.cls or out.failure,
        "reasons": list(out.reasons),
        "dt2": f"{new.rule} {new.cls or new.failure}",
        "lookup_state": res.get("lookup_state"),
        "identifier_role": res.get("identifier_role"),
        "notice_hit_count": res.get("notice_hit_count", 0),
        "issue_codes": sorted({i.get("code") for i in res.get("issues") or () if isinstance(i, dict)}),
        "event_flags": sorted({f for e in obs["events"] for f in e.get("flags") or ()}),
    }


def census(path: Path) -> dict[str, Any]:
    con = _ro(path)
    con.row_factory = sqlite3.Row
    meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
    events = [dict(r) for r in con.execute("SELECT * FROM event")]
    for e in events:
        e["flags"] = json.loads(e["flags"])
    n_events = len(events)

    # ident-table view (every occurrence, before Stage 02 nulls a same-record notice) ------------------------------
    ident_roles: dict[tuple[str, str], dict[str, set[int]]] = defaultdict(lambda: {"original": set(), "notice": set()})
    for scheme, norm, role, ordinal in con.execute(
        "SELECT scheme, norm, role, ordinal FROM ident WHERE norm IS NOT NULL AND missing = 0"
    ):
        ident_roles[(scheme, norm)][role].add(ordinal)
    ident_view: dict[str, Any] = {}
    for scheme in SCHEMES:
        both = {k: v for k, v in ident_roles.items() if k[0] == scheme and v["original"] and v["notice"]}
        same = {k for k, v in both.items() if v["original"] & v["notice"]}
        # cross-record: some record gives the key as its notice identifier only, and another as an original
        cross = {k for k, v in both.items() if v["notice"] - v["original"]}
        ident_view[scheme] = {
            "keys_in_both_roles": len(both),
            "keys_same_record": len(same),
            "keys_cross_record": len(cross),
            "keys_cross_record_only": len(cross - same),
            "keys_same_and_cross": len(same & cross),
            "records_involved": len(set().union(*(v["original"] | v["notice"] for v in both.values())) if both else 0),
        }

    # event view: same-record collisions ----------------------------------------------------------------------------
    same_record: dict[str, Any] = {}
    for scheme in SCHEMES:
        hit = [e for e in events if FLAG[scheme] in e["flags"]]
        keys = {e[f"original_{scheme}"] for e in hit}
        other = "pmid" if scheme == "doi" else "doi"
        same_record[scheme] = {
            "records": len(hit),
            "distinct_keys": len(keys),
            "by_event_type": dict(sorted(Counter(e["event_type"] for e in hit).items())),
            "by_source_label": dict(sorted(Counter(e["source_label"] for e in hit).items())),
            "with_distinct_notice_" + other: sum(1 for e in hit if e[f"notice_{other}"] is not None),
            "with_other_scheme_also_equal": sum(1 for e in hit if FLAG[other] in e["flags"]),
            "also_no_independent_notice_identifier": sum(1 for e in hit if e["notice_key"] is None),
        }
    both_flags = [e for e in events if FLAG["doi"] in e["flags"] and FLAG["pmid"] in e["flags"]]

    # event view: cross-record collisions ---------------------------------------------------------------------------
    cross_record: dict[str, Any] = {}
    cross_keys: dict[str, set[str]] = {}
    for scheme in SCHEMES:
        orig: dict[str, list[dict[str, Any]]] = defaultdict(list)
        note: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for e in events:
            if e[f"original_{scheme}"]:
                orig[e[f"original_{scheme}"]].append(e)
            if e[f"notice_{scheme}"]:
                note[e[f"notice_{scheme}"]].append(e)
        keys = set(orig) & set(note)
        cross_keys[scheme] = keys
        pairs: Counter[str] = Counter()
        for k in keys:
            for a in {e["event_type"] for e in orig[k]}:
                for b in {e["event_type"] for e in note[k]}:
                    pairs[f"original:{a} / notice:{b}"] += 1
        flagged = sum(1 for k in keys for e in note[k] if "NOTICE_ALSO_ORIGINAL_ELSEWHERE" in e["flags"])
        cross_record[scheme] = {
            "distinct_keys": len(keys),
            "events_with_key_as_original": sum(len(orig[k]) for k in keys),
            "events_with_key_as_notice": sum(len(note[k]) for k in keys),
            "event_type_pairs_by_key": dict(sorted(pairs.items())),
            "notice_events_flagged_NOTICE_ALSO_ORIGINAL_ELSEWHERE": flagged,
        }

    # context (not collisions) --------------------------------------------------------------------------------------
    context = {
        "events": n_events,
        "no_notice_identifier": sum(1 for e in events if "NO_NOTICE_IDENTIFIER" in e["flags"]),
        "notice_shared": sum(1 for e in events if "NOTICE_SHARED" in e["flags"]),
        "original_anchor_pmid_only": sum(1 for e in events if "ORIGINAL_ANCHOR_PMID_ONLY" in e["flags"]),
        "original_anchor_source_record_only": sum(
            1 for e in events if "ORIGINAL_ANCHOR_SOURCE_RECORD_ONLY" in e["flags"]
        ),
        "both_schemes_equal_in_one_record": len(both_flags),
    }

    # frozen-engine class of a citation carrying only the colliding key ---------------------------------------------
    frozen: dict[str, Any] = {}
    index = Index(path)
    try:
        for scheme in SCHEMES:
            same_keys = {e[f"original_{scheme}"] for e in events if FLAG[scheme] in e["flags"]}
            groups = {
                "same_record_only": same_keys - cross_keys[scheme],
                "cross_record_only": cross_keys[scheme] - same_keys,
                "same_and_cross": same_keys & cross_keys[scheme],
            }
            frozen[scheme] = {}
            for name, keys in groups.items():
                tally: Counter[str] = Counter()
                tally2: Counter[str] = Counter()
                exposure: Counter[str] = Counter()
                positives: list[str] = []
                for k in sorted(keys):
                    r = frozen_class(index, scheme, k)
                    tally[f"{r['rule']} {r['class']}"] += 1
                    tally2[r["dt2"]] += 1
                    exposure[
                        "issue PMID_ROLE_COLLISION"
                        if "PMID_ROLE_COLLISION" in r["issue_codes"]
                        else ("identifier_role=" + str(r["identifier_role"]))
                    ] += 1
                    if r["rule"] == "D-14":
                        positives.append(k)
                frozen[scheme][name] = {
                    "keys": len(keys),
                    "frozen_dt1_outcome": dict(sorted(tally.items())),
                    "dt2_outcome": dict(sorted(tally2.items())),
                    "stage02_lookup_exposure": dict(sorted(exposure.items())),
                    "positive_keys": len(positives),
                    "positive_key_examples": positives[:10],
                }
    finally:
        index.close()

    return {
        "census": "citerift-stage04-role-collision-census/1",
        "index": {
            "snapshot_id": meta.get("snapshot_id"),
            "artifact_digest": meta.get("artifact_digest"),
            "semantic_digest": meta.get("semantic_digest"),
            "source_sha256": meta.get("source_sha256"),
            "policy_version": meta.get("policy_version"),
        },
        "budget_bytes": DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES,
        "ident_table": ident_view,
        "same_record": same_record,
        "cross_record": cross_record,
        "context": context,
        "frozen_engine_single_key_citation": frozen,
    }


def main(argv: list[str]) -> int:
    doc = census(Path(argv[1]))
    Path(argv[2]).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(doc, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
