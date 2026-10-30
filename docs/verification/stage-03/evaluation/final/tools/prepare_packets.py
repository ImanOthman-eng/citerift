"""Make raw-only evaluator packets after committed freeze; no engine predictions."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
capture = Path(sys.argv[2]).resolve()
out = Path(sys.argv[3]).resolve()
out.mkdir(exist_ok=False)
states = json.loads((capture / "capture_states.json").read_text())["articles"]
guide = repo / "docs/verification/stage-03/protocol/ANNOTATION_GUIDE.md"
shutil.copyfile(guide, out / "ANNOTATION_GUIDE.md")
bundles = []
for st in states.values():
    b = st["final"].get("bundle")
    if b:
        cap = json.loads((Path(b) / "capture.json").read_text())
        if (cap.get("source") or {}).get("artifact"):
            bundles.append(b)
subprocess.run(  # noqa: S603 - fixed Python and retained packet tool; no shell
    [
        str(repo / ".venv/bin/python"),
        str(repo / "docs/verification/stage-03/protocol/scripts/evaluate.py"),
        "packets",
        str(out / "all"),
        *bundles,
    ],
    check=True,
)
packet_paths = sorted((out / "all").iterdir())
template = (repo / "docs/verification/stage-03/evaluation/EVALUATOR_BRIEF.md").read_text()
assignments = []
for lang in ["ar", "en"]:
    pp = [p for p in packet_paths if p.name.startswith(lang + "-")]
    # Contiguous fixed chunks; labels and engine outcomes do not decide assignments.
    for i in range(0, len(pp), 5):
        key = f"{lang}-{i // 5 + 1}"
        target = out / key
        target.mkdir()
        for p in pp[i : i + 5]:
            shutil.copytree(p, target / p.name)
        dest = out / ("output-" + key)
        dest.mkdir()
        brief = template.replace("{LANG}", key).replace("{PACKETS}", str(target)).replace("{OUT}", str(dest))
        brief = brief.replace(
            "`docs/verification/stage-03/protocol/ANNOTATION_GUIDE.md` in the repository at\n`/home/user/citerift`",
            f"`{out / 'ANNOTATION_GUIDE.md'}`",
        )
        brief += f"\nPut any helper script only under `{dest}/tools/`; do not create or use any other directory.\n"
        brief += (
            "Record the actual evaluator tool as ChatGPT/Codex in provenance; "
            "do not claim Claude authored these annotations.\n"
        )
        (out / (key + "-BRIEF.md")).write_text(brief)
        assignments.append(
            {
                "id": key,
                "brief": str(out / (key + "-BRIEF.md")),
                "packets": str(target),
                "output": str(dest),
                "articles": [p.name for p in pp[i : i + 5]],
            }
        )
(out / "ASSIGNMENTS.json").write_text(
    json.dumps({"guide_sha256": hashlib.sha256(guide.read_bytes()).hexdigest(), "assignments": assignments}, indent=2)
    + "\n"
)
print(json.dumps({"packets": len(packet_paths), "assignments": assignments}, indent=2))
