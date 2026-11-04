"""Post-exposure regression, not a gate result.

The D-035 campaign's 48 articles extracted again by the corrected engine (isolated workers, default configuration)
and scored by the frozen ``protocol/scripts/evaluate_v2.py`` against the same locked and adjudicated labels. The
D-035 candidate's published predictions and scores are not read for writing and not changed.

Usage: python rescore_d035.py <repository root> <output directory>
"""

import json
import subprocess
import sys
from pathlib import Path

from citerift.wiki.extract import ExtractConfig, extract_bundle, write_canonical

root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
camp = root / "docs/verification/stage-03/evaluation/confirmation-d035/campaign"
scorer = root / "docs/verification/stage-03/protocol/scripts/evaluate_v2.py"
specs = {
    "adjudicated": json.loads((camp / "prediction/score_spec.json").read_text()),
    "locked": json.loads((camp / "scores/score_spec.locked-only.json").read_text()),
}
done: dict[str, str] = {}
for name, spec in specs.items():
    for items in spec["splits"].values():
        for it in items:
            for key in ("bundle", "locked", "adjudicated"):
                if key in it:  # the spec was written with the campaign's absolute paths
                    it[key] = str(root / it[key][it[key].index("docs/verification/") :])
            bundle = it["bundle"]
            if bundle not in done:
                doc = extract_bundle(Path(bundle), ExtractConfig())
                target = out / "extractions" / Path(it["extraction"]).name
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(write_canonical(doc))
                done[bundle] = str(target)
            it["extraction"] = done[bundle]
    (out / f"spec.{name}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1))
    res = subprocess.run(  # noqa: S603 (fixed interpreter and the repository's own scorer)
        [sys.executable, str(scorer), "score", str(out / f"spec.{name}.json")],
        check=False,
        capture_output=True,
        text=True,
    )
    (out / f"scores.{name}.json").write_text(res.stdout)
    print(name, "exit", res.returncode, res.stderr.strip())
