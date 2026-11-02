"""Positive retraction-warning challenge (AMENDMENT_2026-11-02_CONFIRMATION.md section 9): window, packets, score.

Usage:
  python warning_challenge.py packets OUT_DIR BUNDLE [BUNDLE ...]
  python warning_challenge.py score SPEC_JSON          # {"articles": [{"bundle", "extraction", "locked",
                                                       #   "adjudicated"?, "stratum"}]}

The challenge reuses the frozen scorer's functions (``evaluate.py``: bundle loading, matching, the marker
confusion and fabricated negatives) and scorer v2's definition rule. Only the window differs: 8000 code points
starting at the line that holds a seeded-random call of one of the wiki's marker templates (outside comments and
``<nowiki>``), so that the window contains a warning when the source has one. An article whose source holds no
marker call (the warning comes from another template) gets the frozen window.

Reported, per wiki and per stratum, for locked and adjudicated labels:

- the marker confusion (label x engine state);
- fabricated negatives (label ``warning``, engine ``none``), to which G7 applies;
- sensitivity (engine ``warning`` / label ``warning``);
- engine ``warning`` on label ``none`` (false warnings);
- ``not_inspected`` counts;
- the number of labelled warnings (the denominator).

Nothing here is a holdout gate except G7.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/protocol/scripts"))
import evaluate as v1  # noqa: E402 - the frozen scorer, unchanged
import evaluate_v2 as v2  # noqa: E402

SALT = "citerift-stage03-warning-window-v1"
MARKERS = {
    "ar": ["مصدر مسحوب", "Retracted", "Expression of concern", "Erratum"],
    "en": [
        "Retracted",
        "Retracted paper",
        "Retraction",
        "Expression of concern",
        "Expression of Concern",
        "Erratum",
        "Errata",
    ],
}
_HIDDEN = re.compile(r"<!--.*?-->|<nowiki\b[^>]*>.*?</nowiki\s*>", re.DOTALL | re.IGNORECASE)


def marker_calls(text: str, wiki: str) -> list[int]:
    hidden = [(m.start(), m.end()) for m in _HIDDEN.finditer(text)]
    names = "|".join(re.escape(n[0].upper() + n[1:]) + "|" + re.escape(n[0].lower() + n[1:]) for n in MARKERS[wiki])
    # The namespace prefix is read case-insensitively, as MediaWiki does; arwiki accepts the canonical ``Template:``
    # as well as ``قالب:`` (profile namespace_prefixes). Review R6, RR-9.
    pat = re.compile(r"\{\{\s*(?:(?i:template|قالب)\s*:\s*)?(?:" + names.replace(r"\ ", r"[ _]+") + r")\s*[|}]")
    return [m.start() for m in pat.finditer(text) if not any(s <= m.start() < e for s, e in hidden)]


def challenge_window(text: str, wiki: str, revision_id: int) -> tuple[int, int]:
    if len(text) <= v1.WINDOW_CP:
        return 0, len(text)
    calls = marker_calls(text, wiki)
    if not calls:
        return v1.window(text, wiki, revision_id)
    pick = int(hashlib.sha256(f"{SALT}|{wiki}|{revision_id}".encode()).hexdigest(), 16) % len(calls)
    start = text.rfind("\n", 0, calls[pick]) + 1
    start = min(start, len(text) - v1.WINDOW_CP)
    return start, start + v1.WINDOW_CP


def load(path: Path) -> v1.Article:
    art = v1.load_bundle(path)
    return dataclasses.replace(art, window=challenge_window(art.text, art.wiki, art.revision_id))


def packets(out: Path, bundles: list[Path]) -> None:
    out.mkdir(parents=True, exist_ok=False)
    for b in bundles:
        art = load(b)
        d = out / art.key
        d.mkdir()
        (d / "source.wikitext").write_text(art.text, encoding="utf-8", newline="")
        if art.html_bytes is not None:
            (d / "render.html").write_bytes(art.html_bytes)
        ws, we = art.window
        info = {
            "wiki": art.wiki,
            "revision_id": art.revision_id,
            "source_sha256": art.source_sha256,
            "source_code_points": len(art.text),
            "html_sha256": art.html_sha256,
            "window": {"cp_start": ws, "cp_end": we},
            "window_first_line": art.text[ws : ws + 120],
        }
        (d / "packet.json").write_text(json.dumps(info, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def summarize(confusion: Counter[str]) -> dict[str, Any]:
    labelled = sum(n for k, n in confusion.items() if k.startswith("warning->"))
    detected = confusion.get("warning->warning", 0)
    return {
        "confusion": dict(sorted(confusion.items())),
        "labelled_warnings": labelled,
        "detected_warnings": detected,
        "sensitivity": detected / labelled if labelled else None,
        "fabricated_negatives": confusion.get("warning->none", 0),
        "false_warnings": confusion.get("none->warning", 0),
        "not_inspected": sum(n for k, n in confusion.items() if k.endswith("->not_inspected")),
    }


def score(spec_path: Path) -> dict[str, Any]:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    base = spec_path.parent
    out: dict[str, Any] = {"protocol": "AMENDMENT_2026-11-02_CONFIRMATION.md section 9", "labels": {}}
    for label in ("locked", "adjudicated"):
        per: dict[str, Counter[str]] = {}
        rows = []
        for e in spec["articles"]:
            art = load(base / e["bundle"])
            doc = json.loads((base / e["extraction"]).read_text(encoding="utf-8"))
            if doc["capture"]["revision_id"] != art.revision_id:
                raise SystemExit(f"{e['extraction']}: extraction is for another revision")
            path = e.get(label) or e["locked"]
            ann, problems = v1.load_annotation(base / path, art)
            if problems:
                raise SystemExit(f"{path}: {problems}")
            res = v1.score_article(art, ann, v2.engine_predictions_v2(doc, art.text))
            conf = Counter(res["markers"]["confusion"])
            for key in (art.wiki, f"{art.wiki}/{e['stratum']}"):
                per.setdefault(key, Counter()).update(conf)
            rows.append({"article": art.key, "stratum": e["stratum"], "markers": res["markers"]})
        out["labels"][label] = {k: summarize(c) for k, c in sorted(per.items())} | {"per_article": rows}
    return out


def main() -> int:
    if sys.argv[1] == "packets":
        packets(Path(sys.argv[2]), [Path(p) for p in sys.argv[3:]])
    elif sys.argv[1] == "score":
        sys.stdout.write(json.dumps(score(Path(sys.argv[2])), ensure_ascii=False, indent=1) + "\n")
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
