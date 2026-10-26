import json, sys
from pathlib import Path
root = Path(sys.argv[1]); name = sys.argv[2]
p = root / "governance/stage_registry.json"; r = json.loads(p.read_text()); s0 = r["stages"][0]
if name == "gate_dot":
    for g in s0["verification"]["gates"].values(): g["evidence"] = ["."]
elif name == "drop_ci":
    s0["ci_required"] = False; del s0["verification"]["ci"]
elif name == "shrink_gates":
    s0["acceptance_gates"] = s0["acceptance_gates"][:1]
    s0["verification"]["gates"] = {"00-A": s0["verification"]["gates"]["00-A"]}
    s0["required_test_suites"] = ["unit"]
    r["policy"]["handoff_required_sections"] = []
elif name == "drop_owned_paths":
    s0["owned_paths"] = []
p.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
