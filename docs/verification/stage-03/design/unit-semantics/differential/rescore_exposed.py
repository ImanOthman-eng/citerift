"""Re-score the exposed campaigns with the frozen scorer, swapping only the extraction files for those of a directory.

Usage, from the repository root: ``python rescore_exposed.py <out dir> <extractions dir> <tag>``. The extractions
directory is one written by ``extract_all.py``. Exposed data: regression evidence only, never a scientific pass.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
SCORER = "docs/verification/stage-03/protocol/scripts/evaluate_v2.py"
SPECS = {
    "confirmation-2026-11": "docs/verification/stage-03/evaluation/confirmation-2026-11/campaign/prediction/"
    "score_spec.json",
    "final": "docs/verification/stage-03/evaluation/final/run/score_spec_adjudicated.json",
    "run-1": "docs/verification/stage-03/evaluation/run-1/score_spec_adjudicated.json",
}


def resolve(spec: Path, p: str) -> Path:
    q = Path(p)
    if not q.is_absolute():
        q = (spec.parent / q).resolve()
    if not q.exists():
        q = ROOT / Path(*q.parts[q.parts.index("docs") :])
    return q


def main() -> None:
    out, extractions, tag = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    rows = []
    for name, rel in SPECS.items():
        spec_path = ROOT / rel
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        for split in spec["splits"].values():
            for entry in split:
                for key in ("bundle", "locked", "adjudicated"):
                    if entry.get(key):
                        entry[key] = str(resolve(spec_path, entry[key]))
                flat = Path(entry["bundle"]).relative_to(ROOT).as_posix().replace("/", "__") + ".json"
                if not (extractions / flat).exists():
                    raise SystemExit(f"no extraction for {flat}")
                entry["extraction"] = str(extractions / flat)
        swapped = out / f"spec_{name}_{tag}.json"
        swapped.write_text(json.dumps(spec), encoding="utf-8")
        run = subprocess.run(  # noqa: S603 - fixed interpreter and the frozen scorer, no shell
            [sys.executable, SCORER, "score", str(swapped)], capture_output=True, text=True, check=True
        )
        (out / f"score_{name}_{tag}.json").write_text(run.stdout, encoding="utf-8")
        for split_name, langs in json.loads(run.stdout)["splits"].items():
            for lang, views in langs.items():
                for view, value in views.items():
                    gates = value.get("gates", {})
                    if "G5c unit precision" in gates:
                        rows.append(
                            (
                                name,
                                split_name,
                                lang,
                                view,
                                round(gates["G5c unit precision"]["value"], 4),
                                round(gates["G5d unit recall"]["value"], 4),
                                all(g["passed"] for g in gates.values()),
                            )
                        )
    for row in rows:
        print(*row)


if __name__ == "__main__":
    main()
