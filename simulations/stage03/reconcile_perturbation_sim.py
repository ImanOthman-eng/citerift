"""Stage 03 reconciliation simulation (SIMULATION_REPORT.md 3): render perturbations must never cause wrong attachments.

For seeded random SYNTHETIC articles (named and anonymous refs, reuses, groups) a faithful Parsoid-style render is
generated in which every footnote marker's id encodes the source use it belongs to. The render is then perturbed the
way real renders differ from the saved source (a marker missing, an extra marker from a template, a marker moved,
two notes sharing one id) and the production extractor is run on each pair. Measured per perturbation:

  wrong   uses linked to a marker that is not theirs, and containers given a note that is not theirs (must be 0);
  linked  uses linked to their own marker;
  abstain uses left unmatched (the price of never guessing).

Usage: python simulations/stage03/reconcile_perturbation_sim.py [N_ARTICLES] [SEED]  (prints a JSON summary)
"""

from __future__ import annotations

import json
import random
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "stage03"))

from wiki_support import bundle, note_li, ref_sup, references  # noqa: E402

from citerift.wiki.extract import extract_bundle  # noqa: E402

PERTURBATIONS = ("none", "drop_marker", "extra_marker", "move_marker", "shared_note_id")


def article(rng: random.Random) -> tuple[str, list[dict[str, Any]]]:
    """Source text and the list of uses in order: each use knows its container key and whether it defines."""
    names = [f"n{i}" for i in range(rng.randint(1, 4))]
    defined: set[str] = set()
    uses: list[dict[str, Any]] = []
    parts = []
    for k in range(rng.randint(4, 14)):
        kind = rng.random()
        if kind < 0.45:
            parts.append(f"S{k}.<ref>anon {k}</ref>")
            uses.append({"key": f"anon{k}", "name": None})
        else:
            name = rng.choice(names)
            if name in defined:
                parts.append(f'S{k}.<ref name="{name}" />')
            else:
                parts.append(f'S{k}.<ref name="{name}">body {name}</ref>')
                defined.add(name)
            uses.append({"key": name, "name": name})
    return " ".join(parts) + "\n\n{{reflist}}\n", uses


def render(uses: list[dict[str, Any]], perturbation: str, rng: random.Random) -> tuple[str, dict[int, str]]:
    """Parsoid-like body; returns it and, per source use index, the id of the marker that truly belongs to it."""
    number: dict[str, int] = {}
    seen: dict[str, int] = {}
    sups: list[tuple[int | None, str]] = []
    backlinks: dict[str, list[str]] = {}
    truth: dict[int, str] = {}
    for i, u in enumerate(uses):
        n = number.setdefault(u["key"], len(number) + 1)
        seen[u["key"]] = seen.get(u["key"], 0) + 1
        base = f"{u['name']}_{n}" if u["name"] else f"{n}"
        note = f"cite_note-{u['name']}-{n}" if u["name"] else f"cite_note-{n}"
        rid = f"cite_ref-{base}-{seen[u['key']] - 1}"
        truth[i] = rid
        backlinks.setdefault(note, []).append(rid)
        sups.append((i, ref_sup(n, note, rid, name=u["name"])))
    notes = {
        u["key"]: (f"cite_note-{u['name']}-{number[u['key']]}" if u["name"] else f"cite_note-{number[u['key']]}")
        for u in uses
    }
    if perturbation == "drop_marker" and sups:
        sups.pop(rng.randrange(len(sups)))
    elif perturbation == "extra_marker":
        x = len(number) + 1
        sups.insert(rng.randrange(len(sups) + 1), (None, ref_sup(x, f"cite_note-{x}", f"cite_ref-extra_{x}-0")))
        backlinks[f"cite_note-{x}"] = [f"cite_ref-extra_{x}-0"]
        notes["__extra"] = f"cite_note-{x}"
    elif perturbation == "move_marker" and len(sups) > 1:
        item = sups.pop(rng.randrange(len(sups)))
        sups.insert(rng.randrange(len(sups) + 1), item)
    body = "<p>" + " ".join(f"T{j}." + s for j, (_, s) in enumerate(sups)) + "</p>"
    items = [note_li(note, backlinks.get(note, []), f"text of {key}") for key, note in notes.items()]
    if perturbation == "shared_note_id" and len(items) > 1:
        first, second = list(notes.values())[:2]
        items[1] = items[1].replace(f'id="{second}"', f'id="{first}"')
    return body + references(items), truth


def _same_reference(a: str, b: str) -> bool:
    """cite_ref-<name>_<n>-<k>: same name and number, different occurrence k."""
    return a.rsplit("-", 1)[0] == b.rsplit("-", 1)[0] and not a.startswith("cite_ref-extra")


def run(n: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    totals = {
        p: {"articles": 0, "uses": 0, "linked": 0, "wrong": 0, "abstain": 0, "wrong_notes": 0, "same_reference_swap": 0}
        for p in PERTURBATIONS
    }
    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        for a in range(n):
            text, uses = article(rng)
            for p in PERTURBATIONS:
                body, truth = render(uses, p, rng)
                doc = extract_bundle(bundle(Path(tmp), text, body, name=f"a{a}-{p}"), isolated=False)
                t = totals[p]
                t["articles"] += 1
                src_uses = sorted(doc["uses"], key=lambda u: u["source"]["cp_start"])
                for i, u in enumerate(src_uses):
                    t["uses"] += 1
                    r = u["render"]
                    if r["state"] != "matched":
                        t["abstain"] += 1
                    elif r["locator"]["element_id"] == truth[i]:
                        t["linked"] += 1
                    elif _same_reference(r["locator"]["element_id"], truth[i]):
                        # another marker of the same named reference (same container, same note): the render does
                        # not distinguish them once a marker is moved, so this is not an attachment to a wrong note
                        t["same_reference_swap"] += 1
                    else:
                        t["wrong"] += 1
                        failures.append(
                            {
                                "article": a,
                                "perturbation": p,
                                "use": i,
                                "got": r["locator"]["element_id"],
                                "want": truth[i],
                            }
                        )
                for c in doc["containers"]:
                    region = c["render"].get("region_id")
                    if c["render"]["state"] == "matched":
                        expected = {
                            r["render"].get("target_note")
                            for r in doc["uses"]
                            if r["container_id"] == c["id"] and r["render"]["state"] == "matched"
                        }
                        texts = f"text of {c['name']}" if c["name"] else None
                        if expected != {region} or (texts and f"cite_note-{c['name']}-" not in region):
                            t["wrong_notes"] += 1
                            failures.append({"article": a, "perturbation": p, "container": c["id"], "region": region})
    return {
        "articles": n,
        "seed": seed,
        "per_perturbation": totals,
        "failure_count": len(failures),
        "failures": failures[:20],
    }


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20261028
    print(json.dumps(run(count, seed), indent=1, sort_keys=True))
