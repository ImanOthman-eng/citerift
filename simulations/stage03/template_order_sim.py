"""Stage 03 template-order simulation (R-038, owner instruction D-036): a template that shows its parameters in its
own order must never make a use take another use's marker.

For seeded random SYNTHETIC articles, one infobox-like template holds a few named references, each used in two or
more parameters (the definition in one parameter, or in the article text after the template, so that every use in the
template is a reuse). Its Parsoid-style render shows the parameter rows in a random permutation; every marker's id
encodes the source use it belongs to, so a wrong pairing is detected without the extractor's logic. The parameter
values are of the kinds real infoboxes hold:

  text       plain text before the reference ("+1.31", "Munich, Germany" through a piped link)
  val        a number template that shows its numbers ({{val|9494|143}} -> "9,494±143")
  icon       a template that shows only an image (no readable text)
  dup        the same text as another parameter (ambiguous)

and, in the ``adversarial`` mode only, values whose rendered text the source does not show:

  data       a data template that shows an unrelated small number ({{data|k}} -> "7")
  transform  a template that changes its number ({{double|4}} -> "8")

Two render perturbations are applied on top: ``none`` and ``missing_data_mw`` (one marker of the template loses its
data-mw). Measured per mode and perturbation:

  wrong      uses linked to a marker of another reference (another note);
  swap       uses linked to another use's marker of the same reference (what R-038 did; counted by G6b);
  linked     uses linked to their own marker;
  abstain    uses left unmatched.

Usage: python simulations/stage03/template_order_sim.py [N_ARTICLES] [SEED]  (prints a JSON summary)
"""

from __future__ import annotations

import html
import json
import random
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "stage03"))

from wiki_support import bundle, note_li, references  # noqa: E402

from citerift.wiki.extract import extract_bundle  # noqa: E402

MODES = ("clean", "adversarial")
PERTURBATIONS = ("none", "missing_data_mw")
CLEAN_KINDS = ("text", "text", "val", "icon", "dup", "link")
ADVERSARIAL_KINDS = (*CLEAN_KINDS, "data", "transform")
PLACES = ("Munich", "Lyon", "Porto", "Graz", "Turku")


def value(kind: str, rng: random.Random, texts: list[str]) -> tuple[str, str]:
    """A parameter value: (source wikitext, rendered HTML)."""
    if kind == "dup" and texts:
        t = rng.choice(texts)
        return t, html.escape(t)
    if kind in ("text", "dup"):
        t = f"{rng.choice('+-')}{rng.randint(0, 3)}.{rng.randint(0, 99):02d}"
        texts.append(t)
        return t, html.escape(t)
    if kind == "val":
        a, b = rng.randint(1000, 99999), rng.randint(1, 999)
        return f"{{{{val|{a}|{b}}}}}", f"{a:,}±{b}"
    if kind == "icon":
        return "{{icon|star}}", '<img src="./star.png" alt="" width="16" height="16"/>'
    if kind == "data":
        return f"{{{{data|k{rng.randint(1, 99)}}}}}", str(rng.randint(1, 9))
    if kind == "transform":
        n = rng.randint(1, 9)
        return f"{{{{double|{n}}}}}", str(2 * n)
    raise ValueError(kind)


def _link_value(rng: random.Random) -> tuple[str, str]:
    place = rng.choice(PLACES)
    country = rng.choice(("Germany", "France", "Austria"))
    return (
        f"[[{place} (city)|{place}]], {country}",
        f'<a rel="mw:WikiLink" href="./{place}_(city)">{place}</a>, {country}',
    )


def marker(n: int, note: str, ref_id: str, name: str, body: bool, data_mw: bool, about: int) -> str:
    dm: dict[str, Any] = {"name": "ref", "attrs": {"name": name}}
    if body:
        dm["body"] = {"id": f"mw-reference-text-{note}"}
    data = f' data-mw="{html.escape(json.dumps(dm), quote=True)}"' if data_mw else ""
    return (
        f'<sup about="#mwr{about}" class="mw-ref reference" id="{ref_id}" rel="dc:references" '
        f'typeof="mw:Extension/ref"{data}><a href="./SYNTHETIC#{note}"><span class="mw-reflink-text">'
        f'<span class="cite-bracket">[</span>{n}<span class="cite-bracket">]</span></span></a></sup>'
    )


