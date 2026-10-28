"""Freeze the Evidence Ambiguity Investigator evaluation (SPECIFICATION.md 12.3) before any prediction.

Draws the 40 tuning and 120 held-out groups with a fixed seed, builds the deterministic candidate bundles,
chooses the baseline thresholds on the tuning split only, and writes protocol.json. It does not score the
held-out split: that happens in ai_evaluate.py, after protocol.json is committed.

Run: python docs/verification/stage-02/scripts/ai_protocol.py --index INDEX --out docs/verification/stage-02/ai
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

from citerift.retraction import advisory, ambiguity
from citerift.retraction.canonical import canonical
from citerift.retraction.query import Index
from citerift.retraction.search import title_tokens

SEED = 20261027
QUOTAS = {
    # The real snapshot holds 16 positives whose target record differs in year, authors or title (cosine < 0.9);
    # all of them are used (counted from record fields before any prediction).
    "tuning": {"positive": {"disagreement": 4, "other": 16}, "negative": {"similar_title": 5, "other": 15}},
    "heldout": {"positive": {"disagreement": 12, "other": 48}, "negative": {"similar_title": 20, "other": 40}},
}
TITLE_DISAGREEMENT_COS = 0.9
SIMILAR_TITLE_COS = 0.6


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[Any, Any] = {}

    def find(self, x: Any) -> Any:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: Any, b: Any) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb, key=str)] = min(ra, rb, key=str)


def groups(ix: Index) -> dict[Any, list[dict[str, Any]]]:
    uf = UnionFind()
    rows = ix.conn.execute(
        "SELECT ordinal, record_id, original_doi, original_pmid, notice_doi, notice_pmid, event_type, title, authors,"
        " journal, original_year, flags FROM event ORDER BY ordinal"
    ).fetchall()
    events = []
    for r in rows:
        e = dict(
            zip(
                [
                    "ordinal",
                    "record_id",
                    "od",
                    "op",
                    "nd",
                    "np",
                    "type",
                    "title",
                    "authors",
                    "journal",
                    "year",
                    "flags",
                ],
                r,
                strict=True,
            )
        )
        events.append(e)
        node = ("row", e["ordinal"])
        uf.find(node)
        for key in (
            ("doi", e["od"]),
            ("pmid", e["op"]),
            ("doi", e["nd"]),
            ("pmid", e["np"]),
            ("rid", e["record_id"] or None),
        ):
            if key[1]:
                uf.union(node, key)
    out: dict[Any, list[dict[str, Any]]] = {}
    for e in events:
        out.setdefault(uf.find(("row", e["ordinal"])), []).append(e)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    with Index(args.index) as ix:
        base = ambiguity.Baseline(ix)
        by_doi: dict[str, list[int]] = {}
        for ordinal, od in ix.conn.execute("SELECT ordinal, original_doi FROM event WHERE original_doi IS NOT NULL"):
            by_doi.setdefault(od, []).append(ordinal)
        pool = []
        for members in groups(ix).values():
            q = next((e for e in members if e["od"]), None)  # smallest ordinal with a valid original DOI
            if q is None:
                continue
            others = [o for o in by_doi[q["od"]] if o != q["ordinal"]]
            types = {e["type"] for e in members}
            pool.append(
                {
                    "query": q,
                    "label": "positive" if others else "negative",
                    "target": f"doi:{q['od']}" if others else None,
                    "target_ordinal": min(others) if others else None,
                    "members": len(members),
                    "mixed_event": len(types) > 1,
                    "shared_notice": "NOTICE_SHARED" in q["flags"],
                    "notice_also_original": "NOTICE_ALSO_ORIGINAL_ELSEWHERE" in q["flags"],
                }
            )
        pool.sort(key=lambda g: g["query"]["ordinal"])
        rng = random.Random(SEED)  # noqa: S311 - a reproducible draw, not a secret
        rng.shuffle(pool)
        need = {(split, lab, st): n for split, q in QUOTAS.items() for lab, sts in q.items() for st, n in sts.items()}
        chosen: dict[str, list[dict[str, Any]]] = {"tuning": [], "heldout": []}
        examined = 0
        for g in pool:
            if not any(need.values()):
                break
            if not any(n for (_s, lab, _st), n in need.items() if lab == g["label"]):
                continue
            examined += 1
            q = g["query"]
            probe = ambiguity.Probe(q["ordinal"], q["title"], q["authors"], q["year"])
            if g["label"] == "positive":
                t = ix.conn.execute(
                    "SELECT title, authors, original_year FROM event WHERE ordinal = ?", (g["target_ordinal"],)
                ).fetchone()
                disagree = (
                    t[2] != q["year"]
                    or ambiguity._author_score(q["authors"], t[1]) < 0.5
                    or base.cosine(title_tokens(q["title"]), title_tokens(t[0])) < TITLE_DISAGREEMENT_COS
                )
                stratum = "disagreement" if disagree else "other"
            else:
                cands = base.candidates(probe)
                stratum = "similar_title" if cands and cands[0].cos_title >= SIMILAR_TITLE_COS else "other"
            slot = next((s for s in ("tuning", "heldout") if need.get((s, g["label"], stratum), 0) > 0), None)
            if slot is None:
                continue
            need[(slot, g["label"], stratum)] -= 1
            g["stratum"] = stratum
            chosen[slot].append(g)
        if any(need.values()):
            sys.stderr.write(f"quotas not filled: {need}\n")
            return 1
        items = {}
        for split, gs in chosen.items():
            out = []
            for g in sorted(gs, key=lambda g: g["query"]["ordinal"]):
                q = g["query"]
                probe = ambiguity.Probe(q["ordinal"], q["title"], q["authors"], q["year"])
                cands = base.candidates(probe)
                cand_fields = []
                for c in cands:
                    r = ix.conn.execute(
                        "SELECT title, authors, journal, original_year FROM event WHERE event_id = ?", (c.event_id,)
                    ).fetchone()
                    cand_fields.append(dict(zip(advisory.BUNDLE_FIELDS, r, strict=True)))
                bundle = advisory.make_bundle(
                    {"title": q["title"], "authors": q["authors"], "journal": q["journal"], "original_year": q["year"]},
                    cand_fields,
                )
                out.append(
                    {
                        "group_query_event": f"ev-{q['ordinal']:07d}",
                        "label": g["label"],
                        "target": g["target"],
                        "stratum": g["stratum"],
                        "strata_flags": {k: g[k] for k in ("mixed_event", "shared_notice", "notice_also_original")},
                        "query_notice_key": f"doi:{q['nd']}" if q["nd"] else None,
                        "candidates": [{"candidate_id": f"c{i}", **c.__dict__} for i, c in enumerate(cands, 1)],
                        "candidate_recall_at_5": None
                        if g["target"] is None
                        else any(c.anchor == g["target"] for c in cands),
                        "bundle": bundle,
                        "bundle_sha256": hashlib.sha256(canonical(bundle).encode()).hexdigest(),
                    }
                )
            items[split] = out
    # Thresholds on the tuning split only.
    grid = []
    for ts in ambiguity.TAU_S_GRID:
        for tm in ambiguity.TAU_M_GRID:
            correct = 0
            for it in items["tuning"]:
                cands = [
                    ambiguity.Candidate(
                        **{k: c[k] for k in ("anchor", "event_id", "score", "cos_title", "year", "author")}
                    )
                    for c in it["candidates"]
                ]
                decision, anchor = ambiguity.decide(cands, ts, tm)
                ok = (it["label"] == "positive" and decision == "select" and anchor == it["target"]) or (
                    it["label"] == "negative" and decision == "abstain"
                )
                correct += ok
            grid.append({"tau_s": ts, "tau_m": tm, "tuning_correct": correct, "tuning_n": len(items["tuning"])})
    best = max(grid, key=lambda g: (g["tuning_correct"], g["tau_s"], g["tau_m"]))
    protocol = {
        "protocol_version": "1.0.0",
        "frozen_before_any_prediction": True,
        "specification": "docs/verification/stage-02/SPECIFICATION.md section 12.3",
        "task": "source-established masking (controlled); not natural missing-identifier accuracy",
        "seed": SEED,
        "quotas": QUOTAS,
        "similar_title_cos": SIMILAR_TITLE_COS,
        "groups_examined_for_draw": examined,
        "baseline_version": ambiguity.BASELINE_VERSION,
        "tuning_grid": grid,
        "frozen_thresholds": {"tau_s": best["tau_s"], "tau_m": best["tau_m"]},
        "metrics": [
            "primary_accuracy",
            "selection_precision",
            "coverage",
            "false_selections_on_negatives",
            "positive_recall",
            "abstention",
            "candidate_recall_at_5",
            "wilson_95",
            "mcnemar_b_c_exact_one_sided_p",
        ],
        "admission_gate": {
            "min_eligible_groups": 120,
            "min_accuracy_gain_pp": 10,
            "max_p": 0.05,
            "min_selection_coverage": 0.60,
            "false_selections_on_negatives": "not above baseline",
            "notice_original_confusions": 0,
            "prohibited_fact_writes": 0,
            "resource_limits": "met",
        },
        "model_route": "pending owner decision (session agent facility; see route-pilot-2026-10-27.json)",
        "no_heldout_revision": "No prompt, threshold or bundle change after any held-out prediction; no retries.",
        "splits": items,
    }
    text = json.dumps(protocol, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    (args.out / "protocol.json").write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "protocol_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "thresholds": protocol["frozen_thresholds"],
                "tuning_best": best,
                "examined": examined,
                "recall_at_5_heldout_pos": sum(
                    bool(i["candidate_recall_at_5"]) for i in items["heldout"] if i["label"] == "positive"
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
