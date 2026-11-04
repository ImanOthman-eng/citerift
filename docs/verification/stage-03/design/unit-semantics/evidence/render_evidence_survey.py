"""Survey: per template name, does its render output contain CS1/CS2 cite markup or CITEREF links (exposed data).

Run with the repository root as working directory; output: render_evidence_survey.txt, lines
``(wiki, template) {(cite markup, CITEREF link, parts in the transclusion): count}`` for transclusions in notes.
Run 2026-11-03 at 26398f5 (before the D-035 fix; the survey does not use the engine's unit code).
"""

import collections
import sys
from pathlib import Path

from citerift.wiki.bundle import open_bundle
from citerift.wiki.profile import load_profile
from citerift.wiki.render import read_render

prof = load_profile()
stats = collections.defaultdict(collections.Counter)
for cap in sorted(Path(".").glob("docs/verification/stage-03/**/capture.json")):
    try:
        b = open_bundle(cap.parent)
    except Exception as exc:  # a fixture that is deliberately not a valid bundle
        print("skipped", cap.parent, type(exc).__name__, file=sys.stderr)
        continue
    c = b.capture
    if (c.get("render") or {}).get("state") != "captured":
        continue
    wiki = c["page"]["wiki"]
    w = prof.wikis[wiki]
    doc, reader = read_render(b.artifact(c["render"]["artifact"], limit=16 * 1024 * 1024))
    for t in doc.transclusions:
        if t.in_note is None:
            continue
        els = reader.about_group(t.about)
        cite = any(e.tag == "cite" and "citation" in (e.get("class") or "").split() for g in els for e in g.iter())
        citeref = any(e.tag == "a" and "#CITEREF" in (e.get("href") or "") for g in els for e in g.iter())
        for target, _ in t.templates:
            name = w.canonical_template(target) or target
            stats[(wiki, name)][(cite, citeref, len(t.templates))] += 1
for k, v in sorted(stats.items(), key=lambda kv: -sum(kv[1].values())):
    print(k, dict(v))
