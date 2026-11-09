"""[D-036 copy; see the end of this docstring.]
Interval estimates of the confirmation campaign (AMENDMENT_2026-11-02_CONFIRMATION.md section 8, "Estimands").

Usage (from the repository root): python intervals.py SCORES_JSON CHALLENGE_JSON > intervals.json

Written after the scores existed; it computes nothing that decides a gate. The gates are those of the scores file.

- Article-cluster bootstrap, 95 % percentile intervals, with the frozen scorer's own ``aggregate``, seed and number
  of resamples (``evaluate.py``), over the per-article rows of each language and label set. The frozen
  ``bootstrap`` covers eight ratios; this adds unit precision and recall (G5c, G5d), the key-error rate (G2), role
  agreement (G3b) and binding accuracy (G4c), resampled the same way.
- For the zero-tolerance gates G2 (key errors among matched target identifiers), G3a (promotions among matched
  target identifiers) and G7 (fabricated negatives among labelled warnings), the exact one-sided 95 %
  Clopper-Pearson upper bound of the rate for the observed count.
- For the warning challenge, the exact two-sided 95 % Clopper-Pearson interval of sensitivity.


Copied for the D-036 confirmation (AMENDMENT_2026-11-04_D036_CONFIRMATION.md) from
``../../confirmation-2026-11/scripts/`` with only the changes that amendment lists.
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/protocol/scripts"))
import evaluate as v1  # noqa: E402 - frozen scorer, unchanged

KEYS = (
    ("identifiers", "precision"),
    ("identifiers", "recall"),
    ("identifiers", "key_error_rate"),
    ("identifiers", "role_agreement"),
    ("uses", "precision"),
    ("uses", "recall"),
    ("uses", "binding_accuracy"),
    ("definitions", "precision"),
    ("definitions", "recall"),
    ("units", "precision"),
    ("units", "recall"),
    ("render", "precision"),
    ("render", "coverage"),
)


def binom_cdf(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def _solve(f: Any, target: float) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def cp_upper(k: int, n: int, alpha: float) -> float | None:
    """Exact upper bound: the p with P(X <= k | n, p) = alpha (1.0 when k = n)."""
    if n == 0:
        return None
    if k >= n:
        return 1.0
    return _solve(lambda p: binom_cdf(k, n, p), alpha)


def cp_lower(k: int, n: int, alpha: float) -> float | None:
    """Exact lower bound: the p with P(X >= k | n, p) = alpha (0.0 when k = 0)."""
    if n == 0:
        return None
    if k <= 0:
        return 0.0
    return 1.0 - _solve(lambda q: binom_cdf(n - k, n, q), alpha)


def bootstrap(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rng = random.Random(v1.BOOTSTRAP_SEED)  # noqa: S311 - seeded resampling, not security
    samples: dict[str, list[float]] = {f"{a}.{b}": [] for a, b in KEYS}
    for _ in range(v1.BOOTSTRAP_RESAMPLES):
        agg = v1.aggregate([rows[rng.randrange(len(rows))] for _ in rows])
        for a, b in KEYS:
            if agg[a][b] is not None:
                samples[f"{a}.{b}"].append(agg[a][b])
    out: dict[str, Any] = {}
    for k, vals in samples.items():
        vals.sort()
        out[k] = [vals[int(0.025 * (len(vals) - 1))], vals[int(0.975 * (len(vals) - 1))]] if vals else None
    return out


def main() -> int:
    scores = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    challenge = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    out: dict[str, Any] = {"procedure": __doc__, "gate": {}, "challenge": {}}
    for wiki, labs in scores["splits"]["gate"].items():
        for lab, res in labs.items():
            rows = [r["engine"] for r in res["per_article"]]
            agg = v1.aggregate(rows)
            ident = agg["identifiers"]
            matched = sum(r["identifiers"]["role_total"] for r in rows)
            labelled_warnings = sum(n for k, n in agg["markers"]["confusion"].items() if k.startswith("warning->"))
            out["gate"][f"{wiki}/{lab}"] = {
                "articles": len(rows),
                "point": {f"{a}.{b}": agg[a][b] for a, b in KEYS},
                "bootstrap_95": bootstrap(rows),
                "zero_tolerance_upper_95": {
                    "G2 key errors": {
                        "count": ident["key_errors"],
                        "n": matched,
                        "upper": cp_upper(ident["key_errors"], matched, 0.05),
                    },
                    "G3a promotions": {
                        "count": ident["promotions"],
                        "n": matched,
                        "upper": cp_upper(ident["promotions"], matched, 0.05),
                    },
                    "G7 fabricated negatives": {
                        "count": agg["markers"]["fabricated_negatives"],
                        "n": labelled_warnings,
                        "upper": cp_upper(agg["markers"]["fabricated_negatives"], labelled_warnings, 0.05),
                    },
                },
            }
    for lab, groups in challenge["labels"].items():
        for name, g in groups.items():
            if name == "per_article":
                continue
            n, k = g["labelled_warnings"], g["detected_warnings"]
            out["challenge"][f"{lab}/{name}"] = {
                "labelled_warnings": n,
                "detected": k,
                "fabricated_negatives": g["fabricated_negatives"],
                "sensitivity": g["sensitivity"],
                "sensitivity_cp_95": [cp_lower(k, n, 0.025), cp_upper(k, n, 0.025)] if n else None,
                "G7_upper_95": cp_upper(g["fabricated_negatives"], n, 0.05) if n else None,
            }
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
