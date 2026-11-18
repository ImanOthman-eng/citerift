"""Stage 04 Step 12, D-062: the equivalent-rebuild proof on the full pinned Stage 02 snapshot (owner Step 12 sec. 5).

The accepted Stage 02 snapshot is built twice, independently, by Stage 02 ``build`` from the pinned Retraction Watch
CSV (receipt ``a987928``; the CSV's SHA-256 is checked against the receipt). For each build this records the file's
SHA-256 and size (expected to be allowed to differ) and its canonical Stage 02 identity, established two ways: by the
Stage 04 D-062 identity-verification profile LOOKUP uses (``adapters.lookup.verify_index_identity``, OD-S12-1) and by
Stage 02's complete ``verify`` (every check, including the JSON-Schema check of every stored event). The identities
must be equal before the builds are called equivalent.

Then fresh Stage 04 investigations of the design-exposed vertical-slice bundles (SPEC S-7.4, D-5; no holdout, no
evaluation frame) run through the production operations against each build, in two memory roots, and the script
requires equality of: the canonical identity, the lookup observations, the lookup-plan digest, the evidence ids,
claim ids, decision ids and question ids, the report digest, the projection-set digest and ``C(J)``. Finally the
investigations of build A are replayed with build B named as the index (``--index`` locator), and with build B's
bytes copied over build A's path: ``reproduced``, never STALE because the bytes differ.

That a genuinely different canonical content is STALE, and the tamper cases, are tested on the attributed fixture
subset in ``tests/stage04/test_step12_d062.py`` (CI); this script is the full-size evidence (about 10 minutes).

Run from the repository root, offline (no network interface):

    unshare -rn uv run python docs/verification/stage-04/freeze-2/d062/two_build_equivalence.py \\
        --csv <retraction_watch.csv of the pinned snapshot> --work <empty scratch directory>

Writes ``two_build_equivalence.json`` beside itself.
"""

