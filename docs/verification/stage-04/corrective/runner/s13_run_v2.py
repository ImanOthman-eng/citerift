"""Corrected prediction-run tool (corrective cycle, owner decision D-071 section 9). A runner correction, not an engine
correction; the historical tool ``evaluation/tools/s13_run.py`` and its campaign are unchanged.

The two defects of the historical tool, both seen in the failed campaign (REPORT section 6, deviations 1 and 2):

1. it placed the Investigation Memory under the campaign (``<campaign>/run/memory``), inside the repository, which
   the engine refuses (``MEMORY_ROOT_UNSAFE``, S-15.3);
2. it did not create the export parent ``<campaign>/run/exports``, which the engine requires (``OUTPUT_PATH_UNSAFE``),
   so the first article kept no export.

This version:

- takes the Investigation Memory root as configuration (``--memory-root``): an absolute path that must lie outside the
  repository and outside any repository working tree, checked **before the first article** with the engine's own
  rule (``fsutil.check_memory_root``), created ``0700`` when absent. The path is recorded once, under ``operational``
  in ``RUN.json``, as a locator only: it is in no article record, no score and no digest, and a run with another
  memory root gives the same scientific record;
- creates ``<campaign>/run/exports`` before the first article and refuses to start when it cannot;
- otherwise runs exactly as the historical tool (the production command line only: ``run``, ``resume`` at most three
  times, ``verify``, ``export``; one ``RUN.json``, written once, at the end).

The engine identity, pre-registration and lock checks name a future pre-registration's files (``--parameters``,
``--prereg-manifest``); they are run by ``main`` and are not part of this correction.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "docs/verification/stage-04/evaluation/tools"))

from s13_common import digest, file_sha256, git, read_json, write_json  # noqa: E402

from citerift.investigation.errors import PathUnsafe  # noqa: E402
from citerift.investigation.fsutil import check_memory_root  # noqa: E402

FORMAT = "citerift-stage04-eval-run/2"
RESUME_CODES = (8, 14)
MAX_RESUMES = 3


class RunnerRefused(SystemExit):
    """The runner refuses before the first article: nothing was run."""


def prepare(campaign: Path, memory_root: Path) -> dict[str, Any]:
    """Operational preparation before the first article: the memory root outside the repository (created 0700), the
    export parent inside the campaign. Raises ``RunnerRefused`` and runs nothing when either cannot be prepared."""
    root = Path(memory_root)
    if not root.is_absolute():
        raise RunnerRefused(f"the memory root {root} is not absolute")
    repo = REPO.resolve()
    probe = root.resolve(strict=False)
    if probe == repo or repo in probe.parents:
        raise RunnerRefused(f"the memory root {root} is inside the repository {repo}")
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root.chmod(0o700)
        resolved = check_memory_root(root, repository=repo)
    except PathUnsafe as exc:
        raise RunnerRefused(f"the memory root is refused by the engine rule: {exc}") from exc
    except OSError as exc:
        raise RunnerRefused(f"the memory root {root} cannot be prepared: {exc}") from exc
    exports = campaign / "run" / "exports"
    try:
        exports.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RunnerRefused(f"the export parent {exports} cannot be created: {exc}") from exc
    if not exports.is_dir():
        raise RunnerRefused(f"the export parent {exports} is not a directory")
    return {"memory_root": str(resolved), "exports": "run/exports"}


def investigate(*args: str) -> tuple[int, dict[str, Any]]:
    cmd = [sys.executable, "-m", "citerift.investigation.cli", *args, "--format", "json"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603 - fixed argv
    try:
        doc = json.loads(res.stdout)
    except ValueError:
        doc = {"unparsed_stdout": res.stdout[-2000:], "stderr": res.stderr[-2000:]}
    return res.returncode, doc


def run_article(name: str, wiki: str, campaign: Path, index: Path, memory_root: Path) -> dict[str, Any]:
    """One article, as the historical tool, with the configured memory root and the prepared export parent. The
    record holds no memory path (operational locator only)."""
    bundle = campaign / "bundles" / name
    root = str(memory_root)
    t0 = time.perf_counter()
    code, doc = investigate("run", "--bundle", str(bundle), "--index", str(index), "--memory-root", root)
    res = doc.get("result") or {}
    key = res.get("investigation_key")
    steps = [{"command": "run", "exit": code}]
    resumes = 0
    while key and code in RESUME_CODES and resumes < MAX_RESUMES:
        resumes += 1
        code, doc = investigate("resume", "--memory-root", root, "--key", key)
        res = doc.get("result") or res
        steps.append({"command": "resume", "exit": code})
    rec: dict[str, Any] = {
        "article": name,
        "wiki": wiki,
        "investigation_key": key,
        "lifecycle": res.get("lifecycle"),
        "claims_by_class": res.get("claims_by_class"),
        "verify_passed": False,
        "export": None,
        "commands": steps,
    }
    if key is None:
        rec["error"] = doc
        return rec
    vcode, vdoc = investigate(
        "verify", "--memory-root", root, "--key", key, "--index", str(index), "--bundle", str(bundle)
    )
    rec["verify"] = {"exit": vcode, "result": (vdoc.get("result") or {}).get("result")}
    rec["verify_passed"] = rec["verify"]["result"] == "passed"
    if rec["verify_passed"]:
        out = campaign / "run" / "exports" / name
        ecode, edoc = investigate(
            "export",
            "--memory-root",
            root,
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
            raise RunnerRefused(f"round {rdir.name} is not locked")
        names += read_json(rdir / "ARTICLES.json")["articles"]
    return [(n, n.split("-", 1)[0]) for n in sorted(set(names))]


def frozen_check(params: dict[str, Any]) -> dict[str, Any]:
    frozen = params["frozen_engine"]
    paths = frozen["checked_paths"]
    trees = {p: (git("rev-parse", f"HEAD:{p}"), git("rev-parse", f"{frozen['content_commit']}:{p}")) for p in paths}
    bad = {p: t for p, t in trees.items() if t[0] != t[1]}
    dirty = git("status", "--porcelain", "--", *paths)
    if bad or dirty:
        raise RunnerRefused(f"the engine is not the frozen one: differing {sorted(bad)}; uncommitted: {dirty[:300]}")
    return {
        "head": git("rev-parse", "HEAD"),
        "content_commit": frozen["content_commit"],
        "trees": {p: t[0] for p, t in trees.items()},
    }


def prereg_check(campaign: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    changed = [f["path"] for f in manifest["files"] if file_sha256(REPO / f["path"]) != f["sha256"]]
    if changed:
        raise RunnerRefused(f"pre-registered files changed: {changed}")
    seed = read_json(campaign / "SEED.json")
    if seed["prereg_digest"] != digest(manifest):
        raise RunnerRefused("SEED.json names another pre-registration")
    lock = read_json(campaign / "LOCK.json")
    moved = [p for p, sha in lock["packets"].items() if file_sha256(campaign / "packets" / p) != sha]
    if moved:
        raise RunnerRefused(f"packets changed after the lock: {moved[:3]}")
    return {"prereg_digest": seed["prereg_digest"], "lock_sha256": file_sha256(campaign / "LOCK.json")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 04: the one prediction run (corrected runner)")
    ap.add_argument("--campaign", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--memory-root", type=Path, required=True, help="absolute, outside the repository")
    ap.add_argument("--parameters", type=Path, required=True, help="the pre-registration's PARAMETERS.json")
    ap.add_argument("--prereg-manifest", type=Path, required=True, help="the pre-registration's manifest")
    a = ap.parse_args(argv)
    campaign = a.campaign.resolve()
    final = campaign / "run" / "RUN.json"
    if final.exists():
        raise RunnerRefused("RUN.json exists: the one prediction run is over")
    checks = {
        "frozen": frozen_check(read_json(a.parameters)),
        "preregistration": prereg_check(campaign, a.prereg_manifest),
    }
    operational = prepare(campaign, a.memory_root)
    root = Path(operational["memory_root"])
    progress_path = campaign / "run" / "PROGRESS.json"
    progress = read_json(progress_path) if progress_path.exists() else {"articles": {}}
    for name, wiki in articles_of(campaign):
        if name in progress["articles"]:
            continue
        progress["articles"][name] = run_article(name, wiki, campaign, a.index.resolve(), root)
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
            "operational": {**operational, "note": "locators only; not evidence, not scored, not in any digest"},
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
