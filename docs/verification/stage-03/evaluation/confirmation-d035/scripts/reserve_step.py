"""[D-035 copy; see the end of this docstring.]
One reserve decision of the confirmation campaign (AMENDMENT_2026-11-02_CONFIRMATION.md section 4), from committed
locked annotation counts only.

Usage (from the repository root): python reserve_step.py SELECTION_JSON CAPTURE_DIR LOCK_DIR [LOCK_DIR ...]

For each language, the included articles are the initial holdout plus every reserve block already in the capture
state, in order. Each included article is counted from its locked label with ``reserve_decision.counts`` (unchanged):

- an article without a bundle counts 0;
- an article with a bundle must have a locked label;
- every article of an included block must be resolved: an article the capture driver would still run (a pending
  deferral, an interrupted run) stops the decision, so that a decision never depends on when it was made (review
  R6, RR-7). A block is captured once its articles have runs; a block with some articles run and others not stops
  the decision too.

When the capture stopped at a ceiling or at the acquisition time limit (CAPTURE_DIR/ceiling.json or
acquisition_closed.json), nothing more is captured: every article keeps the state it has, an article never run
counts 0, and no further block is named.

Every lock is checked:

- every label file has its locked SHA-256;
- the lock is committed in git;
- the lock directory has no uncommitted change.

While any minimum is unmet, the next block is named, unless the language is at its maximum. No extraction,
prediction or disagreement is read. The decision is printed as JSON.


Copied for the D-035 confirmation (AMENDMENT_2026-11-03_D035_CONFIRMATION.md) from
``../../confirmation-2026-11/scripts/`` with only the changes that amendment lists.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/evaluation/scripts"))
import campaign_capture as cc  # noqa: E402
from reserve_decision import MIN, counts, total  # noqa: E402 - unchanged count rules


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=False)  # noqa: S603,S607


def locked_labels(lock_dirs: list[Path], check_git: bool = True) -> dict[str, Path]:
    labels: dict[str, Path] = {}
    for d in lock_dirs:
        lock = json.loads((d / "ANNOTATION_LOCK.json").read_text(encoding="utf-8"))
        for name, sha in lock.items():
            if hashlib.sha256((d / name).read_bytes()).hexdigest() != sha:
                raise SystemExit(f"{d / name} does not match its locked hash")
            if name in labels:
                raise SystemExit(f"{name} is locked twice")
            labels[name] = d / name
        if check_git:
            rel = d.resolve().relative_to(ROOT)
            if _git("ls-files", "--error-unmatch", str(rel / "ANNOTATION_LOCK.json")).returncode != 0:
                raise SystemExit(f"{rel} lock is not committed")
            if _git("status", "--porcelain", "--", str(rel)).stdout.strip():
                raise SystemExit(f"{rel} has uncommitted changes")
    return labels


def decide(
    selection: dict[str, Any],
    states: dict[str, Any],
    labels: dict[str, Path],
    stopped: str | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    now = time.time() if now is None else now
    out: dict[str, Any] = {}
    for wiki in ("ar", "en"):
        frame = selection["frame"][wiki]
        groups = [("holdout", frame["initial"])] + [
            (f"reserve{n}", block) for n, block in enumerate(frame["reserve_blocks"], start=1)
        ]
        rows: list[dict[str, Any]] = []
        next_block = None
        for split, arts in groups:
            keys = [f"{split}/{wiki}-{a['page_id']}" for a in arts]
            run = [k for k in keys if (states.get(k) or {}).get("runs")]
            if not run:
                next_block = split
                break
            if stopped is None:
                if len(run) < len(keys):
                    raise SystemExit(f"{split} of {wiki} is partly captured")
                unresolved = [k for k in keys if cc.next_step(states[k], now)[0] != "done"]
                if unresolved:
                    raise SystemExit(f"{split} of {wiki}: unresolved articles {unresolved}; finish the capture first")
            for k in keys:
                bundle = ((states.get(k) or {}).get("final") or {}).get("bundle")
                c = None
                if bundle:
                    cap = json.loads((Path(bundle) / "capture.json").read_text(encoding="utf-8"))
                    name = f"{wiki}-{cap['page']['revision_id']}.json"
                    if name not in labels:
                        raise SystemExit(f"{k}: captured but no locked label {name}")
                    c = counts(json.loads(labels[name].read_text(encoding="utf-8")))
                rows.append({"key": k, "bundle": bundle, "counts": c})
        totals = total(rows)
        met = {k: totals[k] >= v for k, v in MIN.items()}
        if stopped is not None:
            next_block = None
        out[wiki] = {
            "included": [r["key"] for r in rows],
            "totals": totals,
            "minimums": MIN,
            "minimums_met": met,
            "next_block": next_block if not all(met.values()) else None,
            "at_maximum": stopped is None and next_block is None and not all(met.values()),
            "stopped": stopped,
            "rows": rows,
        }
    return out


def main() -> int:
    selection = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    capture = Path(sys.argv[2])
    states = json.loads((capture / "capture_states.json").read_text(encoding="utf-8"))["articles"]
    stopped = next((n for n in ("ceiling.json", "acquisition_closed.json") if (capture / n).exists()), None)
    labels = locked_labels([Path(p) for p in sys.argv[3:]])
    sys.stdout.write(json.dumps(decide(selection, states, labels, stopped), indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
