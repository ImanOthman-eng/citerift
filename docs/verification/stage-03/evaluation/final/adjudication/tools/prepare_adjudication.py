"""Build isolated adjudication inputs for the final campaign (FROZEN_PROTOCOL.md 4.5, AMENDMENT 6).

Reads only the committed disagreement inventory, the committed locked annotations (checked against
ANNOTATION_LOCK.json), the committed raw-only packets and the frozen guide. Copies them into a workspace
outside the repository so that an adjudicator never needs to open the repository. Writes no label.

usage: python3 -I prepare_adjudication.py <repo> <workspace>
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


repo = Path(sys.argv[1]).resolve()
ws = Path(sys.argv[2]).resolve()
ws.mkdir(exist_ok=False)
final = repo / "docs/verification/stage-03/evaluation/final"
guide = repo / "docs/verification/stage-03/protocol/ANNOTATION_GUIDE.md"
lock = json.loads((final / "annotations/ANNOTATION_LOCK.json").read_text())
dis = json.loads((final / "run/disagreements.json").read_text())
packets = {p.name: p for p in (final / "packets").glob("*/*") if p.is_dir()}

items_root = ws / "items"
items_root.mkdir()
shutil.copyfile(guide, ws / "ANNOTATION_GUIDE.md")
manifest = {"guide_sha256": sha(guide), "articles": {}}
for art in dis["holdout"]:
    if not art["items"]:
        continue
    name = art["article"]
    lang = name.split("-")[0]
    locked = final / "annotations" / f"{name}.json"
    if sha(locked) != lock[f"{name}.json"]:
        raise SystemExit(f"lock mismatch: {name}")
    d = items_root / lang / name
    (d / "packet").mkdir(parents=True)
    for f in ("source.wikitext", "render.html", "packet.json"):
        shutil.copyfile(packets[name] / f, d / "packet" / f)
    shutil.copyfile(locked, d / "locked.json")
    disputed = {
        "article": name,
        "window": art["window"],
        "packet_dir": str(d / "packet"),
        "locked_annotation": str(d / "locked.json"),
        "items": [{"item": n, **it} for n, it in enumerate(art["items"], 1)],
    }
    (d / "disputed_items.json").write_text(json.dumps(disputed, ensure_ascii=False, indent=1) + "\n")
    manifest["articles"][name] = {
        "items": len(art["items"]),
        "locked_sha256": sha(locked),
        "source_sha256": sha(d / "packet/source.wikitext"),
        "html_sha256": sha(d / "packet/render.html"),
        "disputed_items_sha256": sha(d / "disputed_items.json"),
    }
(ws / "INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
print(json.dumps({k: v["items"] for k, v in manifest["articles"].items()}))
