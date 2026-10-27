"""Deterministic ambiguity baseline: candidate works for an event whose identifiers are missing or masked
(SPECIFICATION.md 12.2). Read-only; it suggests candidates and never changes any record."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from citerift.retraction.query import Index
from citerift.retraction.search import author_surnames, title_tokens

BASELINE_VERSION = "citerift-ambiguity-baseline/1.0.0"
DF_CUTOFF = 2000
MAX_POOL = 200
TOP_K = 5
WEIGHTS = (0.6, 0.2, 0.2)
TAU_S_GRID = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
TAU_M_GRID = (0.00, 0.05, 0.10)
# Chosen on the 40 tuning groups only and frozen with the protocol (docs/verification/stage-02/ai/protocol.json).
FROZEN_TAU_S = 0.85
FROZEN_TAU_M = 0.10


@dataclass(frozen=True)
class Probe:
    """The fields of the event being linked; its own identifiers are not used."""

    ordinal: int | None
    title: str
    authors: str
    original_year: int | None


@dataclass(frozen=True)
class Candidate:
    anchor: str
    event_id: str
    score: float
    cos_title: float
    year: float
    author: float


def _year_score(a: int | None, b: int | None) -> float:
    if a is None or b is None:
        return 0.5
    if a == b:
        return 1.0
    return 0.5 if abs(a - b) == 1 else 0.0


def _author_score(a: str, b: str) -> float:
    sa, sb = set(author_surnames(a)), set(author_surnames(b))
    if not sa or not sb:
        return 0.5
    return len(sa & sb) / len(sa | sb)


class Baseline:
    def __init__(self, index: Index):
        self.index = index
        self.conn = index.conn
        self.n_docs = self.conn.execute("SELECT COUNT(*) FROM event WHERE original_doi IS NOT NULL").fetchone()[0]
        self._df: dict[str, int] = {}

    def df(self, token: str) -> int:
        if token not in self._df:
            row = self.conn.execute("SELECT df FROM token_df WHERE token = ?", (token,)).fetchone()
            self._df[token] = row[0] if row else 0
        return self._df[token]

    def idf(self, token: str) -> float:
        return math.log(max(self.n_docs, 1) / max(self.df(token), 1))

    def cosine(self, a: list[str], b: list[str]) -> float:
        wa = {t: self.idf(t) for t in a}
        wb = {t: self.idf(t) for t in b}
        na = math.sqrt(sum(w * w for w in wa.values()))
        nb = math.sqrt(sum(w * w for w in wb.values()))
        if na == 0 or nb == 0:
            return 0.0
        return sum(wa[t] * wb[t] for t in wa.keys() & wb.keys()) / (na * nb)

    def pool(self, probe: Probe) -> list[str]:
        """Up to 200 DOI-anchored event ids sharing a title token with df <= 2,000, by summed IDF."""
        summed: dict[str, float] = {}
        for tok in title_tokens(probe.title):
            df = self.df(tok)
            if df == 0 or df > DF_CUTOFF:
                continue
            weight = self.idf(tok)
            for (event_id,) in self.conn.execute("SELECT event_id FROM title_token WHERE token = ?", (tok,)):
                summed[event_id] = summed.get(event_id, 0.0) + weight
        own = None if probe.ordinal is None else f"ev-{probe.ordinal:07d}"
        summed.pop(own or "", None)
        ranked = sorted(summed.items(), key=lambda kv: (-kv[1], kv[0]))
        return [eid for eid, _ in ranked[:MAX_POOL]]

    def candidates(self, probe: Probe, k: int = TOP_K) -> list[Candidate]:
        ids = self.pool(probe)
        if not ids:
            return []
        rows = []
        for i in range(0, len(ids), 500):
            chunk = ids[i : i + 500]
            marks = ",".join("?" * len(chunk))
            rows += self.conn.execute(
                f"SELECT event_id, anchor, title, authors, original_year FROM event WHERE event_id IN ({marks})",  # noqa: S608
                chunk,
            ).fetchall()
        q_tokens = title_tokens(probe.title)
        best: dict[str, Candidate] = {}
        w_t, w_y, w_a = WEIGHTS
        for event_id, anchor, title, authors, year in rows:
            cos = self.cosine(q_tokens, title_tokens(title))
            ys = _year_score(probe.original_year, year)
            au = _author_score(probe.authors, authors)
            score = round(w_t * cos + w_y * ys + w_a * au, 12)
            cand = Candidate(anchor, event_id, score, round(cos, 12), ys, round(au, 12))
            prev = best.get(anchor)
            if prev is None or (cand.score, prev.event_id) > (prev.score, cand.event_id):
                best[anchor] = cand
        ranked = sorted(best.values(), key=lambda c: (-c.score, c.anchor))
        return ranked[:k]


def decide(cands: list[Candidate], tau_s: float, tau_m: float) -> tuple[str, str | None]:
    """('select', anchor) iff top score >= tau_s and its margin over the second >= tau_m; else abstain."""
    if not cands:
        return "abstain", None
    second = cands[1].score if len(cands) > 1 else 0.0
    if cands[0].score >= tau_s - 1e-12 and cands[0].score - second >= tau_m - 1e-12:
        return "select", cands[0].anchor
    return "abstain", None


def probe_for_event(index: Index, event_id: str) -> Probe:
    e = index.event_by_id(event_id)
    if e is None:
        raise KeyError(event_id)
    return Probe(e["ordinal"], e["title"], e["authors"], e["original_year"])


def suggest(index: Index, event_id: str, tau_s: float, tau_m: float) -> dict[str, Any]:
    """Baseline suggestion for one event (CLI ``ambiguity``). An exact identifier wins (decision ``exact``)."""
    e = index.event_by_id(event_id)
    if e is None:
        raise KeyError(event_id)
    if e["original_doi"] or e["original_pmid"]:
        return {
            "baseline_version": BASELINE_VERSION,
            "event_id": event_id,
            "decision": "exact",
            "anchor": e["anchor"],
            "candidates": [],
            "advisory": True,
        }
    probe = Probe(e["ordinal"], e["title"], e["authors"], e["original_year"])
    cands = Baseline(index).candidates(probe)
    decision, anchor = decide(cands, tau_s, tau_m)
    return {
        "baseline_version": BASELINE_VERSION,
        "event_id": event_id,
        "decision": decision,
        "anchor": anchor,
        "thresholds": {"tau_s": tau_s, "tau_m": tau_m},
        "candidates": [c.__dict__ for c in cands],
        "advisory": True,
        "note": "A suggestion for review. It is not a link and changes no record.",
    }
