"""Prototype (read-only): local text anchors for same-name uses in one template output."""
import html as H, json, re, sys, unicodedata
from pathlib import Path
from citerift.wiki.bundle import open_bundle
from citerift.wiki.extract import ExtractConfig
from citerift.wiki.profile import load_profile
from citerift.wiki.render import read_render
from citerift.wiki.source import scan_source
from citerift.wiki.textmap import ByteMap
from citerift.wiki.units import source_model

REF = re.compile(r"(?is)<ref\b[^>]*/>|<ref\b[^>]*>.*?</ref\s*>")
def norm(s):
    s = unicodedata.normalize("NFC", H.unescape(s)).replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()
def src_tail(text, model, u):
    r = model.refs[u.ref]
    t = model.templates.get(u.template) if u.template is not None else None
    if t is None: return None
    p = next((p for p in t.params if p.value_start <= r.start < p.value_end), None)
    if p is None: return None
    raw = text[p.value_start:r.start]
    raw = re.sub(r"(?s)<!--.*?-->", "", raw)
    raw = REF.sub("", raw)
    cut = max(raw.rfind("}}"), raw.rfind("{{"), raw.rfind("|"))  # after the last construct we cannot render
    raw = raw[cut + 2 if raw[cut:cut+2] in ("}}", "{{") else cut + 1:] if cut >= 0 else raw
    raw = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", raw)
    raw = re.sub(r"\[(?:https?:)?//\S+\s+([^\]]*)\]", r"\1", raw)
    raw = re.sub(r"'{2,}", "", raw)
    raw = re.sub(r"<[^>]*>", "", raw)
    if "[" in raw or "]" in raw or "{" in raw or "}" in raw: return None
    s = norm(raw)
    return s[-32:] if len(s) >= 2 else None
BLOCK = {"td", "th", "li", "dd", "dt", "p", "div", "caption", "figcaption", "body"}
def ren_prefix(reader, ru):
    el = reader.element_by_path(ru.locator.path)
    blk = el.getparent()
    while blk is not None and blk.tag not in BLOCK: blk = blk.getparent()
    if blk is None: return None
    out = []
    def walk(n):
        if n is el: raise StopIteration
        t = (n.get("typeof") or "").split()
        skip = "mw:Extension/ref" in t or "reference" in (n.get("class") or "").split() or "display:none" in (n.get("style") or "").replace(" ", "")
        if not skip:
            if n.text: out.append(n.text)
            for ch in n:
                if isinstance(ch.tag, str): walk(ch)
                if ch.tail: out.append(ch.tail)
    try: walk(blk)
    except StopIteration: pass
    return norm("".join(out))

root = Path(sys.argv[1]); groups = json.load(open(sys.argv[2]))["groups"]
profile = load_profile(); cfg = ExtractConfig()
for g in groups:
    cap = root / g["bundle"] / "capture.json"; c = json.loads(cap.read_text())
    b = open_bundle(cap.parent); page = c["page"]; w = profile.wikis[page["wiki"]]
    text = b.artifact(c["source"]["artifact"], limit=4<<20).decode()
    render, reader = read_render(b.artifact(c["render"]["artifact"], limit=16<<20), cfg.max_render_elements)
    model, rec = source_model(scan_source(text, w, profile, cfg.limits()), w, profile, ByteMap(text), render, reader, text)
    uses = {u.id: u for u in model.uses}
    src = [uses[s[0]] for s in g["src"]]
    ren = [x for x in render.uses if x.locator.element_id in {e for e, _ in g["ren_all"]}]
    st = [src_tail(text, model, u) for u in src]; rp = [ren_prefix(reader, x) for x in ren]
    agree = [[j for j in range(len(ren)) if st[i] and rp[j] is not None and rp[j].endswith(st[i])] for i in range(len(src))]
    back = {}
    for i, js in enumerate(agree):
        for j in js: back.setdefault(j, []).append(i)
    bij = all(len(js) == 1 and back[js[0]] == [i] for i, js in enumerate(agree))
    pairs = [(src[i].id, ren[agree[i][0]].locator.element_id) for i in range(len(src))] if bij else None
    print(g["rev"], g["name"], "BIJECTION" if bij else "no", pairs == [tuple(e) for e in g["engine"]] if bij else "")
    for i, u in enumerate(src): print("   S", u.id, repr(st[i]))
    for j, x in enumerate(ren): print("   R", x.locator.element_id, repr(rp[j][-40:] if rp[j] else rp[j]))
