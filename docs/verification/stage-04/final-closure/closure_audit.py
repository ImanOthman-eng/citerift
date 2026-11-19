"""Stage 04 non-passing final closure audit (D-079..D-082): evidence checks 1-13 of the owner's instruction.

Read-only over the repository: it recomputes, from the committed and retained inputs, every identity the P2 campaign
records and compares it with the committed artifact. It writes only ``--out`` (and temporary files under ``--work``,
which must lie outside the repository). It never changes a scientific artifact.

Inputs outside the repository (operational): the pinned Stage 02 index, the extracted ``run/run-archive.tar.gz`` and
a ``SCORES.json`` reproduced by ``p2_score.py`` from that extraction (check 1 compares its bytes).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
STAGE = REPO / "docs/verification/stage-04"
P2 = STAGE / "evaluation-p2"
C = STAGE / "evaluation-p2-campaign"
HIST = STAGE / "evaluation-campaign"
sys.path.insert(0, str(P2 / "tools"))

import p2_common as CM  # noqa: E402
import p2_draw as DR  # noqa: E402
import p2_frame as FR  # noqa: E402
import p2_labels as LB  # noqa: E402
import p2_manifest as MF  # noqa: E402
import p2_packets as PK  # noqa: E402

P2_DIGEST = "5d323a67d89a521384772ce7a566520e862715ce9389227f428ff8439f74f75a"
SEED_ROUND = 34096937
ROUNDS = ["primary", "ar-expansion-1", "en-expansion-1", "en-expansion-2", "ar-expansion-2"]
RESULTS: list[dict[str, Any]] = []


def check(n: int, name: str, ok: bool, **detail: Any) -> bool:
    RESULTS.append({"check": n, "name": name, "result": "PASS" if ok else "FAIL", **detail})
    print(f"{n:>2} {'PASS' if ok else 'FAIL'} {name}", flush=True)
    return ok


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603, S607


def c1_scores(reproduced: Path) -> None:
    committed, again = CM.file_sha256(C / "SCORES.json"), CM.file_sha256(reproduced)
    check(1, "SCORES.json reproduced byte for byte", committed == again, committed=committed, reproduced=again)


def c2_p2() -> None:
    recorded = CM.read_json(P2 / "PREREGISTRATION_MANIFEST.json")
    changed = [f["path"] for f in recorded["files"] if CM.file_sha256(REPO / f["path"]) != f["sha256"]]
    rebuilt = MF.build()
    check(
        2,
        "P2 digest and every listed file",
        CM.digest(recorded) == P2_DIGEST and not changed and CM.digest(rebuilt) == P2_DIGEST,
        digest=CM.digest(recorded),
        rebuilt_digest=CM.digest(rebuilt),
        files=len(recorded["files"]),
        changed=changed,
    )


def c3_seed_draw() -> None:
    seed = CM.read_json(C / "SEED.json")
    agreeing, errors = [], []
    for url, m in seed["mirrors"].items():
        if "beacon" in m:
            agreeing.append(DR.check_beacon(m["beacon"], SEED_ROUND) == seed["randomness"])
        else:
            errors.append(url)
    t = datetime.fromisoformat(seed["acceptance_time"]).astimezone(UTC)
    ok_seed = (
        seed["prereg_digest"] == P2_DIGEST
        and seed["round"] == SEED_ROUND == DR.round_for(t)
        and seed["round_time"] == DR.round_time(SEED_ROUND)
        and sum(agreeing) >= 2
        and all(agreeing)
        and DR.seed_of(P2_DIGEST, SEED_ROUND, seed["randomness"]) == seed["seed"]
    )
    draw = CM.read_json(C / "DRAW.json")
    sampling = CM.read_json(P2 / "PARAMETERS.json")["sampling"]
    plan = DR.plan(CM.read_json(P2 / "frame/FRAME.json"), seed["seed"], sampling)
    ok_draw = draw["seed"] == seed["seed"] and CM.digest(plan) == CM.digest(draw["plan"])
    check(
        3,
        "seed and draw identities",
        ok_seed and ok_draw,
        round=seed["round"],
        mirrors_agreeing=sum(agreeing),
        mirrors_failed=errors,
        seed=seed["seed"],
        draw_file_sha256=CM.file_sha256(C / "DRAW.json"),
        draw_plan_digest=CM.digest(draw["plan"]),
        recomputed_plan_digest=CM.digest(plan),
    )


def acquired() -> list[dict[str, Any]]:
    return [a for a in CM.read_json(C / "ACQUISITION.json")["attempts"] if a["status"] == "acquired"]


def c4_acquisition() -> None:
    log = CM.read_json(C / "ACQUISITION.json")["attempts"]
    nums = [a["attempt"] for a in log]
    acq = acquired()
    draw = CM.read_json(C / "DRAW.json")["plan"]
    drawn = {(p["wiki"], p["page_id"]) for w in ("ar", "en") for p in draw[w]["positions"]}
    manifest = CM.read_json(REPO / CM.read_json(P2 / "PARAMETERS.json")["exposure"]["manifest_path"])
    ids, titles = FR.exposure_keys(manifest)
    exposed = [
        a["name"]
        for a in acq
        if (a["wiki"], a["page_id"]) in ids or (a["wiki"], CM.norm_title(a["wiki"], a["title"])) in titles
    ]
    hist = {a["name"] for a in CM.read_json(HIST / "ACQUISITION.json")["attempts"] if a["status"] == "acquired"}
    overlap_hist = sorted({a["name"] for a in acq} & hist)
    strata = Counter((a["wiki"], a["stratum"]) for a in acq)
    bundles = sorted(p.name for p in (C / "bundles").iterdir())
    ok = (
        nums == list(range(1, len(log) + 1))
        and len(log) == len(acq) == 100
        and all((a["wiki"], a["page_id"]) in drawn for a in acq)
        and not exposed
        and not overlap_hist
        and bundles == sorted(a["name"] for a in acq)
        and CM.file_sha256(REPO / manifest_path())
        == CM.read_json(P2 / "PARAMETERS.json")["exposure"]["manifest_sha256"]
    )
    check(
        4,
        "acquisition log and exposure-v2 non-overlap",
        ok,
        attempts=len(log),
        acquired=len(acq),
        by_language_stratum={f"{w} {s}": n for (w, s), n in sorted(strata.items())},
        exposed=exposed,
        historical_campaign_overlap=overlap_hist,
        exposure_manifest_articles=len(manifest["articles"]),
    )


def manifest_path() -> str:
    return str(CM.read_json(P2 / "PARAMETERS.json")["exposure"]["manifest_path"])


def c5_packets(index: Path, work: Path) -> None:
    lock = CM.read_json(C / "LOCK.json")
    moved = [p for p, sha in lock["packets"].items() if CM.file_sha256(C / "packets" / p) != sha]
    rebuilt_differs, extraction_differs = [], []
    for a in acquired():
        packet, extraction = PK.packet(C / "bundles" / a["name"], index)
        CM.write_json(work / "packet.json", packet)
        CM.write_json(work / "extraction.json", extraction)
        if CM.file_sha256(work / "packet.json") != CM.file_sha256(C / "packets" / f"{a['name']}.json"):
            rebuilt_differs.append(a["name"])
        if CM.file_sha256(work / "extraction.json") != CM.file_sha256(C / "extractions" / f"{a['name']}.json"):
            extraction_differs.append(a["name"])
    check(
        5,
        "packet hashes (locked hashes, and packets rebuilt from the committed bundles)",
        not moved and not rebuilt_differs and not extraction_differs and len(lock["packets"]) == 100,
        packets=len(lock["packets"]),
        changed_after_lock=moved,
        rebuilt_differs=rebuilt_differs,
        extraction_differs=extraction_differs,
    )


def c6_labels(work: Path) -> None:
    problems: list[str] = []
    locks = []
    adjudicated = 0
    for r in ROUNDS:
        rd = C / "rounds" / r
        committed = CM.read_json(rd / "LOCK.json")
        for role in ("A", "B", "ADJ"):
            files = sorted((rd / "labels" / role).glob("*.json")) if (rd / "labels" / role).is_dir() else []
            if files:
                LB.combine(role, files, work / f"{role}.json")
                if CM.file_sha256(work / f"{role}.json") != CM.file_sha256(rd / f"{role}.json"):
                    problems.append(f"{r} {role}.json is not the combination of its instance files")
            elif role != "ADJ" or CM.read_json(rd / "ADJ.json")["labels"]:
                problems.append(f"{r} {role} has no instance files")
        packets = [C / "packets" / p for p in committed["packets"]]
        LB.lock(packets, rd / "A.json", rd / "B.json", rd / "ADJ.json", work / r / "LOCK.json")
        if CM.file_sha256(work / r / "LOCK.json") != CM.file_sha256(rd / "LOCK.json"):
            problems.append(f"{r} LOCK.json not reproduced")
        locks.append(work / r / "LOCK.json")
        adjudicated += committed["disagreed"]
    LB.merge(locks, work / "LOCK.json")
    merged_ok = CM.file_sha256(work / "LOCK.json") == CM.file_sha256(C / "LOCK.json")
    check(
        6,
        "A/B/ADJ labels and LOCK.json (round locks and campaign lock reproduced)",
        not problems and merged_ok,
        lock_sha256=CM.file_sha256(C / "LOCK.json"),
        items=CM.read_json(C / "LOCK.json")["items"],
        adjudicated=adjudicated,
        problems=problems,
    )


def first_commit(path: Path) -> str:
    return git("log", "--diff-filter=A", "--format=%H", "--", str(path.relative_to(REPO))).splitlines()[-1]


def c7_lock_before_run() -> None:
    lock_c, run_c = first_commit(C / "LOCK.json"), first_commit(C / "run/RUN.json")
    cmd = ["git", "merge-base", "--is-ancestor", lock_c, run_c]
    ancestor = subprocess.run(cmd, cwd=REPO, check=False).returncode == 0  # noqa: S603
    run = CM.read_json(C / "run/RUN.json")
    started = min(a["started_at"] for a in run["articles"]) if "started_at" in run["articles"][0] else None
    lock_time = git("show", "-s", "--format=%cI", lock_c)
    ok = (
        ancestor
        and lock_c != run_c
        and run["checks"]["preregistration"]["lock_sha256"] == CM.file_sha256(C / "LOCK.json")
        and run["checks"]["frozen"]["head"] == lock_c
        and git("log", "--format=%H", "--", "docs/verification/stage-04/evaluation-p2-campaign/LOCK.json") == lock_c
    )
    check(
        7,
        "labels locked (and committed) before RUN.json",
        ok,
        lock_commit=lock_c,
        lock_commit_time=lock_time,
        run_commit=run_c,
        run_head_recorded=run["checks"]["frozen"]["head"],
        first_article_started=started,
    )


def c8_one_run() -> None:
    run = CM.read_json(C / "run/RUN.json")
    versions = git("log", "--format=%H", "--", "docs/verification/stage-04/evaluation-p2-campaign/run/RUN.json")
    others = [str(p.relative_to(C)) for p in C.rglob("RUN.json") if p != C / "run/RUN.json"]
    names = [a["article"] for a in run["articles"]]
    commands = Counter(c["command"] for a in run["articles"] for c in a["commands"])
    progress = CM.read_json(C / "run/PROGRESS.json")["articles"]
    ok = (
        len(versions.splitlines()) == 1
        and not others
        and sorted(names) == sorted(a["name"] for a in acquired())
        and len(set(names)) == 100
        and commands.get("run") == 100
        and commands.get("resume", 0) == 0
        and sorted(progress) == sorted(names)
        and all(progress[a["article"]] == a for a in run["articles"])
    )
    check(
        8,
        "exactly one prediction-run identity",
        ok,
        run_sha256=CM.file_sha256(C / "run/RUN.json"),
        run_json_commits=versions.splitlines(),
        other_run_files=others,
        commands=dict(commands),
        format=run["format"],
    )


def c9_engine() -> None:
    params = CM.read_json(P2 / "PARAMETERS.json")
    current = CM.engine_check(params)
    run = CM.read_json(C / "run/RUN.json")
    scores = CM.read_json(C / "SCORES.json")
    fe = params["frozen_engine"]
    ok = (
        current["content_commit"] == fe["content_commit"] == run["checks"]["frozen"]["content_commit"]
        and run["checks"]["frozen"]["tree"] == fe["tree"]
        and run["checks"]["frozen"]["freeze_manifest_digest"] == fe["freeze_manifest_digest"]
        and run["checks"]["frozen"]["identity"] == fe["identity"] == current["identity"]
        and run["checks"]["frozen"]["trees"] == current["trees"]
        and scores["engine_identity"]["identity"] == fe["identity"]
        and run["checks"]["engine"]["engine_version"] == "0.3.0"
    )
    check(
        9,
        "frozen engine 28ba646 (run, scores and current checkout)",
        ok,
        content_commit=fe["content_commit"],
        tree=fe["tree"],
        freeze_manifest_digest=fe["freeze_manifest_digest"],
        identity=fe["identity"],
        trees_at_run=run["checks"]["frozen"]["trees"],
        trees_now=current["trees"],
    )


def c10_exports(archive: Path) -> None:
    run = CM.read_json(C / "run/RUN.json")
    root = archive / "run"
    problems = []
    if CM.file_sha256(root / "RUN.json") != CM.file_sha256(C / "run/RUN.json"):
        problems.append("archive RUN.json differs")
    if CM.file_sha256(root / "PROGRESS.json") != CM.file_sha256(C / "run/PROGRESS.json"):
        problems.append("archive PROGRESS.json differs")
    files = 0
    for a in run["articles"]:
        ex = root / "exports" / a["article"]
        if not a["verify_passed"] or a["export"] is None or not (ex / "export.json").is_file():
            problems.append(f"{a['article']}: no verified export")
            continue
        if CM.file_sha256(ex / "export.json") != a["export_manifest_sha256"]:
            problems.append(f"{a['article']}: export manifest hash")
        manifest = CM.read_json(ex / "export.json")
        for f in manifest["files"]:
            p = ex / f["path"]
            files += 1
            if not p.is_file() or p.stat().st_size != f["bytes"] or CM.file_sha256(p) != f["sha256"]:
                problems.append(f"{a['article']}: {f['path']}")
        if not (root / "memory" / a["investigation_key"]).is_dir():
            problems.append(f"{a['article']}: investigation {a['investigation_key'][:12]} not in the memory archive")
    lifecycles = Counter(a["lifecycle"] for a in run["articles"])
    check(
        10,
        "all 100 exports and the Investigation Memory archive",
        not problems and len(run["articles"]) == 100,
        archive_sha256=CM.file_sha256(C / "run/run-archive.tar.gz"),
        exports=len(run["articles"]),
        export_files_checked=files,
        verify_passed=sum(a["verify_passed"] for a in run["articles"]),
        lifecycles=dict(lifecycles),
        memory_investigations=len([p for p in (root / "memory").iterdir() if p.is_dir()]),
        problems=problems[:20],
    )


def c11_gates() -> None:
    params = CM.read_json(P2 / "PARAMETERS.json")["gates"]
    scores = CM.read_json(C / "SCORES.json")
    expected = {
        "ar": {"G1": (42, True), "G2": ((0, 42), True), "G3": (0, True), "G4": (0, True), "G5": (766, True)},
        "en": {"G1": (44, True), "G2": ((1, 44), False), "G3": (0, True), "G4": (0, True), "G5": (1717, True)},
    }
    table, ok = {}, True
    for w, exp in expected.items():
        s = scores["engine"][w]
        ub = CM.cp_upper(s["false_attachments"], s["positive_units"], 0.05)
        got = {
            "G1": (s["positive_units"], s["positive_units"] >= params["min_positive_units"]),
            "G2": (
                (s["false_attachments"], s["positive_units"]),
                ub <= params["max_false_attachment_upper_95"],
            ),
            "G3": (sum(s["hazards"].values()), not s["hazards"]),
            "G4": (sum(s["structural"].values()), not s["structural"]),
            "G5": (s["negative_units"], s["negative_units"] >= params["min_negative_units"]),
        }
        recorded = s["gates"]
        names = {
            "G1": "G1_positive_denominator",
            "G2": "G2_false_attachment_bound",
            "G3": "G3_no_hazard",
            "G4": "G4_no_structural_violation",
            "G5": "G5_negative_denominator",
        }
        for g, (value, passed) in got.items():
            ok = ok and (value, passed) == exp[g] and recorded[names[g]] == passed
        ok = ok and abs(ub - s["false_attachment_rate"]["one_sided_95_upper"]) < 1e-12
        table[w] = {g: {"value": v, "pass": p} for g, (v, p) in got.items()} | {"G2_upper_bound": round(ub, 4)}
    ok = ok and scores["passed"] is False and scores["engine"]["ar"]["passed"] and not scores["engine"]["en"]["passed"]
    check(11, "G1-G5 exactly as reported (recomputed from SCORES.json)", ok, gates=table, gate_04_I="NOT PASSED")


def c12_baseline_sensitivity() -> None:
    s = CM.read_json(C / "SCORES.json")
    expected = {
        "baseline": {"ar": (51, 3), "en": (73, 22)},
        "a": {"ar": (39, 0), "en": (43, 1)},
        "b": {"ar": (42, 0), "en": (44, 1)},
        "c": {"ar": (40, 0), "en": (44, 1)},
    }
    got = {"baseline": {w: s["baseline"][w] for w in ("ar", "en")}} | {
        v: {w: s["sensitivity"][v][w] for w in ("ar", "en")} for v in "abc"
    }
    ok = all(
        (got[k][w]["positive_units"], got[k][w]["false_attachments"]) == expected[k][w]
        for k in expected
        for w in expected[k]
    ) and s["not_computable_units"] == {"a": 0, "b": 0, "c": 87}
    check(
        12,
        "baseline and sensitivity outputs (inside the reproduced SCORES.json)",
        ok,
        positives_and_false_attachments={k: {w: list(expected[k][w]) for w in expected[k]} for k in expected},
        not_computable=s["not_computable_units"],
    )


def c13_deviations(run_log: Path) -> None:
    seed = CM.read_json(C / "SEED.json")
    decisions = (REPO / "DECISIONS.md").read_text(encoding="utf-8")
    log = run_log.read_text(encoding="utf-8").splitlines()
    article_lines = [line for line in log if line.split(" ")[0][:3] in ("ar-", "en-")]
    instances = {}
    for r in ROUNDS:
        instances |= CM.read_json(C / "rounds" / r / "INSTANCES.json")["instances"]
    hist_glue = (HIST / "executor/s14_batches.py").read_text(encoding="utf-8").splitlines()
    glue = (C / "executor/p2c_batches.py").read_text(encoding="utf-8").splitlines()
    run = CM.read_json(C / "run/RUN.json")
    items = {
        "1_seed_boundary": DR.round_for(datetime(2026, 11, 19, 12, 16, 15, tzinfo=UTC)) == SEED_ROUND
        and DR.round_for(datetime(2026, 11, 19, 12, 16, 16, tzinfo=UTC)) == SEED_ROUND + 1
        and "## D-078" in decisions,
        "2_one_mirror_403": list(k for k, v in seed["mirrors"].items() if "error" in v)
        == ["https://drand.cloudflare.com"],
        "3_B-ar-p05_recorded": bool(instances.get("B-ar-p05", {}).get("transcript")),
        "4_status_listings_not_acted_on": "was not acted on" in (C / "PROTOCOL_LOG.md").read_text(encoding="utf-8"),
        "5_wrapper_detachment": "exit 137" in log
        and len(article_lines) == 100
        and all([c["command"] for c in a["commands"]] == ["run"] for a in run["articles"])
        and "## D-082" in decisions,
        "6_archive": (C / "run/run-archive.tar.gz").is_file() and not (C / "run/exports").exists(),
        "7_transcripts": len(instances) == 40
        and all(i.get("transcript_sha256") and i.get("platform_original") for i in instances.values()),
        "8_executor_glue_small_diff": len(glue) == len(hist_glue)
        and sum(1 for x, y in zip(glue, hist_glue, strict=True) if x != y) <= 10,
    }
    check(13, "every protocol deviation matches the retained evidence", all(items.values()), deviations=items)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 04 final closure audit, checks 1-13")
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--archive", type=Path, required=True, help="directory holding the extracted run archive")
    ap.add_argument("--reproduced-scores", type=Path, required=True)
    ap.add_argument("--run-log", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True, help="empty scratch directory outside the repository")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    work = a.work.resolve()
    if work.is_relative_to(REPO):
        raise SystemExit("--work must be outside the repository")
    work.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC).isoformat()
    c1_scores(a.reproduced_scores)
    c2_p2()
    c3_seed_draw()
    c4_acquisition()
    c5_packets(a.index, work)
    c6_labels(work)
    c7_lock_before_run()
    c8_one_run()
    c9_engine()
    c10_exports(a.archive)
    c11_gates()
    c12_baseline_sensitivity()
    c13_deviations(a.run_log)
    doc = {
        "format": "citerift-stage04-final-closure-audit/1",
        "head": git("rev-parse", "HEAD"),
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "index_sha256": CM.file_sha256(a.index),
        "passed": all(r["result"] == "PASS" for r in RESULTS),
        "checks": RESULTS,
    }
    a.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("ALL PASS" if doc["passed"] else "FAILURES PRESENT")
    return 0 if doc["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
