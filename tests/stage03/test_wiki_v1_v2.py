"""RF-56 (V1), RF-57 (V2): altered documents, not incorrect extraction. SYNTHETIC/offline."""

from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, extract, note_li, ref_sup, references

from citerift.wiki.bundle import open_bundle
from citerift.wiki.canonical import digest
from citerift.wiki.render import read_render
from citerift.wiki.verify import replay_bundle, verify_bundle


def redigest(doc: dict[str, Any]) -> None:
    doc["accounting"]["markers"] = dict(Counter(m["state"] for m in doc["markers"]))
    doc["extraction_digest"] = digest({k: v for k, v in doc.items() if k != "extraction_digest"})


@pytest.mark.negative
def test_schema_integer_float_returns_report_not_exception(tmp_path: Path) -> None:
    """RF-58: JSON Schema accepts 400000.0 as integer, but ExtractConfig deliberately rejects a float."""
    path, genuine, _ = probe(tmp_path, "outside")
    genuine["config"]["max_nodes"] = 400000.0
    genuine["config_digest"] = digest(genuine["config"])
    redigest(genuine)
    result = verify_bundle(path, genuine)
    assert not result["verified"]
    assert "BUNDLE_SCHEMA_INVALID" in {i["code"] for i in result["issues"]}


def probe(tmp: Path, variant: str, wiki: str = "en") -> tuple[Path, dict[str, Any], dict[str, Any]]:
    word = "Retracted" if wiki == "en" else "مسحوب"
    inners = {
        "outside": "Paper. Smith 2001.",
        "region": "Paper. Smith 2001.",
        "other_note": "Paper. Smith 2001.",
        "negated": f"Paper. {'not' if wiki == 'en' else 'غير'} {word}.",
        "quoted": f"Paper. <q>{word}</q>.",
        "substring": "Paper. unretracted." if wiki == "en" else "ورقة. مسحوبات.",
        "prefix": f"Paper. {word}: title.",
        "hidden": f"Paper. <span hidden>{word}</span>.",
        "citation": f"Paper. <cite>{word}</cite>.",
        "interrupted": "Paper. Re<span hidden>x</span>tracted."
        if wiki == "en"
        else "ورقة. مس<span hidden>x</span>حوب.",
        "repeated": f"Paper. {word}. {'x ' * 60} not {word}.",
    }
    text = 'A.<ref name="a">Paper.</ref>'
    uses = ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
    notes = [note_li("cite_note-a-1", ["cite_ref-a_1-0"], inners[variant])]
    if variant == "other_note":
        text += ' B.<ref name="b">Second.</ref>'
        uses += ref_sup(2, "cite_note-b-2", "cite_ref-b_2-0", name="b")
        notes.append(note_li("cite_note-b-2", ["cite_ref-b_2-0"], word))
    body = "<p>A." + uses + "</p>" + references(notes) + f'<p id="unrelated">{word}</p>'
    path = bundle(tmp, text, body, wiki=wiki, name=f"{wiki}-{variant}")
    genuine = extract(path, isolated=True)
    forged = copy.deepcopy(genuine)
    m = forged["markers"][0]
    if variant in {"outside", "region", "substring"}:
        b = open_bundle(path)
        _, reader = read_render(b.artifact(b.capture["render"]["artifact"], limit=16 * 1024 * 1024))
        el = next(e for e in reader.doc.iter("p") if e.get("id") == "unrelated")
        loc = reader.locator(el).to_json() if variant != "substring" else m["region"]["locator"]
        m["evidence"] = [
            {
                "kind": "warning",
                "part": "text",
                "term": word.lower(),
                "matched": word if variant != "substring" else word.lower(),
                "snippet": word,
                "locator": loc,
            }
        ]
        if variant == "region":
            m["region"].update(region_id="forged", locator=loc)
    elif variant == "other_note":
        m["evidence"] = copy.deepcopy(forged["markers"][1]["evidence"])
    else:
        ev = next((e for e in m["evidence"] if e["kind"] != "warning"), m["evidence"][0])
        ev.update(kind="warning", part="text")
        ev.pop("exclusion", None)
        ev.pop("hidden_basis", None)
    m["state"] = "recognized_warning_text"
    redigest(forged)
    return path, genuine, forged


@pytest.mark.regression
@pytest.mark.parametrize("wiki", ["en", "ar"])
@pytest.mark.parametrize(
    "variant",
    [
        "outside",
        "region",
        "other_note",
        "negated",
        "quoted",
        "substring",
        "prefix",
        "hidden",
        "citation",
        "interrupted",
        "repeated",
    ],
)
def test_warning_witness_is_bound_and_classified_from_retained_context(tmp_path: Path, variant: str, wiki: str) -> None:
    path, genuine, forged = probe(tmp_path, variant, wiki)
    assert verify_bundle(path, genuine)["verified"]
    assert replay_bundle(path, recorded=genuine)["replay"]["state"] == "reproduced"
    assert replay_bundle(path, recorded=forged)["replay"]["state"] == "differs"
    checked = verify_bundle(path, forged)
    assert not checked["verified"], (wiki, variant)
    assert all(
        c["failed"] == 0
        for c in checked["checks"]
        if c["name"] in {"extraction digest", "markers by state", "artifact hashes"}
    )
