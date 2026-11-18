"""Stage 04 Step 13: the one locked prediction run (PREREGISTRATION.md section 9).

Nothing here may run before every annotation round is locked (``LOCK.json``) and the owner-accepted pre-registration
is in force. It runs the frozen engine once per acquired article, through the production command line only:

    citerift-investigate run    --bundle bundles/<name> --index I --memory-root run/memory --format json
    citerift-investigate verify --memory-root run/memory --key K --index I --bundle bundles/<name> --format json
    citerift-investigate export --memory-root run/memory --key K --index I --bundle bundles/<name>
                                --out run/exports/<name> --format json

Checks before the first article (any failure stops the run before any prediction exists):

- the tree of every path in ``PARAMETERS.json`` ``frozen_engine.checked_paths`` at ``HEAD`` equals its tree at the
  frozen content commit, and none of them has an uncommitted change;
- every file listed in ``PREREGISTRATION_MANIFEST.json`` still has its recorded SHA-256, and the manifest digest is
  the ``prereg_digest`` of ``SEED.json``;
- ``LOCK.json`` exists, and every packet it names still has its locked SHA-256.

**One run.** ``run/RUN.json`` is written once, at the end; if it exists, this tool refuses. An interrupted run is
continued by invoking the tool again: ``run/PROGRESS.json`` keeps every finished article, and the engine reopens an
existing investigation of the same request (the same key) instead of creating another. An investigation the engine
leaves CREATED or RUNNING with a step that may start (exit 14), or waiting (exit 8), is continued with ``resume``, at
most three times, never re-created. Nothing is re-run after ``RUN.json`` exists, whatever the scores are.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s13_common import EVALUATION, REPO, digest, file_sha256, git, read_json, write_json

FORMAT = "citerift-stage04-eval-run/1"
RESUME_CODES = (8, 14)
MAX_RESUMES = 3


def frozen_check(params: dict[str, Any]) -> dict[str, Any]:
    frozen = params["frozen_engine"]
    paths = frozen["checked_paths"]
    trees = {p: (git("rev-parse", f"HEAD:{p}"), git("rev-parse", f"{frozen['content_commit']}:{p}")) for p in paths}
    bad = {p: t for p, t in trees.items() if t[0] != t[1]}
    dirty = git("status", "--porcelain", "--", *paths)
    if bad or dirty:
        raise SystemExit(f"the engine is not the frozen one: differing {sorted(bad)}; uncommitted: {dirty[:300]}")
    return {
        "head": git("rev-parse", "HEAD"),
        "content_commit": frozen["content_commit"],
        "trees": {p: t[0] for p, t in trees.items()},
    }


def prereg_check(campaign: Path) -> dict[str, Any]:
    manifest_path = EVALUATION / "PREREGISTRATION_MANIFEST.json"
    manifest = read_json(manifest_path)
    changed = [f["path"] for f in manifest["files"] if file_sha256(REPO / f["path"]) != f["sha256"]]
    if changed:
        raise SystemExit(f"pre-registered files changed: {changed}")
    seed = read_json(campaign / "SEED.json")
    if seed["prereg_digest"] != digest(manifest):
        raise SystemExit("SEED.json names another pre-registration")
    lock = read_json(campaign / "LOCK.json")
    moved = [p for p, sha in lock["packets"].items() if file_sha256(campaign / "packets" / p) != sha]
    if moved:
        raise SystemExit(f"packets changed after the lock: {moved[:3]}")
    return {"prereg_digest": seed["prereg_digest"], "lock_sha256": file_sha256(campaign / "LOCK.json")}


def investigate(*args: str) -> tuple[int, dict[str, Any]]:
    cmd = [sys.executable, "-m", "citerift.investigation.cli", *args, "--format", "json"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603 - fixed argv
    try:
        doc = json.loads(res.stdout)
    except ValueError:
        doc = {"unparsed_stdout": res.stdout[-2000:], "stderr": res.stderr[-2000:]}
    return res.returncode, doc


def run_article(name: str, wiki: str, campaign: Path, index: Path) -> dict[str, Any]:
    bundle = campaign / "bundles" / name
    root = campaign / "run" / "memory"
    t0 = time.perf_counter()
    code, doc = investigate("run", "--bundle", str(bundle), "--index", str(index), "--memory-root", str(root))
    res = doc.get("result") or {}
    key = res.get("investigation_key")
    steps = [{"command": "run", "exit": code}]
    resumes = 0
    while key and code in RESUME_CODES and resumes < MAX_RESUMES:
        resumes += 1
        code, doc = investigate("resume", "--memory-root", str(root), "--key", key)
        res = doc.get("result") or res
        steps.append({"command": "resume", "exit": code})
    rec: dict[str, Any] = {
        "article": name,
        "wiki": wiki,
        "investigation_key": key,
        "lifecycle": res.get("lifecycle"),
        "claims_by_class": res.get("claims_by_class"),
        "memory_root": "run/memory",
        "verify_passed": False,
        "export": None,
        "commands": steps,
    }
    if key is None:
        rec["error"] = doc
        return rec
    vcode, vdoc = investigate(
        "verify", "--memory-root", str(root), "--key", key, "--index", str(index), "--bundle", str(bundle)
    )
    rec["verify"] = {"exit": vcode, "result": (vdoc.get("result") or {}).get("result")}
    rec["verify_passed"] = rec["verify"]["result"] == "passed"
    if rec["verify_passed"]:
        out = campaign / "run" / "exports" / name
        ecode, edoc = investigate(
            "export",
            "--memory-root",
            str(root),
            "--key",
            key,
            "--index",
            str(index),
            "--bundle",
            str(bundle),
            "--out",
            str(out),
        )
        rec["export_exit"] = ecode
        if out.is_dir() and (out / "export.json").exists():
            rec["export"] = f"run/exports/{name}"
            rec["export_manifest_sha256"] = file_sha256(out / "export.json")
        else:
            rec["export_error"] = edoc
    rec["seconds"] = round(time.perf_counter() - t0, 3)
    return rec


def articles_of(campaign: Path) -> list[tuple[str, str]]:
    names = []
    for rdir in sorted((campaign / "rounds").glob("*")):
        if not (rdir / "LOCK.json").exists():
            raise SystemExit(f"round {rdir.name} is not locked")
        names += read_json(rdir / "ARTICLES.json")["articles"]
    return [(n, n.split("-", 1)[0]) for n in sorted(set(names))]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 04 Step 13: the one prediction run")
    ap.add_argument("--campaign", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    a = ap.parse_args(argv)
    campaign = a.campaign.resolve()
    final = campaign / "run" / "RUN.json"
    if final.exists():
        sys.exit("RUN.json exists: the one prediction run is over")
    params = read_json(EVALUATION / "PARAMETERS.json")
    checks = {"frozen": frozen_check(params), "preregistration": prereg_check(campaign)}
    root = campaign / "run" / "memory"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    progress_path = campaign / "run" / "PROGRESS.json"
    progress = read_json(progress_path) if progress_path.exists() else {"articles": {}}
    for name, wiki in articles_of(campaign):
        if name in progress["articles"]:
            continue
        progress["articles"][name] = run_article(name, wiki, campaign, a.index.resolve())
        write_json(progress_path, progress)
        r = progress["articles"][name]
        print(name, r["lifecycle"], r["verify_passed"], r["export"] is not None, flush=True)
    write_json(
        final,
        {
            "format": FORMAT,
            "checks": checks,
            "index_sha256": file_sha256(a.index),
            "articles": [progress["articles"][n] for n in sorted(progress["articles"])],
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
