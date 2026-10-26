"""Y-11: inputs that still end in a Python traceback instead of a named error (X-05 residual).
Each case runs the CLI the way CI does (python -P -m citerift.governance.cli) in a sandbox."""
import json
import os

from lib import BASE, PY, new_sandbox, run
from citerift.governance.model import Status


def cli(sb, *args):
    out = run([PY, "-P", "-m", "citerift.governance.cli", *args], cwd=sb.root)
    tb = "Traceback" in out.stderr
    last = (out.stderr.strip().splitlines() or [""])[-1] if tb else (out.stdout.strip().splitlines() or [""])[0]
    return out.returncode, tb, last[:160]


def implemented_sandbox(name):
    sb = new_sandbox(name)
    for t in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sb.go("00", t).allowed
    sb.write("impl/00.txt", "x\n")
    rev = sb.commit("impl")
    assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sb.write_evidence("00", rev)
    sb.commit("evidence")
    return sb, rev


def verify_args(sb, rev):
    rec = {"gates": sb.gates("00"), "ci": sb.ci(rev)}
    (sb.root.parent / "rec.json").write_text(json.dumps(rec))
    return ["transition", "00", "VERIFIED_AWAITING_OWNER_ACCEPTANCE", "--actor", "engineering-agent",
            "--reason", "verify", "--record", str(sb.root.parent / "rec.json"), "--at", sb.tick()]


# A: a file in the verification directory whose name is not valid UTF-8.
sb, rev = implemented_sandbox("y05a")
os.close(os.open(os.fsencode(str(sb.root / "docs/verification/stage-00")) + b"/notes-\xff.md", os.O_CREAT | os.O_WRONLY))
print("A non-UTF-8 file name in the evidence directory, transition:", cli(sb, *verify_args(sb, rev)))

# B: a damaged git index (git status and check-ignore fail, rev-parse still works).
sb, rev = implemented_sandbox("y05b")
(sb.root / ".git" / "index").write_bytes(b"DIRC garbage")
print("B damaged index, recover:", cli(sb, "recover"))
print("B damaged index, transition to verified:", cli(sb, *verify_args(sb, rev)))

# C: a stage definition with an absolute verification_dir (schema allows any non-empty string;
# definitions may be edited before verification, GOVERNANCE.md).
sb, rev = implemented_sandbox("y05c")
reg = sb.registry()
outside = sb.root.parent / "elsewhere"
outside.mkdir()
(outside / "f.md").write_text("x" * 400)
reg["stages"][0]["verification_dir"] = str(outside)
sb.save_registry(reg)
sb.orc().write()
print("C absolute verification_dir, transition to verified:", cli(sb, *verify_args(sb, rev)))
print("C absolute verification_dir, readiness:", cli(sb, "readiness", "00"))

# D: deeply nested JSON. json.loads raises RecursionError, which is not a ValueError, so the
# registry reader and the contracts validator end in a traceback.
sb = new_sandbox("y05d")
(sb.root / "governance/stage_registry.json").write_text("[" * 100000 + "]" * 100000)
print("D deeply nested registry, check:", cli(sb, "check"))
(sb.root / "rec.json").write_text("[" * 100000 + "]" * 100000)
out = run([PY, "-P", "-m", "citerift.contracts.validate", "--schemas", str(BASE / "schemas/contracts"),
           "validate", str(sb.root / "rec.json")], cwd=sb.root)
print("D deeply nested record, citerift-contracts validate:", out.returncode, "Traceback" in out.stderr,
      (out.stderr.strip().splitlines() or [""])[-1][:120])
