"""Stage 00 handoff simulation: can a later stage start from a clean checkout and use the foundation?

Usage: python docs/verification/stage-00/handoff/handoff_simulation.py REVISION OUTPUT.json

Clones the repository at REVISION into a temporary directory, installs the
locked environment there with uv (offline, from the local cache), and runs
ten checks as a later-stage engineer would, with a minimal environment
(no inherited variables except PATH and the uv cache). Nothing is written to
the source repository; every write happens in the temporary clone and is
removed afterwards. A synthetic Stage 02 consumer is created in the clone
only, never committed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SOURCE = Path(__file__).resolve().parents[4]

CONSUMER_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:citerift:schema:stage02-simulation:retraction-record",
    "x-citerift-version": "0.0.1",
    "type": "object",
    "additionalProperties": False,
    "required": ["paper", "retraction_status", "retrieved_at"],
    "properties": {
        "paper": {"$ref": "urn:citerift:schema:contracts:v1:common#/$defs/paper_identifiers"},
        "retraction_status": {
            "$ref": "urn:citerift:schema:contracts:v1:investigation#/$defs/paper/properties/retraction_status"
        },
        "retrieved_at": {"$ref": "urn:citerift:schema:contracts:v1:common#/$defs/utc_timestamp"},
    },
}

CONSUMER = """
import json, sys
from pathlib import Path
from citerift.contracts import load_contracts
from citerift.contracts.validate import ContractSet

v1 = load_contracts(Path("schemas/contracts"))
own = json.loads(Path("stage02_sim/retraction_record.schema.json").read_text(encoding="utf-8"))
contracts = ContractSet({**v1.schemas, own["$id"]: own})
assert contracts.meta_problems() == [], contracts.meta_problems()
prov = [{"source_id": "synthetic-fixture", "locator": "fixture:x", "retrieved_at": "2026-10-25T12:00:00Z"}]
good = {"paper": {"doi": "10.5555/stage02.sim"}, "retrieved_at": "2026-10-25T12:00:00Z",
        "retraction_status": {"status": "uncertain", "value": "not_found_in_checked_sources", "provenance": prov,
                              "reason": "no record in the checked sources"}}
bad = [
    {**good, "retraction_status": {"status": "verified_fact", "value": "not_retracted", "provenance": prov}},
    {**good, "retraction_status": {"status": "verified_fact", "value": "not_found_in_checked_sources",
                                   "provenance": prov}},
    {**good, "retrieved_at": "2026-02-31T12:00:00Z"},
    {**good, "paper": {"doi": "10.5555/x\\n"}},
]
sid = own["$id"]
result = {"valid_accepted": contracts.validate(good, sid) == [],
          "invalid_rejected": [bool(contracts.validate(b, sid)) for b in bad],
          "diagnostic_example": str(contracts.validate(bad[0], sid)[0])}
