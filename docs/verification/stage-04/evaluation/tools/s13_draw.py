"""Stage 04 Step 13: the seed and the draw order (PREREGISTRATION.md section 4).

Nothing here may run for the final sample before the owner has accepted the committed pre-registration.

**Seed.** A public randomness beacon fixes the seed after acceptance, so neither the executor nor anyone else can
choose or predict it when the pre-registration is committed:

- beacon: drand ``quicknet`` (chain hash ``52db9ba7...e971``, genesis 1692803367, period 3 s, unchained BLS); a round's
  ``randomness`` is the SHA-256 of its ``signature``, which ``check_beacon`` verifies;
- round ``R``: the first round whose time is at least one hour after the owner's acceptance message
  (``round_for``); it is fixed by that message's timestamp alone;
- the round is read from at least two of the listed mirrors, which must agree; if no two agree within 24 hours of
  the round time, the draw stops for an owner decision (no other round is ever used);
- seed = SHA-256(``citerift-stage04-eval-seed/1|<pre-registration digest>|<R>|<randomness>``).

**Order.** Within each (wiki, stratum), frame members are ordered by SHA-256(``citerift-stage04-eval-order/1|<seed>|
<wiki>|<stratum>|<page_id>``), ascending. The order depends only on the seed and the page id: never on content, the
engine, a label or an earlier failure.

**Blocks** (``PARAMETERS.json`` ``sampling``): per language, primary positions per stratum, then reserve positions per
stratum, then expansion blocks; ``plan`` lists every position with its block and its replacement rule.

Usage after acceptance (never before):

    python -P .../s13_draw.py seed --acceptance-time 2026-11-18T12:00:00Z --prereg-digest D --out SEED.json
    python -P .../s13_draw.py plan --frame FRAME.json --seed SEED.json --out DRAW.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s13_common import EVALUATION, LANGUAGES, read_json, sha256_hex, write_json

CHAIN = "52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971"
GENESIS = 1692803367
PERIOD = 3
DELAY_S = 3600
MIRRORS = ("https://api.drand.sh", "https://api2.drand.sh", "https://api3.drand.sh", "https://drand.cloudflare.com")
SEED_TAG = "citerift-stage04-eval-seed/1"
ORDER_TAG = "citerift-stage04-eval-order/1"


def round_for(acceptance_time: datetime) -> int:
    """The first quicknet round whose time is >= acceptance time + one hour."""
    target = int(acceptance_time.timestamp()) + DELAY_S
    if target <= GENESIS:
        return 1
    return -(-(target - GENESIS) // PERIOD) + 1


def round_time(r: int) -> int:
    return GENESIS + (r - 1) * PERIOD


def check_beacon(beacon: dict[str, Any], r: int) -> str:
    """The verified randomness of round ``r`` (randomness = SHA-256(signature) for this unchained scheme)."""
    if beacon.get("round") != r:
        raise ValueError(f"beacon round {beacon.get('round')} is not {r}")
    sig = bytes.fromhex(str(beacon["signature"]))
    randomness = hashlib.sha256(sig).hexdigest()
    if "randomness" in beacon and beacon["randomness"] != randomness:
        raise ValueError("the beacon's randomness is not the SHA-256 of its signature")
    return randomness


def seed_of(prereg_digest: str, r: int, randomness: str) -> str:
    return sha256_hex(f"{SEED_TAG}|{prereg_digest}|{r}|{randomness}".encode())


def order_key(seed: str, wiki: str, stratum: str, page_id: int) -> str:
    return sha256_hex(f"{ORDER_TAG}|{seed}|{wiki}|{stratum}|{page_id}".encode())


def ordered(seed: str, wiki: str, stratum: str, members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [m for m in members if m["stratum"] == stratum]
    return sorted(rows, key=lambda m: order_key(seed, wiki, stratum, int(m["page_id"])))


def _take(
    queue: list[dict[str, Any]],
    taken: dict[str, int],
    positions: list[dict[str, Any]],
    seed: str,
    wiki: str,
    stratum: str,
    block: str,
    n: int,
) -> None:
    for _ in range(n):
        if taken[stratum] >= len(queue):
            return
        m = queue[taken[stratum]]
        taken[stratum] += 1
        positions.append(
            {
                "wiki": wiki,
                "page_id": m["page_id"],
                "title": m["title"],
                "stratum": stratum,
                "block": block,
                "rank_in_stratum": taken[stratum],
                "order_key": order_key(seed, wiki, stratum, int(m["page_id"])),
            }
        )


def plan(frame: dict[str, Any], seed: str, sampling: dict[str, Any]) -> dict[str, Any]:
    """Every drawn position per language: primary, reserve (same stratum, in order) and expansion blocks."""
    out: dict[str, Any] = {}
    for wiki in LANGUAGES:
        members = frame["frames"][wiki]["frame"]
        queues = {s: ordered(seed, wiki, s, members) for s in ("S1", "S2")}
        taken = {"S1": 0, "S2": 0}
        positions: list[dict[str, Any]] = []
        alloc = sampling["allocation"][wiki]
        for block in ("primary", "reserve"):
            for s in ("S1", "S2"):
                _take(queues[s], taken, positions, seed, wiki, s, block, alloc[block][s])
        for k in range(1, sampling["expansion"]["max_blocks"] + 1):
            need = sampling["expansion"]["block_size"]
            for s in sampling["expansion"]["stratum_order"]:
                before = len(positions)
                _take(queues[s], taken, positions, seed, wiki, s, f"expansion-{k}", need)
                need -= len(positions) - before
                if need == 0:
                    break
        out[wiki] = {"positions": positions, "available_by_stratum": {s: len(q) for s, q in queues.items()}}
    return out


def fetch_round(r: int, timeout: float = 20.0) -> dict[str, Any]:
    """Round ``r`` from every mirror; at least two must answer with the same verified randomness."""
    answers: dict[str, Any] = {}
    for base in MIRRORS:
        url = f"{base}/{CHAIN}/public/{r}"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - fixed https mirrors
                beacon = json.loads(resp.read())
            answers[base] = {"beacon": beacon, "randomness": check_beacon(beacon, r)}
        except (OSError, ValueError, KeyError) as exc:
            answers[base] = {"error": f"{type(exc).__name__}: {exc}"[:300]}
    values = [a["randomness"] for a in answers.values() if "randomness" in a]
    agreed = {v for v in values if values.count(v) >= 2}
    if len(agreed) != 1:
        raise RuntimeError(f"round {r}: no two mirrors agree: {answers}")
    return {"round": r, "round_time": round_time(r), "randomness": agreed.pop(), "mirrors": answers}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 04 Step 13 seed and draw order")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seed")
    s.add_argument("--acceptance-time", required=True, help="UTC time of the owner's acceptance message")
    s.add_argument("--prereg-digest", required=True)
    s.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("plan")
    p.add_argument("--frame", type=Path, required=True)
    p.add_argument("--seed", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "seed":
        t = datetime.fromisoformat(a.acceptance_time.replace("Z", "+00:00")).astimezone(UTC)
        r = round_for(t)
        if datetime.now(UTC).timestamp() < round_time(r):
            sys.exit(f"round {r} is in the future ({datetime.fromtimestamp(round_time(r), UTC).isoformat()})")
        beacon = fetch_round(r)
        seed = seed_of(a.prereg_digest, r, beacon["randomness"])
        write_json(a.out, {"acceptance_time": t.isoformat(), "prereg_digest": a.prereg_digest, **beacon, "seed": seed})
        print(seed)
    else:
        sampling = read_json(EVALUATION / "PARAMETERS.json")["sampling"]
        seed_doc = read_json(a.seed)
        write_json(a.out, {"seed": seed_doc["seed"], "plan": plan(read_json(a.frame), seed_doc["seed"], sampling)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
