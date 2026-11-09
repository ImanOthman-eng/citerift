"""[D-035 copy; see the end of this docstring.]
The single prediction run of the confirmation campaign (AMENDMENT_2026-11-02_CONFIRMATION.md section 8), and the
scoring specs built from it.

Usage (from the repository root):
  python run_confirmation.py run SELECTION_JSON CAPTURE_DIR OUT_DIR LOCK_DIR [LOCK_DIR ...]
  python run_confirmation.py spec SELECTION_JSON OUT_DIR ADJUDICATED_DIR LOCK_DIR [LOCK_DIR ...]

``run`` refuses to start unless:

- every lock directory holds ANNOTATION_LOCK.json, every label matches its locked SHA-256, and every lock is
  committed and unchanged (``reserve_step.locked_labels``);
- every captured article has exactly one locked label (review R6, RR-8: an article is never left out silently);
- every article is resolved (no pending deferral or interrupted run), unless the capture stopped at a ceiling or at
  the acquisition time limit.

It then runs, through the installed CLI and for each article with a bundle, ``citerift-wiki extract``,
``verify --extraction`` and ``replay --extraction`` (``run_holdout._run``, unchanged), and writes OUT_DIR/runs.json
and the specs. OUT_DIR must not exist: the run is made once.

``spec`` rebuilds the specs from OUT_DIR/runs.json after adjudication, adding each article's adjudicated label when
ADJUDICATED_DIR holds one. No extraction is repeated.

Specs:

- OUT_DIR/score_spec.json, for ``evaluate_v2.py score``: one split ``gate`` holding the initial holdout and every
  included reserve block (the gates are computed over all of them together), in capture-state order;
- OUT_DIR/challenge_spec.json, for ``warning_challenge.py score``: the challenge articles with their stratum.


Copied for the D-035 confirmation (AMENDMENT_2026-11-03_D035_CONFIRMATION.md) from
``../../confirmation-2026-11/scripts/`` with only the changes that amendment lists.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/evaluation/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import campaign_capture as cc  # noqa: E402
import reserve_step  # noqa: E402
from run_holdout import _run  # noqa: E402 - unchanged CLI runner


def _strata(selection: dict[str, Any]) -> dict[str, str]:
    return {
        f"challenge/{wiki}-{r['page_id']}": stratum
        for wiki, strata in selection["challenge"].items()
        for stratum, s in strata.items()
        for r in s["selected"]
    }


def plan_run(
    selection: dict[str, Any], capture: Path, labels: dict[str, Path], now: float | None = None
) -> list[dict[str, Any]]:
    """The articles to run, each with its bundle and locked label; refuses an incomplete input."""
    now = time.time() if now is None else now
    states = json.loads((capture / "capture_states.json").read_text(encoding="utf-8"))["articles"]
    stopped = any((capture / n).exists() for n in ("ceiling.json", "acquisition_closed.json"))
    strata = _strata(selection)
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    unresolved: list[str] = []
    for key, st in sorted(states.items()):
        if not stopped and cc.next_step(st, now)[0] != "done":
            unresolved.append(key)
        final = st.get("final") or {}
        row: dict[str, Any] = {"article": key, "split": st["split"], "capture": final or None}
        if st["split"] == "challenge":
            if key not in strata:
                raise SystemExit(f"{key} is not a selected challenge article")
            row["stratum"] = strata[key]
        bundle = final.get("bundle")
        if bundle:
            cap = json.loads((Path(bundle) / "capture.json").read_text(encoding="utf-8"))
            name = f"{cap['page']['wiki']}-{cap['page']['revision_id']}.json"
            row["bundle"], row["name"] = str(Path(bundle).resolve()), name
            if name not in labels:
                missing.append(f"{key} ({name})")
            else:
                row["locked"] = str(labels[name].resolve())
        rows.append(row)
    if unresolved:
        raise SystemExit(f"unresolved captures, finish them first: {unresolved}")
    if missing:
        raise SystemExit(f"captured articles without a locked label: {missing}")
    return rows


def specs(runs: list[dict[str, Any]], adjudicated: Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    gate: list[dict[str, Any]] = []
    challenge: list[dict[str, Any]] = []
    for r in runs:
        if "extraction" not in r:
            continue
        entry = {"bundle": r["bundle"], "extraction": r["extraction"], "locked": r["locked"]}
        if adjudicated is not None and (adjudicated / r["name"]).exists():
            entry["adjudicated"] = str((adjudicated / r["name"]).resolve())
        if r["split"] == "challenge":
            challenge.append({**entry, "stratum": r["stratum"]})
        else:
            gate.append(entry)
    return {"splits": {"gate": gate}}, {"articles": challenge}


def _write_specs(out: Path, runs: list[dict[str, Any]], adjudicated: Path | None) -> None:
    score_spec, challenge_spec = specs(runs, adjudicated)
    (out / "score_spec.json").write_text(json.dumps(score_spec, indent=1) + "\n", encoding="utf-8")
    (out / "challenge_spec.json").write_text(json.dumps(challenge_spec, indent=1) + "\n", encoding="utf-8")


def run(selection: dict[str, Any], capture: Path, out: Path, labels: dict[str, Path]) -> list[dict[str, Any]]:
    rows = plan_run(selection, capture, labels)
    out.mkdir(parents=True, exist_ok=False)
    (out / "extractions").mkdir()
    for row in rows:
        if "bundle" not in row:
            continue
        ext = out / "extractions" / row["name"]
        row["extraction"] = str(ext.resolve())
        row["extract"] = _run(["citerift-wiki", "extract", "--bundle", row["bundle"], "--out", str(ext)])
        row["verify"] = _run(["citerift-wiki", "verify", "--bundle", row["bundle"], "--extraction", str(ext)])
        row["replay"] = _run(["citerift-wiki", "replay", "--bundle", row["bundle"], "--extraction", str(ext)])
    (out / "runs.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    _write_specs(out, rows, None)
    return rows


def main() -> int:
    cmd = sys.argv[1]
    selection = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    if cmd == "run":
        labels = reserve_step.locked_labels([Path(p) for p in sys.argv[5:]])
        rows = run(selection, Path(sys.argv[3]), Path(sys.argv[4]), labels)
        bad = [r["article"] for r in rows if "extract" in r and (r["verify"]["exit"] != 0 or r["replay"]["exit"] != 0)]
        summary = {
            "articles": len(rows),
            "extracted": sum("extract" in r for r in rows),
            "without_bundle": sum("bundle" not in r for r in rows),
            "verify_or_replay_failed": bad,
        }
        print(json.dumps(summary))
        return 0
    if cmd == "spec":
        out = Path(sys.argv[3])
        reserve_step.locked_labels([Path(p) for p in sys.argv[5:]])  # the locks are still intact and committed
        rows = json.loads((out / "runs.json").read_text(encoding="utf-8"))
        _write_specs(out, rows, Path(sys.argv[4]))
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
