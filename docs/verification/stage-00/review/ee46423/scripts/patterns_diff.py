import json, re, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1])
files = [root / "schemas/contracts/v1/common.schema.json", root / "schemas/contracts/v1/investigation.schema.json", root / "schemas/governance/stage_registry.schema.json"]
pats = set()
def walk(n):
    if isinstance(n, dict):
        for k, v in n.items():
            if k == "pattern" and isinstance(v, str): pats.add(v)
            else: walk(v)
    elif isinstance(n, list):
        for x in n: walk(x)
for f in files: walk(json.loads(f.read_text()))
strings = []
for f in [*files, *(root / "tests/stage00/fixtures/contracts/v1/valid").glob("*.json"), root / "governance/stage_registry.json"]:
    def coll(n):
        if isinstance(n, dict):
            for k, v in n.items(): coll(k); coll(v)
        elif isinstance(n, list):
            for x in n: coll(x)
        elif isinstance(n, str): strings.append(n)
    coll(json.loads(f.read_text()))
extra = ["2026-10-25T10:00:00Z", "2026-10-25T10:00:00.5Z", "1.0.0", "cmsg_ABCDEFGHIJ", "https://a.example/x", "00", "00-A", "A-00-001", "B-00-001",
         "a" * 40, "0" * 64, "10.5555/x", "12345", "en", "zh-yue", "abc_def", "x", "https://github.com/o/r/actions/runs/1", "docs/x.md"]
cps = list(range(0, 0x3100)) + [0x180E, 0x1680, 0x2000, 0x200A, 0x200B, 0x2028, 0x2029, 0x202F, 0x205F, 0x3000, 0xFEFF, 0xFFFE, 0xFFFF, 0x10000, 0x1F600]
cases = []
for p in sorted(pats):
    rx = re.compile(p)
    seeds = [s for s in set(strings + extra) if rx.search(s)][:2] or ["x"]
    for s in seeds:
        for c in cps:
            ch = chr(c)
            if 0xD800 <= c <= 0xDFFF: continue
            for t in (s + ch, s[: len(s) // 2] + ch + s[len(s) // 2:], ch + s):
                cases.append((p, t))
print("patterns", len(pats), "cases", len(cases), file=sys.stderr)
py = [bool(re.search(p, t)) for p, t in cases]
js_src = "const fs=require('fs');const c=JSON.parse(fs.readFileSync(0,'utf8'));const cache={};process.stdout.write(JSON.stringify(c.map(([p,t])=>{if(!(p in cache))cache[p]=new RegExp(p,'u');return cache[p].test(t);})));"
r = subprocess.run(["/opt/node22/bin/node", "-e", js_src], input=json.dumps(cases), capture_output=True, text=True, check=True)
js = json.loads(r.stdout)
diff = [(p, t) for (p, t), a, b in zip(cases, py, js) if a != b]
print("disagreements:", len(diff))
seen = set()
for p, t in diff:
    if p in seen: continue
    seen.add(p); print("  pattern", repr(p), "string", repr(t), "python", bool(re.search(p, t)))