def article(rng: random.Random, mode: str, perturbation: str) -> tuple[str, str, dict[int, str]]:
    """Source text, render body and, per source use (in source order), the id of its own marker."""
    kinds = ADVERSARIAL_KINDS if mode == "adversarial" else CLEAN_KINDS
    names = [f"r{i}" for i in range(rng.randint(1, 3))]
    in_prose = {nm: rng.random() < 0.3 for nm in names}  # definition after the template, in the article text
    params: list[dict[str, Any]] = []
    texts: list[str] = []
    for nm in names:
        for _ in range(rng.randint(2, 5)):
            kind = rng.choice(kinds)
            src, shown = _link_value(rng) if kind == "link" else value(kind, rng, texts)
            params.append({"name": nm, "src": src, "shown": shown})
    for _ in range(rng.randint(0, 3)):  # parameters without a reference
        src, shown = value("text", rng, [])
        params.append({"name": None, "src": src, "shown": shown})
    rng.shuffle(params)  # source order of the parameters
    defined: set[str] = set()
    uses: list[dict[str, Any]] = []  # in source order
    lines = []
    for k, p in enumerate(params):
        p["key"] = f"p{k}"
        ref = ""
        if p["name"] is not None:
            nm = p["name"]
            if in_prose[nm] or nm in defined:
                ref = f'<ref name="{nm}" />'
                p["def"] = False
            else:
                ref = f'<ref name="{nm}">{{{{cite web |title=Work {nm} |url=https://example.org/{nm}}}}}</ref>'
                p["def"] = True
                defined.add(nm)
            uses.append(p)
        p["wt"] = p["src"] + ref
        lines.append(f"| {p['key']} = {p['wt']}\n")
    prose = [nm for nm in names if in_prose[nm]]
    text = (
        "{{Infobox sim\n"
        + "".join(lines)
        + "}}\nThe subject."
        + "".join(
            f'<ref name="{nm}">{{{{cite web |title=Work {nm} |url=https://example.org/{nm}}}}}</ref>' for nm in prose
        )
    )
    text += "\n\n{{reflist}}\n"

    rows = params[:]
    rng.shuffle(rows)  # the order the template shows them
    number: dict[str, int] = {}
    seen: dict[str, int] = {}
    backlinks: dict[str, list[str]] = {}
    about = [0]
    template_uses = [r for r in rows if r["name"] is not None]
    no_dm = rng.randrange(len(template_uses)) if perturbation == "missing_data_mw" and template_uses else -1

    def place(p: dict[str, Any], *, body: bool, data_mw: bool = True) -> str:
        nm = p["name"]
        n = number.setdefault(nm, len(number) + 1)
        note = f"cite_note-{nm}-{n}"
        rid = f"cite_ref-{nm}_{n}-{seen.get(nm, 0)}"
        seen[nm] = seen.get(nm, 0) + 1
        backlinks.setdefault(note, []).append(rid)
        p["truth"] = rid
        about[0] += 1
        return marker(n, note, rid, nm, body, data_mw, about[0])

    cells = []
    for r in rows:
        cell = r["shown"]
        if r["name"] is not None:
            cell += place(r, body=r["def"], data_mw=template_uses.index(r) != no_dm)
        cells.append(f"<tr><th>{r['key']}</th><td>{cell}</td></tr>")
    part = {"target": {"wt": "Infobox sim"}, "params": {p["key"]: {"wt": p["wt"]} for p in params}, "i": 0}
    dm = html.escape(json.dumps({"parts": [{"template": part}]}, ensure_ascii=False), quote=True)
    body = f'<table about="#mwt1" typeof="mw:Transclusion" data-mw="{dm}"><tbody>{"".join(cells)}</tbody></table>'
    prose_uses = [{"name": nm} for nm in prose]
    body += "<p>The subject." + "".join(place(p, body=True) for p in prose_uses) + "</p>"
    items = [note_li(f"cite_note-{nm}-{n}", backlinks[f"cite_note-{nm}-{n}"], f"Work {nm}") for nm, n in number.items()]
    body += references(items)
    truth = {i: u["truth"] for i, u in enumerate(uses + prose_uses)}
    return text, body, truth


def _same_reference(a: str, b: str) -> bool:
    return a.rsplit("-", 1)[0] == b.rsplit("-", 1)[0]


def run(n: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    totals = {
        f"{m}/{p}": {"articles": 0, "uses": 0, "linked": 0, "wrong": 0, "swap": 0, "abstain": 0}
        for m in MODES
        for p in PERTURBATIONS
    }
    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        for a in range(n):
            for m in MODES:
                for p in PERTURBATIONS:
                    text, body, truth = article(rng, m, p)
                    doc = extract_bundle(bundle(Path(tmp), text, body, name=f"a{a}-{m}-{p}"), isolated=False)
                    t = totals[f"{m}/{p}"]
                    t["articles"] += 1
                    named = sorted((u for u in doc["uses"] if u["name"]), key=lambda u: u["source"]["cp_start"])
                    if len(named) != len(truth):
                        raise RuntimeError(f"generator error: article {a} {m} {p}")
                    for i, u in enumerate(named):
                        t["uses"] += 1
                        r = u["render"]
                        if r["state"] != "matched":
                            t["abstain"] += 1
                            continue
                        got = r["locator"]["element_id"]
                        if got == truth[i]:
                            t["linked"] += 1
                            continue
                        t["swap" if _same_reference(got, truth[i]) else "wrong"] += 1
                        failures.append({"article": a, "mode": m, "perturbation": p, "use": i, "got": got})
    return {"articles": n, "seed": seed, "totals": totals, "failure_count": len(failures), "failures": failures[:20]}


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20261104
    print(json.dumps(run(count, seed), indent=1, sort_keys=True))
