"""Ordered reserve decision from committed, hash-locked annotations only.

This operational wrapper records one step of AMENDMENT_2026-10-29 section 4.
It never imports the engine or reads predictions. It uses the established
reserve_decision.counts and total functions unchanged.
Usage: python reserve_step.py REPO SELECTION CAPTURE_DIR ANNOTATION_DIR OUT_DIR
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

repo, selection, capture, ann, out = map(lambda s: Path(s).resolve(), sys.argv[1:])
sys.path.insert(0, str(repo / "docs/verification/stage-03/evaluation/scripts"))
from reserve_decision import MIN, counts, total  # noqa: E402 - retained operational helper


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise SystemExit(detail)


def git(*args: str) -> str:
    return subprocess.check_output(  # noqa: S603 - fixed git commands, no shell
        ["git", *args],  # noqa: S607 - configured system git
        cwd=repo,
        text=True,
    ).strip()


lock = json.loads((ann / "ANNOTATION_LOCK.json").read_text())
for name, sha in lock.items():
    require(hashlib.sha256((ann / name).read_bytes()).hexdigest() == sha, f"Lock mismatch: {name}")
relative = ann.relative_to(repo)
git("ls-files", "--error-unmatch", str(relative / "ANNOTATION_LOCK.json"))
require(not git("status", "--porcelain", "--", str(relative)), "Annotations must be committed unchanged")
sel = json.loads(selection.read_text())
states = json.loads((capture / "capture_states.json").read_text())["articles"]
decision = {}
view = {"splits": {}, "challenge": {"ar": {"selected": []}, "en": {"selected": []}}}
for wiki in ["ar", "en"]:
    selected = []
    remaining = []
    for split in ["holdout", "reserve"]:
        for a in sel["splits"][wiki][split]:
            key = f"{split}/{wiki}-{a['page_id']}"
            if key not in states:
                require(split == "reserve", f"Holdout not attempted: {key}")
                remaining.append(a)
                continue
            st = states[key]
            b = st["final"].get("bundle")
            c = None
            if b:
                cap = json.loads((Path(b) / "capture.json").read_text())
                name = f"{wiki}-{cap['page']['revision_id']}.json"
                if (cap.get("source") or {}).get("artifact"):
                    require(name in lock, f"Source captured but annotation not locked: {name}")
                    c = counts(json.loads((ann / name).read_text()))
            selected.append({"key": key, "counts": c, "capture_status": st["final"]["status"]})
    t = total(selected)
    met = all(t[k] >= v for k, v in MIN.items())
    need_draw = not met and len(selected) == 14 and len(remaining) == 1 and wiki == "ar"
    # A pair must exist before it is requested. The authorized Arabic 16th draw
    # therefore happens only when the locked 14-article counts require the pair.
    nxt = [] if met or need_draw else remaining[:2]
    require(len(selected) + len(nxt) <= 16, "Per-language article ceiling exceeded")
    decision[wiki] = {
        "included": [x["key"] for x in selected],
        "totals": t,
        "minimums": MIN,
        "minimums_met": {k: t[k] >= v for k, v in MIN.items()},
        "next_pair": nxt,
        "requires_authorized_sixteenth_draw": need_draw,
        "exhausted": not met and not remaining,
        "rows": selected,
    }
    view["splits"][wiki] = {"holdout": [], "reserve": nxt}
out.mkdir(exist_ok=False)
(out / "RESERVE_DECISION.json").write_text(
    json.dumps(
        {
            "annotation_lock_sha256": hashlib.sha256((ann / "ANNOTATION_LOCK.json").read_bytes()).hexdigest(),
            "annotation_commit": git("rev-parse", "HEAD"),
            "languages": decision,
        },
        indent=2,
    )
    + "\n"
)
(out / "capture_selection.json").write_text(json.dumps(view, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(decision, ensure_ascii=False, indent=2))
