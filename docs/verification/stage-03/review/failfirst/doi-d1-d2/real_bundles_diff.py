"""DOI boundary fixes D-1, D-2: real-data impact on EXPOSED retained bundles (a regression check, not
evaluation evidence).

dump:    python real_bundles_diff.py dump <repo> <out_dir>   extract every retained real bundle with the importable
         citerift (run once with the pre-fix source on PYTHONPATH, once with the fixed source)
compare: python real_bundles_diff.py compare <before_dir> <after_dir>   JSON report of every difference
"""

import json
import sys
from pathlib import Path

IGNORE = {"extraction_digest"}


def pairs(repo: Path) -> list[tuple[str, Path]]:
    ev = repo / "docs/verification/stage-03/evaluation"
    out = []
    for runs, bundles in ((ev / "final/run", ev / "final/capture/bundles"), (ev / "run-1", ev / "capture/bundles")):
        for r in json.loads((runs / "runs.json").read_text()):
            b = (r.get("capture") or {}).get("bundle")
            if b and (r.get("extract") or {}).get("argv"):
                rel = b.split("/bundles/", 1)[1]
                out.append((f"{runs.name}__{rel.replace('/', '__')}", bundles / rel))
    return out


if sys.argv[1] == "dump":
    from citerift.wiki.extract import extract_bundle

    dst = Path(sys.argv[3])
    dst.mkdir(parents=True)
    for name, bundle in pairs(Path(sys.argv[2]).resolve()):
        doc = extract_bundle(bundle, None, isolated=False)
        (dst / f"{name}.json").write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True))
else:
    before, after = Path(sys.argv[2]), Path(sys.argv[3])
    rep = {"bundles": 0, "unchanged": 0, "changed": []}
    for p in sorted(before.glob("*.json")):
        old, new = json.loads(p.read_text()), json.loads((after / p.name).read_text())
        rep["bundles"] += 1
        diff = sorted(k for k in set(old) | set(new) if k not in IGNORE and old.get(k) != new.get(k))
        if not diff:
            rep["unchanged"] += 1
            continue
        ids = [
            {
                "id": a["id"],
                "key_before": (a["normalization"] or {}).get("normalized"),
                "key_after": (b["normalization"] or {}).get("normalized"),
                "steps_after": (b["decoding"] or {}).get("structural_steps"),
            }
            for a, b in zip(old["identifiers"], new["identifiers"], strict=True)
            if a != b
        ]
        rep["changed"].append({"bundle": p.stem, "sections": diff, "identifiers": ids})
    print(json.dumps(rep, ensure_ascii=False, indent=1))
