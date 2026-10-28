"""Exact statistics for the frozen evaluation protocol (SPECIFICATION.md 12.3)."""

from __future__ import annotations

import math

Z95 = 1.959963984540054


def wilson(successes: int, n: int, z: float = Z95) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion; None when n is 0."""
    if n <= 0:
        return None
    if not 0 <= successes <= n:
        raise ValueError("successes must be between 0 and n")
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar_exact_one_sided(b: int, c: int) -> float:
    """P(X >= c) for X ~ Binomial(b + c, 1/2): evidence that the model (right in the c discordant groups) beats
    the baseline (right in the b discordant groups). 1.0 when there are no discordant groups."""
    if b < 0 or c < 0:
        raise ValueError("counts must be non-negative")
    n = b + c
    if n == 0:
        return 1.0
    return float(sum(math.comb(n, k) for k in range(c, n + 1)) / 2**n)
