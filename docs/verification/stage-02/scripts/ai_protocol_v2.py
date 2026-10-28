"""AI Protocol v2 for the Evidence Ambiguity Investigator (docs/verification/stage-02/ai/v2/PROTOCOL_V2.md).

Task: controlled recovery of a masked source identifier. A query record with a valid original DOI has its
identifiers removed (the bundle carries no identifier); the correct answer is the candidate that carries the
same original DOI, or abstention when no other record carries it. This is not natural missing-identifier
resolution and not human-adjudicated bibliographic identity.

Subcommands, in the order the protocol runs them (each writes one JSON file under --out):

  audit    development pool only: label/exclusion census, strata, baseline errors, recall@5 (no model)
  devset   development cases for screening and calibration: the exposed v1 groups (relabeled) plus a
           seeded stratified fresh development sample
  draw     the confirmatory holdout, by the preregistered quotas in protocol-v2.json, with the separation
           proof, the baseline decisions and the attainability report (no model)

The draw uses only label and retrieval features (candidate titles, years, authors), never a baseline or model
decision. Nothing here writes to the index (it is opened read-only).

Run: python docs/verification/stage-02/scripts/ai_protocol_v2.py {audit|devset|draw} --index INDEX --out DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_protocol import groups

from citerift.retraction import advisory, ambiguity, stats
from citerift.retraction.canonical import canonical
from citerift.retraction.query import Index
from citerift.retraction.search import title_tokens

PROTOCOL_VERSION = "2.0.0"
SEED = 20261028
DEV_SHARE = 3  # groups whose split hash mod 10 is below this are development; the rest may enter the holdout
V1_PROTOCOL = Path("docs/verification/stage-02/ai/protocol.json")
STAGE_DOCS = Path("docs/verification/stage-02")
# Label repair (PROTOCOL_V2.md 2): a DOI shared with a record whose title barely overlaps is a collision of
# distinct works (for example a conference-supplement DOI), not a source-established same-work link.
COLLISION_TITLE_JACCARD = 0.5
# Strata from retrieval features (PROTOCOL_V2.md 3), fixed before any decision is seen.
AGREE_TITLE_COS = 0.9
COMPETITOR_COS = 0.6
NEAR_DUPLICATE_COS = 0.85
SIMILAR_TITLE_COS = 0.6


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def _split_hash(group_min_ordinal: int) -> int:
    return int(hashlib.sha256(f"{SEED}:{group_min_ordinal}".encode()).hexdigest(), 16)


def referenced_keys() -> set[str]:
    """Event ids and DOI keys named anywhere in the Stage 02 documents and evidence before v2 (prior use)."""
    out: set[str] = set()
    for p in sorted(STAGE_DOCS.rglob("*")):
        if p.is_file() and "ai/v2" not in p.as_posix() and p.suffix in (".json", ".md", ".txt", ".jsonl", ".py"):
            text = p.read_text(encoding="utf-8", errors="replace")
            out |= set(re.findall(r"ev-[0-9]{7}", text))
            out |= {"doi:" + d for d in re.findall(r"doi:(10\.[^\"' ,)\]]+)", text)}
    return out


class Population:
    """Every lineage group of the index with its v2 label, exclusion reason and prior-use status."""

    def __init__(self, ix: Index):
        self.ix = ix
        self.base = ambiguity.Baseline(ix)
        self.rec: dict[int, tuple[Any, ...]] = {}
        self.by_doi: dict[str, list[int]] = {}
        self.by_pmid: dict[str, list[int]] = {}
        for row in ix.conn.execute(
            "SELECT ordinal, original_doi, original_pmid, title, authors, original_year, journal FROM event"
        ):
            self.rec[row[0]] = row
            if row[1]:
                self.by_doi.setdefault(row[1], []).append(row[0])
            if row[2]:
                self.by_pmid.setdefault(row[2], []).append(row[0])
        proto = json.loads(V1_PROTOCOL.read_text(encoding="utf-8"))
        self.v1_events = {it["group_query_event"]: split for split, s in proto["splits"].items() for it in s}
        self.referenced = referenced_keys()
        self.cases: list[dict[str, Any]] = []
        self.census: Counter[str] = Counter()
        for members in groups(ix).values():
            self._add(members)
        self.cases.sort(key=lambda c: c["group_min_ordinal"])

    def _add(self, members: list[dict[str, Any]]) -> None:
        q = next((e for e in members if e["od"]), None)  # smallest ordinal with a valid original DOI (as v1)
        if q is None:
            self.census["excluded/no_original_doi"] += 1
            return
        events = {f"ev-{e['ordinal']:07d}" for e in members}
        keys = {f"doi:{e[k]}" for e in members for k in ("od", "nd") if e[k]}
        v1 = sorted(events & set(self.v1_events))
        prior = "v1_" + self.v1_events[v1[0]] if v1 else ("referenced" if (events | keys) & self.referenced else None)
        targets = [o for o in self.by_doi[q["od"]] if o != q["ordinal"]]
        label, reason = ("positive", None) if targets else ("negative", None)
        q_tokens = title_tokens(q["title"])
        if targets:
            if any(q["op"] and self.rec[o][2] and self.rec[o][2] != q["op"] for o in targets):
                reason = "conflicting_original_pmid"
            elif any(_jaccard(q_tokens, title_tokens(self.rec[o][3])) < COLLISION_TITLE_JACCARD for o in targets):
                reason = "doi_shared_by_distinct_titles"
        elif q["op"] and any(self.rec[o][1] != q["od"] for o in self.by_pmid.get(q["op"], []) if o != q["ordinal"]):
            reason = "pmid_shared_with_different_doi"
        status = f"excluded/{reason}" if reason else label
        self.census[f"{prior or 'fresh'}/{status}"] += 1
        self.cases.append(
            {
                "group_min_ordinal": min(e["ordinal"] for e in members),
                "group_events": sorted(events),
                "group_keys": sorted(keys),
                "query": q,
                "label": label,
                "exclusion": reason,
                "prior_use": prior,
                "target": f"doi:{q['od']}" if targets else None,
                "target_ordinals": targets,
                "split": "development"
                if prior or _split_hash(min(e["ordinal"] for e in members)) % 10 < DEV_SHARE
                else "holdout_pool",
            }
        )

    def features(self, case: dict[str, Any]) -> dict[str, Any]:
        """Candidates, stratum and bundle of one case. Uses retrieval features only, never a decision."""
        q = case["query"]
        probe = ambiguity.Probe(q["ordinal"], q["title"], q["authors"], q["year"])
        cands = self.base.candidates(probe)
        if case["label"] == "positive":
            qt = title_tokens(q["title"])
            agree = any(
                self.rec[o][5] == q["year"]
                and ambiguity._author_score(q["authors"], self.rec[o][4]) >= 0.5
                and self.base.cosine(qt, title_tokens(self.rec[o][3])) >= AGREE_TITLE_COS
                for o in case["target_ordinals"]
            )
            competitor = any(c.anchor != case["target"] and c.cos_title >= COMPETITOR_COS for c in cands)
            stratum = "disagreement" if not agree else ("competitor" if competitor else "other")
        else:
            top = cands[0].cos_title if cands else 0.0
            stratum = (
                "near_duplicate"
                if top >= NEAR_DUPLICATE_COS
                else ("similar_title" if top >= SIMILAR_TITLE_COS else "other")
            )
        fields = []
        for c in cands:
            r = self.ix.conn.execute(
                "SELECT title, authors, journal, original_year FROM event WHERE event_id = ?", (c.event_id,)
            ).fetchone()
            fields.append(dict(zip(advisory.BUNDLE_FIELDS, r, strict=True)))
        bundle = advisory.make_bundle(
            {"title": q["title"], "authors": q["authors"], "journal": q["journal"], "original_year": q["year"]}, fields
        )
        return {
            "group_query_event": f"ev-{q['ordinal']:07d}",
            "group_min_ordinal": case["group_min_ordinal"],
            "label": case["label"],
            "target": case["target"],
            "stratum": stratum,
            "prior_use": case["prior_use"],
            "query_notice_key": f"doi:{q['nd']}" if q["nd"] else None,
            "query_title_script": _script(q["title"]),
            "candidates": [{"candidate_id": f"c{i}", **c.__dict__} for i, c in enumerate(cands, 1)],
            "candidate_recall_at_5": None if case["target"] is None else any(c.anchor == case["target"] for c in cands),
            "bundle": bundle,
            "bundle_sha256": hashlib.sha256(canonical(bundle).encode()).hexdigest(),
        }


def _script(text: str) -> str:
    if re.search(r"[؀-ۿ]", text or ""):
        return "arabic"
    if re.search(r"[一-鿿぀-ヿ가-힯]", text or ""):
        return "cjk"
    if re.search(r"[Ѐ-ӿ]", text or ""):
        return "cyrillic"
    return "latin_or_other"


def baseline_correct(item: dict[str, Any]) -> tuple[bool, str, str | None]:
    cands = [
        ambiguity.Candidate(**{k: c[k] for k in ("anchor", "event_id", "score", "cos_title", "year", "author")})
        for c in item["candidates"]
    ]
    decision, anchor = ambiguity.decide(cands, ambiguity.FROZEN_TAU_S, ambiguity.FROZEN_TAU_M)
    ok = (item["label"] == "positive" and decision == "select" and anchor == item["target"]) or (
        item["label"] == "negative" and decision == "abstain"
    )
    return ok, decision, anchor


def _write(out: Path, name: str, data: Any) -> str:
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    (out / name).write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest()


def cmd_audit(pop: Population, out: Path) -> dict[str, Any]:
    dev = [c for c in pop.cases if c["split"] == "development" and c["prior_use"] is None and not c["exclusion"]]
    table: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    recall: Counter[str] = Counter()
    for case in dev:
        item = pop.features(case)
        key = f"{item['label']}/{item['stratum']}"
        ok, _d, _a = baseline_correct(item)
        table[key] += 1
        errors[key] += not ok
        recall[key] += bool(item["candidate_recall_at_5"])
    v1 = [c for c in pop.cases if c["prior_use"] and c["prior_use"].startswith("v1_")]
    v1_items = [pop.features(c) for c in v1 if not c["exclusion"]]
    v1_table: Counter[str] = Counter(f"{i['label']}/{i['stratum']}" for i in v1_items)
    v1_err: Counter[str] = Counter(f"{i['label']}/{i['stratum']}" for i in v1_items if not baseline_correct(i)[0])
    holdout_pool: Counter[str] = Counter(
        c["label"] for c in pop.cases if c["split"] == "holdout_pool" and not c["exclusion"]
    )
    result = {
        "protocol_version": PROTOCOL_VERSION,
        "what": "development pool only; baseline decisions, no model; the holdout pool is counted by label only",
        "census": dict(sorted(pop.census.items())),
        "fresh_development_pool": {
            k: {
                "n": table[k],
                "baseline_errors": errors[k],
                "baseline_error_rate": errors[k] / table[k],
                "baseline_error_rate_wilson_95": stats.wilson(errors[k], table[k]),
                "recall_at_5": recall[k] / table[k] if k.startswith("positive") else None,
            }
            for k in sorted(table)
        },
        "v1_groups_relabeled": {
            "excluded": sorted((f"ev-{c['query']['ordinal']:07d}", c["exclusion"]) for c in v1 if c["exclusion"]),
            "strata": {k: {"n": v1_table[k], "baseline_errors": v1_err[k]} for k in sorted(v1_table)},
        },
        "holdout_pool_by_label": dict(holdout_pool),
    }
    sha = _write(out, "dev-audit.json", result)
    return {"dev-audit.json": sha}


def _stratified(
    pop: Population, cases: list[dict[str, Any]], quotas: dict[str, int], seed: int
) -> list[dict[str, Any]]:
    """Seeded shuffle, then take cases in order while their (label/stratum) quota is open. Strata come from
    retrieval features only; a case is never chosen or skipped for its baseline or model outcome."""
    rng = random.Random(seed)  # noqa: S311 - a reproducible draw, not a secret
    order = sorted(cases, key=lambda c: c["group_min_ordinal"])
    rng.shuffle(order)
    need = dict(quotas)
    chosen = []
    for case in order:
        if not any(need.values()):
            break
        if not any(n for k, n in need.items() if k.startswith(case["label"] + "/")):
            continue
        item = pop.features(case)
        key = f"{item['label']}/{item['stratum']}"
        if need.get(key, 0) > 0:
            need[key] -= 1
            chosen.append(item)
    chosen.sort(key=lambda i: i["group_min_ordinal"])
    return [*chosen, {"unfilled": need}] if any(need.values()) else chosen


def cmd_devset(pop: Population, out: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    v1 = [pop.features(c) for c in pop.cases if (c["prior_use"] or "").startswith("v1_") and not c["exclusion"]]
    fresh_pool = [c for c in pop.cases if c["split"] == "development" and c["prior_use"] is None and not c["exclusion"]]
    fresh = _stratified(pop, fresh_pool, protocol["development_quotas"], SEED + 1)
    if fresh and "unfilled" in fresh[-1]:
        raise SystemExit(f"development quotas not filled: {fresh[-1]}")
    items = sorted(v1 + fresh, key=lambda i: i["group_min_ordinal"])
    sha = _write(out, "dev-set.json", {"protocol_version": PROTOCOL_VERSION, "items": items})
    return {"dev-set.json": sha, "n": len(items), "v1": len(v1), "fresh": len(fresh)}


def cmd_draw(pop: Population, out: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    pool = [c for c in pop.cases if c["split"] == "holdout_pool" and not c["exclusion"]]
    if any(c["prior_use"] for c in pool):
        raise SystemExit("a holdout-pool group has prior use")
    items = _stratified(pop, pool, protocol["holdout_quotas"], SEED + 2)
    if items and "unfilled" in items[-1]:
        raise SystemExit(f"holdout quotas not filled: {items[-1]}")
    # Separation proof: no event or identifier key of a holdout group occurs in any development or prior group.
    hold = {i["group_min_ordinal"] for i in items}
    other = [
        c for c in pop.cases if c["group_min_ordinal"] not in hold and (c["split"] == "development" or c["prior_use"])
    ]
    dev_events = {e for c in other for e in c["group_events"]}
    dev_keys = {k for c in other for k in c["group_keys"]}
    hold_cases = [c for c in pop.cases if c["group_min_ordinal"] in hold]
    overlap_events = sorted({e for c in hold_cases for e in c["group_events"]} & dev_events)
    overlap_keys = sorted({k for c in hold_cases for k in c["group_keys"]} & dev_keys)
    separation = {
        "holdout_groups": len(hold_cases),
        "development_or_prior_groups": len(other),
        "shared_events": overlap_events,
        "shared_identifier_keys": overlap_keys,
        "referenced_in_prior_documents": sorted(
            {e for c in hold_cases for e in c["group_events"] + c["group_keys"]} & pop.referenced
        ),
        "separated": not overlap_events and not overlap_keys,
    }
    manifest_sha = _write(out, "holdout-manifest.json", {"protocol_version": PROTOCOL_VERSION, "items": items})
    # Baseline and attainability (no model): the oracle selects the target when it is a candidate and abstains
    # on negatives, so its errors are the positives without the target in the top five.
    base = [baseline_correct(i) for i in items]
    b_err = sum(not ok for ok, _d, _a in base)
    oracle_err = sum(1 for i in items if i["label"] == "positive" and not i["candidate_recall_at_5"])
    max_fixable = b_err - oracle_err if b_err >= oracle_err else 0
    need_errors = int(b_err * 0.75)  # AI errors allowed for a 25% relative reduction (floor)
    best_p = stats.mcnemar_exact_one_sided(0, max_fixable) if max_fixable else 1.0
    attain = {
        "n": len(items),
        "baseline_errors": b_err,
        "baseline_correct": len(items) - b_err,
        "baseline_false_selections_on_negatives": sum(
            1 for i, (_ok, d, _a) in zip(items, base, strict=True) if i["label"] == "negative" and d == "select"
        ),
        "baseline_positive_recall": sum(
            1 for i, (ok, _d, _a) in zip(items, base, strict=True) if i["label"] == "positive" and ok
        )
        / max(1, sum(i["label"] == "positive" for i in items)),
        "candidate_recall_at_5": sum(bool(i["candidate_recall_at_5"]) for i in items if i["label"] == "positive")
        / max(1, sum(i["label"] == "positive" for i in items)),
        "oracle_errors": oracle_err,
        "max_relative_error_reduction": (b_err - oracle_err) / b_err if b_err else None,
        "ai_errors_allowed_for_25pct": need_errors,
        "best_case_paired_p": best_p,
        "min_rule": protocol["attainability_rule"],
        "per_stratum": {
            k: {
                "n": sum(1 for i in items if f"{i['label']}/{i['stratum']}" == k),
                "baseline_errors": sum(
                    1
                    for i, (ok, _d, _a) in zip(items, base, strict=True)
                    if f"{i['label']}/{i['stratum']}" == k and not ok
                ),
            }
            for k in sorted({f"{i['label']}/{i['stratum']}" for i in items})
        },
        "baseline_correct_vector": [ok for ok, _d, _a in base],
        "baseline_decisions": [[d, a] for _ok, d, a in base],
    }
    rule = protocol["attainability_rule"]
    attain["attainable"] = b_err >= rule["min_baseline_errors"] and best_p < rule["max_best_case_p"]
    sha = _write(out, "holdout-attainability.json", {"separation": separation, "attainability": attain})
    return {
        "holdout-manifest.json": manifest_sha,
        "holdout-attainability.json": sha,
        "separated": separation["separated"],
        "attainable": attain["attainable"],
        "baseline_errors": b_err,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=("audit", "devset", "draw"))
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    with Index(args.index) as ix:
        pop = Population(ix)
        if args.command == "audit":
            result = cmd_audit(pop, args.out)
        else:
            protocol = json.loads((args.out / "protocol-v2.json").read_text(encoding="utf-8"))
            result = (
                cmd_devset(pop, args.out, protocol) if args.command == "devset" else cmd_draw(pop, args.out, protocol)
            )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
