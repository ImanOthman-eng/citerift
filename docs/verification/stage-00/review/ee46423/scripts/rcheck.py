import json, sys
from pathlib import Path
from citerift.governance import evidence
rep, rev = Path(sys.argv[1]), sys.argv[2]
suites = ['unit', 'integration', 'negative', 'regression', 'reproducibility', 'security', 'contracts', 'simulation']
d = json.loads(rep.read_text())
print("collected", d["collected"], "totals", d["totals"], "dirty", d["dirty"], "exit", d["exit_status"])
print("selection", d["selection"])
print("suites", {k: v.get("passed") for k, v in d["suites"].items()})
print("check_test_report problems:", [f"{p.code}: {p.message[:90]}" for p in evidence.check_test_report(rep.parent, rep.name, None, rev, suites)])
