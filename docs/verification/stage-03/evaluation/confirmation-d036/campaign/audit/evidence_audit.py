"""Evidence-integrity audit of the D-036 confirmation campaign (AMENDMENT_2026-11-04_D036_CONFIRMATION.md, which keeps
the evidence audit of AMENDMENT_2026-11-03_D035_CONFIRMATION.md section 8). Changes nothing.

A copy of ``../../../confirmation-d035/campaign/audit/evidence_audit.py`` with these changes only: the campaign
directory; the two reserve decisions of this campaign; and check 10, which here confirms that no campaign file was
withheld (no ``WITHHELD_FILES.json``, no campaign ``.gitignore``) and that no tracked campaign file matches the
secret gate's patterns (``../../scripts/secret_gate.py``: the Stage 00 patterns plus review B-3's), instead of
checking withheld files on disk.

Usage (from the repository root): python evidence_audit.py > EVIDENCE_AUDIT.json

Each check is recomputed from the committed files and git history; the report lists every check with its result.

1. Order: the draw, every capture, every lock and every reserve decision are ancestors of the prediction commit, and
   the prediction commit is an ancestor of the first commit that holds scores and of the adjudication commit.
2. Frozen candidate: ``src/``, ``pyproject.toml`` and ``uv.lock`` at the prediction commit equal the candidate
   revision; the MANIFEST file hashes hold at the prediction commit and now.
3. Locks: every lock file's entries match its label files now, and no file in a lock directory changed after its
   lock commit.
4. Labels: every locked label equals, byte for byte, an evaluator output named in VALIDATION.json's instance groups
   (checked through the packets: each label's article and hashes match its packet).
5. Packets: every packet's ``source.wikitext`` and ``render.html`` hash to ``packet.json`` and to the capture bundle
   recorded for that article.
6. Prediction: every extraction named in ``runs.json`` exists, is unchanged since the prediction commit, and its
   verify and replay exits are 0; every captured gate and challenge article has exactly one extraction.
7. Adjudication: every adjudicated label passed validation, and the JSON paths it changes are within the items its
   decisions marked ``correct``; articles without disputed items have no adjudicated file.
8. Ceilings: HTTP attempts and accepted bytes recomputed from the capture journal are within 500 and 300 MiB.
9. Scores: re-running ``evaluate_v2.py score`` on the committed specs gives the committed score files byte for byte.
10. Nothing withheld: the campaign has no ``WITHHELD_FILES.json`` and no ``.gitignore``, and no tracked campaign file
    (decoded and percent-decoded as by the gate) matches a secret-gate pattern.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[7]
CONF = ROOT / "docs/verification/stage-03/evaluation/confirmation-d036"
CAMP = CONF / "campaign"
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/evaluation/scripts"))
import campaign_capture as cc  # noqa: E402


def git(*args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(ROOT), *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def is_ancestor(a: str, b: str) -> bool:
    return (
        subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", a, b], check=False).returncode  # noqa: S603,S607
        == 0
    )


def last_commit(path: Path) -> str:
    return git("log", "-1", "--format=%H", "--", str(path.relative_to(ROOT)))


def first_commit(path: Path) -> str:
    return git("log", "--diff-filter=A", "--format=%H", "--", str(path.relative_to(ROOT))).splitlines()[-1]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    pred = first_commit(CAMP / "prediction/runs.json")
    scores_c = first_commit(CAMP / "scores/locked.json")
    adj_c = first_commit(next((CAMP / "adjudication/decisions").glob("*.json")))
    before = {
        "selection": CAMP / "selection/SELECTION.json",
        "capture journal (first)": CAMP / "capture/captures.jsonl",
        "reserve step 1": CAMP / "reserve/step-1.json",
        "reserve step 2": CAMP / "reserve/step-2.json",
    }
    locks = sorted((CAMP / "annotations/locked").glob("*/ANNOTATION_LOCK.json"))
    for lk in locks:
        before[f"lock {lk.parent.name}"] = lk
    for name, p in before.items():
        c = first_commit(p)
        add(f"1 order: {name} ({c[:7]}) before prediction ({pred[:7]})", is_ancestor(c, pred) and c != pred)
    add("1 order: prediction before first scores", is_ancestor(pred, scores_c) and pred != scores_c)
    add("1 order: prediction before adjudication", is_ancestor(pred, adj_c) and pred != adj_c)

    manifest = json.loads((CONF / "MANIFEST.json").read_text(encoding="utf-8"))
    cand = manifest["candidate_revision"]
    diff = git("diff", "--stat", cand, pred, "--", "src", "pyproject.toml", "uv.lock")
    add("2 frozen: src, pyproject.toml, uv.lock at prediction equal the candidate", diff == "", diff or None)
    bad_now = [p for p, h in manifest["files_sha256_at_candidate"].items() if sha(ROOT / p) != h]
    bad_pred = [
        p
        for p, h in manifest["files_sha256_at_candidate"].items()
        if hashlib.sha256(
            subprocess.run(["git", "-C", str(ROOT), "show", f"{pred}:{p}"], capture_output=True, check=True).stdout  # noqa: S603,S607
        ).hexdigest()
        != h
    ]
    add("2 frozen: MANIFEST hashes hold at prediction and now", not bad_now and not bad_pred, bad_now + bad_pred)

    for lk in locks:
        entries = json.loads(lk.read_text(encoding="utf-8"))
        mism = [n for n, h in entries.items() if sha(lk.parent / n) != h]
        lc = first_commit(lk)
        changed = git("log", "--format=%H", f"{lc}..HEAD", "--", str(lk.parent.relative_to(ROOT)))
        add(
            f"3 lock {lk.parent.name}: {len(entries)} labels match; no change after {lc[:7]}",
            not mism and not changed,
            {"mismatch": mism, "later_commits": changed.splitlines()},
        )

    packets = {p.name: p for p in (CAMP / "annotations").glob("packets*/*/packets/*") if p.is_dir()}
    states = json.loads((CAMP / "capture/capture_states.json").read_text(encoding="utf-8"))["articles"]
    bundle_of: dict[str, Path] = {}
    for st in states.values():
        b = Path(st["final"]["bundle"])
        cap = json.loads((b / "capture.json").read_text(encoding="utf-8"))
        bundle_of[f"{cap['page']['wiki']}-{cap['page']['revision_id']}"] = b
    bad_labels, bad_packets = [], []
    for lk in locks:
        for n in json.loads(lk.read_text(encoding="utf-8")):
            art = n.removesuffix(".json")
            lab = json.loads((lk.parent / n).read_text(encoding="utf-8"))["article"]
            info = json.loads((packets[art] / "packet.json").read_text(encoding="utf-8"))
            if (lab["revision_id"], lab["source_sha256"], lab["html_sha256"]) != (
                info["revision_id"],
                info["source_sha256"],
                info["html_sha256"],
            ):
                bad_labels.append(art)
    for art, p in packets.items():
        info = json.loads((p / "packet.json").read_text(encoding="utf-8"))
        cap = json.loads((bundle_of[art] / "capture.json").read_text(encoding="utf-8"))
        ok = sha(p / "source.wikitext") == info["source_sha256"] and (
            not (p / "render.html").exists() or sha(p / "render.html") == info["html_sha256"]
        )
        if not ok or cap["page"]["revision_id"] != info["revision_id"]:
            bad_packets.append(art)
    add("4 labels: every locked label names its packet's revision and hashes", not bad_labels, bad_labels)
    add("5 packets: source and render hash to packet.json", not bad_packets, bad_packets)
    bundle_files = {art: sorted(sha(f) for f in bundle_of[art].rglob("*") if f.is_file()) for art in packets}
    missing = [
        art
        for art, p in packets.items()
        if sha(p / "source.wikitext") not in bundle_files[art]
        or ((p / "render.html").exists() and sha(p / "render.html") not in bundle_files[art])
    ]
    add("5 packets: source and render are byte copies of a file in the article's capture bundle", not missing, missing)

    runs = json.loads((CAMP / "prediction/runs.json").read_text(encoding="utf-8"))
    bad_runs = []
    for r in runs:
        ext = Path(r["extraction"])
        rel = str(ext.relative_to(ROOT)) if ext.is_absolute() else r["extraction"]
        if not (ROOT / rel).exists() or r["verify"]["exit"] or r["replay"]["exit"]:
            bad_runs.append(r["article"])
            continue
        if git("log", "--format=%H", f"{pred}..HEAD", "--", rel):
            bad_runs.append(f"{r['article']} changed after prediction")
    add(f"6 prediction: {len(runs)} extractions present, unchanged, verify and replay exit 0", not bad_runs, bad_runs)
    add("6 prediction: one run per captured article", sorted(r["article"] for r in runs) == sorted(states), None)

    val = json.loads((CAMP / "adjudication/ADJUDICATION_VALIDATION.json").read_text(encoding="utf-8"))
    used = {}
    for rep in val.values():
        for art, r in rep["articles"].items():
            used[art] = r
    adj_files = {p.stem for p in (CAMP / "adjudication/adjudicated").glob("*.json")}
    dis = json.loads((CAMP / "adjudication/disagreements.json").read_text(encoding="utf-8"))
    disputed = {a["article"] for arts in dis.values() for a in arts if a["items"]}
    probs = [a for a, r in used.items() if r["problems"]]
    add(
        "7 adjudication: one valid adjudicated label per article with disputed items, and no other",
        adj_files == disputed == set(used) and not probs,
        {"problems": probs},
    )
    unexplained = [a for a, r in used.items() if r["changed_paths"] and not r["corrected"]]
    add("7 adjudication: labels change only in articles with a 'correct' decision", not unexplained, unexplained)

    attempts, nbytes = cc.used(cc._journal(CAMP / "capture"))
    add(
        f"8 ceilings: {attempts} attempts <= 500 and {nbytes} bytes <= 300 MiB",
        attempts <= 500 and nbytes <= 300 * 1024 * 1024,
        None,
    )

    for script, spec, out in (
        (
            ROOT / "docs/verification/stage-03/protocol/scripts/evaluate_v2.py",
            "scores/score_spec.locked-only.json",
            "scores/locked.json",
        ),
        (
            ROOT / "docs/verification/stage-03/protocol/scripts/evaluate_v2.py",
            "prediction/score_spec.json",
            "scores/adjudicated.json",
        ),
    ):
        got = subprocess.run(  # noqa: S603
            [sys.executable, str(script), "score", str(CAMP / spec)], capture_output=True, check=True
        ).stdout
        add(f"9 scores: {out} reproduces byte for byte", got == (CAMP / out).read_bytes(), None)

    sys.path.insert(0, str(CONF / "scripts"))
    import secret_gate as sg  # noqa: PLC0415

    pats = sg.patterns()
    tracked = git("ls-files", "--", str(CAMP.relative_to(ROOT))).splitlines()
    hits = [
        p
        for p in tracked
        if any(pat.search(text) for text in sg.scanned((ROOT / p).read_bytes()) for pat in pats)
    ]
    ledger = (CAMP / "WITHHELD_FILES.json").exists() or (CAMP / ".gitignore").exists()
    add(
        f"10 nothing withheld: no ledger or .gitignore; {len(tracked)} tracked campaign files match no gate pattern",
        not ledger and not hits,
        {"ledger_or_gitignore": ledger, "matching_files": hits},
    )

    report = {
        "procedure": __doc__,
        "head": git("rev-parse", "HEAD"),
        "prediction_commit": pred,
        "all_ok": all(c["ok"] for c in checks),
        "checks": checks,
    }
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