print(json.dumps(result))
"""


def run(cmd: list[str], cwd: Path, env: dict[str, str], timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603


def main(revision: str, output: Path) -> int:
    uv = shutil.which("uv")
    git = shutil.which("git")
    if uv is None or git is None:
        raise SystemExit("uv and git are required")
    results: list[dict[str, Any]] = []

    def record(point: str, ok: bool, evidence: str) -> None:
        results.append({"point": point, "pass": ok, "evidence": evidence[:2000]})
        print(f"{'PASS' if ok else 'FAIL'} {point}: {evidence[:200]}", flush=True)

    with tempfile.TemporaryDirectory(prefix="citerift-handoff-") as tmp:
        work = Path(tmp)
        clone = work / "clone"
        home = work / "home"
        home.mkdir()
        env = {
            "PATH": os.environ["PATH"],
            "HOME": str(home),
            "LANG": "C.UTF-8",
            "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", str(Path.home() / ".cache" / "uv")),
            "UV_OFFLINE": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        }
        for key in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "UV_PYTHON_INSTALL_DIR"):
            if key in os.environ:
                env[key] = os.environ[key]

        # 1. Clean checkout of the exact revision.
        c = run([git, "clone", "-q", "--no-local", str(SOURCE), str(clone)], work, env)
        c2 = run([git, "checkout", "-q", "--detach", revision], clone, env)
        head = run([git, "rev-parse", "HEAD"], clone, env).stdout.strip()
        status = run([git, "status", "--porcelain"], clone, env).stdout
        record(
            "1 clean checkout",
            c.returncode == 0 and c2.returncode == 0 and head.startswith(revision) and status == "",
            f"HEAD {head}, porcelain {status!r}",
        )

        # 8 (first, because everything else depends on it). No hidden dependency: the locked environment
        # installs from the lock file alone and the CLIs run with a minimal environment.
        sync = run([uv, "sync", "--locked"], clone, env)
        py = clone / ".venv" / "bin" / "python"
        record("8 no hidden dependency: locked install", sync.returncode == 0 and py.exists(), sync.stderr[-400:])

        def gov(*args: str) -> subprocess.CompletedProcess[str]:
            return run([str(py), "-I", "-m", "citerift.governance.cli", *args], clone, env)

        # 2. Orchestrator usable.
        st = gov("status")
        chk = gov("check")
        record(
            "2 orchestrator usable",
            st.returncode == 0 and chk.returncode == 0 and "0 errors" in chk.stdout,
            (st.stdout.splitlines()[0] if st.stdout else st.stderr) + " | " + chk.stdout.splitlines()[0],
        )

        # 3. Memory usable and 10. recovery read-only.
        before = (clone / "governance/stage_registry.json").read_bytes(), (clone / "PROJECT_STATUS.md").read_bytes()
        rec = gov("--json", "recover")
        data = json.loads(rec.stdout) if rec.returncode == 0 else {}
        after = (clone / "governance/stage_registry.json").read_bytes(), (clone / "PROJECT_STATUS.md").read_bytes()
        record(
            "3 persistent memory usable",
            bool(data) and data["consistency"]["errors"] == [] and len(data["open_risks_and_limitations"]) > 0,
            f"verified awaiting acceptance {data.get('verified_awaiting_owner_acceptance')}, "
            f"{len(data.get('open_risks_and_limitations', []))} open risks, next actions {data.get('next_actions')}",
        )
        porcelain = run([git, "status", "--porcelain"], clone, env).stdout
        record(
            "10 recovery does not change state",
            before == after and ".venv" not in porcelain,
            f"porcelain {porcelain!r}",
        )

        # 4 and 7. Contracts usable by a synthetic downstream consumer outside the Stage 00 owned paths.
        (clone / "stage02_sim").mkdir()
        (clone / "stage02_sim/retraction_record.schema.json").write_text(json.dumps(CONSUMER_SCHEMA), encoding="utf-8")
        cons = run([str(py), "-I", "-c", CONSUMER], clone, env)
        out = json.loads(cons.stdout) if cons.returncode == 0 else {}
        record(
            "4 contracts usable",
            run([str(py), "-I", "-m", "citerift.contracts.validate", "check-schemas"], clone, env).returncode == 0
            and run(
                [
                    str(py),
                    "-I",
                    "-m",
                    "citerift.contracts.validate",
                    "validate",
                    *map(str, sorted((clone / "tests/stage00/fixtures/contracts/v1/valid").glob("*.json"))),
                ],
                clone,
                env,
            ).returncode
            == 0,
            "check-schemas and validate of the three valid fixtures",
        )
        record(
            "7 synthetic downstream consumer",
            out.get("valid_accepted") is True and out.get("invalid_rejected") == [True, True, True, True],
            json.dumps(out) if out else cons.stderr[-600:],
        )
        chk2 = gov("check")
        record(
            "7b consumer files outside owned paths do not disturb Stage 00",
            chk2.returncode == 0 and "UNCOMMITTED_OWNED_CHANGE" not in chk2.stdout,
            chk2.stdout.splitlines()[0],
        )

        # 5. Dependencies enforced; 6. approval gates enforced (dry runs: nothing is written).
        dep = gov(
            "transition",
            "02",
            "AUTHORIZED",
            "--actor",
            "owner",
            "--owner-ref",
            "cmsg_HANDOFFSIMREF01",
            "--reason",
            "simulation",
        )
        record(
            "5 dependencies enforced",
            dep.returncode == 1 and "DEPENDENCY_NOT_ACCEPTED" in dep.stdout,
            dep.stdout.strip()[:400],
        )
        acc = gov("transition", "00", "ACCEPTED_CLOSED", "--actor", "engineering-agent", "--reason", "self acceptance")
        auth = gov("transition", "03", "AUTHORIZED", "--actor", "engineering-agent", "--reason", "self authorization")
        record(
            "6 approval gates enforced",
            acc.returncode == 1 and "OWNER_DECISION_REQUIRED" in acc.stdout and auth.returncode == 1,
            acc.stdout.strip()[:300] + " | " + auth.stdout.strip()[:300],
        )

        # 9. Clear diagnostics: a damaged registry and a forged hand edit get named errors, not tracebacks.
        reg_path = clone / "governance/stage_registry.json"
        good = reg_path.read_text(encoding="utf-8")
        reg_path.write_text(good[: len(good) // 2], encoding="utf-8")
        broken = gov("check")
        reg = json.loads(good)
        reg["history"][-1]["actor"] = "engineering-agent" if reg["history"][-1]["actor"] == "owner" else "owner"
        reg_path.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
        forged = gov("check")
        reg_path.write_text(good, encoding="utf-8")
        record(
            "9 clear diagnostics",
            broken.returncode == 1
            and "REGISTRY_UNREADABLE" in broken.stdout
            and "Traceback" not in broken.stderr + forged.stderr
            and forged.returncode == 1
            and "ERROR" in forged.stdout,
            broken.stdout.strip()[:200] + " | " + forged.stdout.strip()[:300],
        )
        final = gov("check")
        record("10b state intact after the simulation", final.returncode == 0, final.stdout.splitlines()[0])

    summary = {
        "simulation": "citerift-stage00-handoff/1",
        "revision": revision,
        "python": sys.version.split()[0],
        "results": results,
        "passed": sum(r["pass"] for r in results),
        "total": len(results),
    }
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], Path(sys.argv[2])))
