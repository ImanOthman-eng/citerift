"""Read-only survey: Parsoid data-mw body evidence on every retained real bundle.
1) For every source use matched to a render use (current engine), compare source has_body with render body form.
2) For every template-output group, list same-key groups with >=2 uses and their def/reuse composition."""

import json
import sys
from collections import Counter
from pathlib import Path

from citerift.wiki.bundle import open_bundle
from citerift.wiki.extract import ExtractConfig
from citerift.wiki.profile import load_profile
from citerift.wiki.render import read_render
from citerift.wiki.source import scan_source
from citerift.wiki.textmap import ByteMap
from citerift.wiki.units import source_model

root = Path(sys.argv[1])
profile = load_profile()
cfg = ExtractConfig()
agree = Counter()
groups = []
seen_rev = set()
body_forms = Counter()
for cap in sorted(root.glob("docs/verification/stage-03/**/capture.json")):
    rel = cap.parent.relative_to(root).as_posix()
    c = json.loads(cap.read_text())
    page = c.get("page") or {}
    if "SYNTHETIC" in (page.get("title") or "").upper() or "/synthetic" in rel:
        continue
    if (c.get("render") or {}).get("state") != "captured" or not c.get("source"):
        continue
    rk = (page.get("wiki"), page.get("revision_id"))
    if rk in seen_rev:
        continue
    try:
        b = open_bundle(cap.parent)
        text = b.artifact(c["source"]["artifact"], limit=4 * 1024 * 1024).decode()
        html = b.artifact(c["render"]["artifact"], limit=16 * 1024 * 1024)
    except Exception as e:
        print("skip", rel, type(e).__name__, file=sys.stderr)
        continue
    seen_rev.add(rk)
    w = profile.wikis[page["wiki"]]
    scan = scan_source(text, w, profile, cfg.limits())
    render, reader = read_render(html, cfg.max_render_elements)
    model, rec = source_model(scan, w, profile, ByteMap(text), render, reader, text)

    def body(ru, reader=reader):
        el = reader.element_by_path(ru.locator.path)
        try:
            dm = json.loads(el.get("data-mw") or "null")
        except ValueError:
            return "invalid"
        if not isinstance(dm, dict):
            return "none"
        bd = dm.get("body")
        if bd is None:
            return "absent"
        if isinstance(bd, dict):
            return "+".join(sorted(bd.keys())) or "empty"
        return type(bd).__name__

    for ru in render.uses:
        body_forms[body(ru)] += 1
    for u in model.uses:
        if u.id in rec.use_match:
            ru = render.uses[rec.use_match[u.id]]
            agree[(u.zone, u.origin, model.refs[u.ref].has_body, body(ru), rec.use_basis[u.id])] += 1
    # template groups
    by_about = {}
    for u in model.uses:
        if u.id in rec.use_match and rec.use_basis[u.id] == "name_in_template_output":
            ru = render.uses[rec.use_match[u.id]]
            by_about.setdefault((ru.in_transclusion, u.group, u.name), []).append((u, ru))
    for k, pairs in by_about.items():
        if len(pairs) < 2:
            continue
        pairs.sort(key=lambda p: (p[0].start, p[0].position))
        groups.append(
            {
                "bundle": rel,
                "rev": rk,
                "name": k[2],
                "group": k[1],
                "src": [(p[0].id, p[0].origin, model.refs[p[0].ref].has_body) for p in pairs],
                "ren_all": [
                    (x.locator.element_id, body(x))
                    for x in render.uses
                    if x.in_transclusion == k[0] and (x.name or "").strip() == k[2]
                ],
                "engine": [(p[0].id, p[1].locator.element_id) for p in pairs],
            }
        )
print(
    json.dumps(
        {
            "articles": len(seen_rev),
            "render_body_forms": body_forms,
            "matched_use_evidence": sorted([[*list(k), v] for k, v in agree.items()], key=str),
            "groups": groups,
        },
        ensure_ascii=False,
        indent=1,
        default=str,
    )
)