# ruff: noqa: PLC0415

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
S03 = "docs/verification/stage-03"
CASES = {
    "VS-1": f"{S03}/demonstrations/bundles/en-1381772671",
    "VS-2": "tests/stage03/fixtures/observed/ar-76190003",
    "VS-3a": "tests/stage03/fixtures/observed/en-1372543632",
    "VS-3b": f"{S03}/demonstrations/bundles/en-1374726997",
    "VS-4": f"{S03}/evaluation/confirmation-2026-11/campaign/capture/bundles/challenge/en-65547507-a1",
    "VS-5": f"{S03}/evaluation/capture/bundles/challenge/ar-4541237-a1",
    "VS-6a": f"{S03}/evaluation/capture/bundles/reserve/ar-9617858-a1",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build_twice(csv_path: Path, work: Path) -> list[Path]:
    from citerift.retraction.source import load_receipt
    from citerift.retraction.store import build

    receipt = load_receipt()
    sha = sha256_file(csv_path)
    if sha != receipt.expected_sha256:
        raise SystemExit(f"{csv_path}: sha256 {sha} is not the pinned receipt's {receipt.expected_sha256}")
    out = []
    for name in ("build-a", "build-b"):
        t0 = time.perf_counter()
        out.append(build(csv_path, receipt, work / name).index_path)
        print(f"{name}: built in {time.perf_counter() - t0:.1f} s", file=sys.stderr)
    return out


def describe(index: Path) -> dict[str, Any]:
    from citerift.investigation.adapters import lookup
    from citerift.retraction import export
    from citerift.retraction.query import Index
    from citerift.retraction.store import manifest_path_for

    t0 = time.perf_counter()
    lookup_identity = lookup.IndexVerifier(enabled=False).identity(index)
    t1 = time.perf_counter()
    with Index(index) as ix:
        full = export.verify(ix.conn, manifest_path=manifest_path_for(index))
    t2 = time.perf_counter()
    return {
        "file": index.name,
        "file_sha256": sha256_file(index),
        "file_bytes": index.stat().st_size,
        "manifest_sha256": sha256_file(manifest_path_for(index)),
        "identity": lookup_identity,
        "identity_scope": "D-062 identity-verification profile (verify_index_identity, OD-S12-1)",
        "identity_s": round(t1 - t0, 1),
        "stage02_verify": {
            "problems": [str(p) for p in full["problems"]][:20],
            "digests": dict(full["digests"]),
            "seconds": round(t2 - t1, 1),
        },
    }


def content(root: Path, key: str) -> dict[str, Any]:
    from citerift.investigation.fold import STEPS
    from citerift.investigation.memory import InvestigationMemory

    with InvestigationMemory.open(root, key, writable=False) as mem:
        f = mem.view
        logical = f.committed_content()
        outputs = {
            r["step"]: r["payload"]["outputs"]
            for r in f.records
            if r["kind"] == "step_succeeded" and r["step"] in STEPS
        }
        evidence: list[str] = []
        for r in logical:
            if r["kind"] == "evidence_batch_recorded":
                evidence += [i["evidence_id"] for i in json.loads(mem.blobs.get(r["payload"]["batch"]))["items"]]
        report = [r["payload"] for r in logical if r["kind"] == "report_recorded"]
        return {
            "lifecycle": f.lifecycle(),
            "index_identity_blobs": sorted(
                r["payload"]["blob"]
                for r in logical
                if r["kind"] == "observation_recorded" and r["payload"]["obs_kind"] == "index_identity"
            ),
            "lookup_observations": sorted(
                r["payload"]["blob"]
                for r in logical
                if r["kind"] == "observation_recorded" and r["payload"]["obs_kind"] == "lookup"
            ),
            "lookup_plan": outputs["LOOKUP"][0] if "LOOKUP" in outputs else None,
            "evidence_ids": sorted(evidence),
            "claim_ids": sorted(r["payload"]["claim_id"] for r in logical if r["kind"] == "claim_recorded"),
            "decision_ids": sorted(r["payload"]["decision_id"] for r in logical if r["kind"] == "decision_recorded"),
            "question_ids": sorted(r["payload"]["question_id"] for r in logical if r["kind"] == "question_opened"),
            "report": report[0]["report"] if report else None,
            "projection_set": report[0]["projection_set"] if report else None,
            "content_digest": f.content_digest(),
        }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    args = ap.parse_args(argv)
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    if any(work.iterdir()):
        raise SystemExit(f"{work} is not empty")
    os.environ.setdefault("CITERIFT_WIKI_NETWORK_LOCK", str(work / "network-gate.lock"))
    from citerift.investigation import operations as ops
    from citerift.investigation.adapters.plan import Integration
    from citerift.retraction.store import manifest_path_for

    t0 = time.perf_counter()
    a, b = build_twice(args.csv.resolve(), work)
    builds = {"A": describe(a), "B": describe(b)}
    same_identity = builds["A"]["identity"] == builds["B"]["identity"]
    full_digests_equal = builds["A"]["stage02_verify"]["digests"] == builds["B"]["stage02_verify"]["digests"]
    clean = not builds["A"]["stage02_verify"]["problems"] and not builds["B"]["stage02_verify"]["problems"]
    cases: dict[str, Any] = {}
    for name, rel in CASES.items():
        bundle = REPO / rel
        got = {}
        for side, index in (("A", a), ("B", b)):
            root = work / "memory" / f"{name}-{side}"
            root.mkdir(parents=True, mode=0o700)
            root.chmod(0o700)
            out, code = ops.run(ops.retained_request(bundle, index, root))
            got[side] = {"exit_code": code, "investigation_key": out["investigation_key"], "root": root}
            got[side]["content"] = content(root, out["investigation_key"])
        key, root_a = got["A"]["investigation_key"], got["A"]["root"]
        replay_b, replay_code = ops.replay(root_a, key, integration=Integration(locators={"index_path": str(b)}))
        verify_b, verify_code = ops.verify(root_a, key, integration=Integration(locators={"index_path": str(b)}))
        differing = sorted(k for k in got["A"]["content"] if got["A"]["content"][k] != got["B"]["content"][k])
        cases[name] = {
            "bundle": rel,
            "exit_codes": [got["A"]["exit_code"], got["B"]["exit_code"]],
            "investigation_keys_equal": key == got["B"]["investigation_key"],
            "investigation_key": key,
            "compared": sorted(got["A"]["content"]),
            "differing": differing,
            "content": got["A"]["content"],
            "replay_A_with_index_B": {"exit_code": replay_code, "result": replay_b["result"]},
            "verify_A_with_index_B": {"exit_code": verify_code, "result": verify_b["result"]},
        }
    # Build B's bytes at build A's path (and its manifest): replay of every A investigation is still reproduced.
    shutil.copyfile(b, a)
    shutil.copyfile(manifest_path_for(b), manifest_path_for(a))
    for name, case in cases.items():
        root_a = work / "memory" / f"{name}-A"
        res, code = ops.replay(root_a, case["investigation_key"])
        case["replay_A_after_B_bytes_at_A_path"] = {"exit_code": code, "result": res["result"]}
    checks = {
        "file SHA-256 of the two builds differ (bytes are allowed to differ)": builds["A"]["file_sha256"]
        != builds["B"]["file_sha256"],
        "Stage 02 complete verify finds no problem in either build": clean,
        "canonical identities equal (D-062 verification)": same_identity,
        "Stage 02 complete verify digests equal": full_digests_equal,
        "identity equals the complete-verify digests": all(
            builds[s]["identity"][k] == (int(v) if k == "export_lines" else v)
            for s in ("A", "B")
            for k, v in builds[s]["stage02_verify"]["digests"].items()
        ),
        **{
            f"{n}: same key and identical scientific content": c["investigation_keys_equal"] and not c["differing"]
            for n, c in cases.items()
        },
        **{
            f"{n}: replay with the other build reproduced, never stale": c["replay_A_with_index_B"]["result"]
            == "reproduced"
            and c["replay_A_after_B_bytes_at_A_path"]["result"] == "reproduced"
            and c["verify_A_with_index_B"]["result"] == "passed"
            for n, c in cases.items()
        },
    }
    result = {
        "label": "Stage 04 Step 12 D-062 equivalent-rebuild proof on design-exposed inputs (D-5); not an evaluation",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "csv_sha256": sha256_file(args.csv.resolve()),
        "builds": builds,
        "cases": cases,
        "checks": checks,
        "failed_checks": [k for k, ok in checks.items() if not ok],
        "seconds": round(time.perf_counter() - t0, 1),
    }
    text = json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False, default=str)
    text = text.replace(str(work), "<work>")
    (HERE / "two_build_equivalence.json").write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"failed_checks": result["failed_checks"], "seconds": result["seconds"]}, indent=1))
    return 0 if not result["failed_checks"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
