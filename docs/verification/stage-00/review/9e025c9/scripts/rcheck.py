"""Run evidence.check_test_report (the verification-time check) on a report inside ROOT. Usage: rcheck.py ROOT REL"""
import json, sys
from pathlib import Path
from citerift.governance import evidence, gitutil
root = Path(sys.argv[1]); rel = sys.argv[2]
rep = json.loads((root / rel).read_text())
rev = gitutil.head(root)
suites = [s for s in json.loads((root / "governance/stage_registry.json").read_text())["stages"] if s["id"] == "00"][0]["required_test_suites"]
print("collected", rep["collected"], "totals", rep["totals"], "dirty", rep["dirty"], "exit", rep["exit_status"])
sel = dict(rep["selection"]); files = sel.pop("files")
print("selection", sel, "files", len(files))
print("check_test_report problems:", [f"{p.code}: {p.message}" for p in evidence.check_test_report(root, rel, None, rev, suites)])
