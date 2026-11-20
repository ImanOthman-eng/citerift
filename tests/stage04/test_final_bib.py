"""Final corrective cycle (owner decision D-083): bib-1, the layer of the freeze-3 candidate c3854b8, kept as history.

Owner decision D-085 did not accept c3854b8; D-086 and D-087 replaced bib-1 by bib-2 in the production engine
(``test_final_bib2.py``). bib-1 stays the reference point of property B4 (dt-4 never yields a positive dt-3 would not),
so it is checked here as it was committed (D-074 style: the historical module is read from git at c3854b8, never the
working tree's):

- The adversarial bib-1 corpus (``corpus/BIB_CORPUS.json``, unchanged) gives, through c3854b8's module and through the
  independent bib-1 reference model (``simulations/stage04/bib_reference.py``), exactly its expected verdict fields.
- c3854b8's module and the reference agree on the whole output over seeded generated templates and records.
"""

from __future__ import annotations

import ast
import json
import random
import sys
from pathlib import Path
from typing import Any

import history_support as H
import pytest

from citerift.investigation import bibliographic as PROD

REPO = Path(__file__).resolve().parents[2]
SIM = REPO / "simulations" / "stage04"
CORPUS = REPO / "docs" / "verification" / "stage-04" / "final-cycle" / "corpus" / "BIB_CORPUS.json"
sys.path.insert(0, str(SIM))

import bib_reference as BR  # noqa: E402

pytestmark = pytest.mark.unit

CASES: list[dict[str, Any]] = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]
PROFILE = BR.load_profile(SIM / "bib-reference-profile.json")
B = H.bib1()


def _record(raw: Any) -> B.RecordObject | None:
    return B.RecordObject.from_json(raw) if raw is not None else None


def _production(case: dict[str, Any]) -> tuple[B.CitedObject | None, dict[str, Any]]:
    cited = B.cited_object(case["source"], case["wiki"])
    out = B.compare(cited, _record(case["record"])).to_json()
    out.pop("version")
    return cited, out


def test_the_reference_model_imports_no_production_code() -> None:
    tree = ast.parse((SIM / "bib_reference.py").read_text(encoding="utf-8"))
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {str(n.module) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not any(m.startswith("citerift") for m in names), names


def test_the_production_profile_is_the_independently_extracted_profile() -> None:
    prod = PROD.profile()
    assert prod["profile_version"] == "bib-profile-2"  # bib-2's profile (D-087): bib-1's plus TitleType, TitleNote
    for wiki in ("ar", "en"):
        assert {k: sorted(v) for k, v in prod["wikis"][wiki]["aliases"].items()} == {
            k: sorted(v) for k, v in PROFILE["wikis"][wiki]["aliases"].items()
        }, wiki


def test_the_corpus_covers_every_required_category() -> None:
    required = {
        "garry", "true_original", "punctuation", "author_format", "truncated_authors", "subtitle", "comment", "reply",
        "editorial", "erratum", "withdrawal", "retraction_notice", "eoc", "same_title_other_object",
        "incompatible_description", "malformed", "missing_title", "missing_author", "arabic", "insufficient",
    }  # fmt: skip
    assert required <= {c["category"] for c in CASES}
    assert len({c["id"] for c in CASES}) == len(CASES)
    objects = {c["expect"]["object"] for c in CASES}
    assert objects == {"COMPATIBLE", "INSUFFICIENT", "MATERIAL_CONFLICT"}


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_corpus_case_production_and_reference(case: dict[str, Any]) -> None:
    cited, got = _production(case)
    for field, want in case["expect"].items():
        value = cited is None if field == "cited_none" else got[field]
        assert value == want, (field, value, want)
    ref_cited = BR.cited_object(case["source"], case["wiki"], PROFILE)
    assert (cited.to_json() if cited is not None else None) == ref_cited
    if ref_cited is not None and case["record"] is not None:
        assert BR.compare(ref_cited, case["record"]) == got


# Differential: seeded generated templates and records ----------------------------------------------------------------

WORDS = [
    "Thermal", "drift", "of", "synthetic", "lattice", "sensors", "a", "field", "study", "Coastal", "erosion",
    "budgets", "Comment", "comments", "Reply", "Erratum", "Correction", "corrigendum", "Retraction", "Withdrawal",
    "Expression", "concern", "response", "to", "RETRACTED:", "Retracted", "article:", "Letter:", "α", "Ångström",
    "naïve", "Ⅻ", "x_y", "—", "–", ":", "'", ";", "2010", "١٩٩٩", "تعليق", "الرد", "تصحيح", "سحب", "دراسة",
    "ميدانية", "والرد", "Müller", "O'Brien", "et", "al.", "et al", "Jr.", "ΔT", "ﬁeld",
]  # fmt: skip
MARKUP = ["''", "'''", "[[Lattice|lattice]]", "[[drift]]", "<!-- c -->", "&amp;", "{{lang|fr|terme}}", "<i>x</i>", "\n"]
NAMES = ["Mara Q Lindqvist", "Tomas Oyelaran", "Hana Brezinova", "L Iorio", "Kam L E Hon", "Ann Author", "محمد علي"]
EN_PARAMS = [
    "title", "script-title", "trans-title", "chapter", "author", "author1", "last", "last1", "first1", "last2",
    "authors", "vauthors", "editor1", "collaboration", "journal", "work", "website", "date", "year", "volume", "issue",
    "pages", "page", "doi", "pmid", "Title", "title ", " last3",
]  # fmt: skip
AR_PARAMS = [
    "عنوان", "الأخير1", "الأول1", "مؤلف", "صحيفة", "تاريخ", "سنة", "المجلد", "العدد", "صفحات", "title", "last1",
]  # fmt: skip


def _value(rng: random.Random) -> str:
    parts = [rng.choice(WORDS + MARKUP) for _ in range(rng.randint(0, 8))]
    if rng.random() < 0.1:
        parts.insert(0, rng.choice(["en:", "ar:", "zh-Hant:", "xx-1:"]))
    return " ".join(parts)


def _template(rng: random.Random, wiki: str) -> str:
    names = AR_PARAMS if wiki == "ar" else EN_PARAMS
    head = rng.choice(["cite journal", "Cite journal", "استشهاد بدورية محكمة", "citation"])
    params = []
    for _ in range(rng.randint(0, 7)):
        if rng.random() < 0.08:
            params.append(_value(rng))  # positional
        else:
            params.append(f"{rng.choice(names)}={_value(rng)}")
    text = "{{" + head + "".join(" |" + p for p in params) + "}}"
    if rng.random() < 0.05:
        text = rng.choice(["", " ", "x "]) + text + rng.choice(["", " ", " {{x}}"])
    return text


def _record_raw(rng: random.Random) -> dict[str, Any]:
    def title() -> Any:
        return rng.choice([None, "", 5, " ".join(rng.choice(WORDS) for _ in range(rng.randint(1, 8)))])

    def authors() -> Any:
        return rng.choice([None, "", ["x"], ";".join(rng.sample(NAMES, rng.randint(1, 3)))])

    return {
        "title": title(),
        "authors": authors(),
        "journal": rng.choice([None, "Virology Journal", "Cell", 3]),
        "original_year": rng.choice([None, 2010, 2011, 1999, True, "2010"]),
    }


def test_the_c3854b8_module_equals_the_reference_on_generated_cases() -> None:
    rng = random.Random(20261119)
    differ: list[Any] = []
    seen_objects: set[str] = set()
    for _ in range(4000):
        wiki = rng.choice(["en", "ar"])
        source = _template(rng, wiki)
        raw = _record_raw(rng)
        cited = B.cited_object(source, wiki)
        ref_cited = BR.cited_object(source, wiki, PROFILE)
        if (cited.to_json() if cited is not None else None) != ref_cited:
            differ.append(("cited", wiki, source))
            continue
        if ref_cited is None:
            continue
        got = B.compare(cited, B.RecordObject.from_json(raw)).to_json()
        got.pop("version")
        if got != BR.compare(ref_cited, raw):
            differ.append(("compare", wiki, source, raw))
        seen_objects.add(got["object"])
    assert differ == []
    assert seen_objects == {"COMPATIBLE", "INSUFFICIENT", "MATERIAL_CONFLICT"}


def test_no_section2_input_of_another_type_raises() -> None:
    """Spec B8: a record or a committed description outside its type yields INSUFFICIENT, never an exception."""
    for raw in (None, 5, "x", [], {"title": ["a"], "authors": {"x": 1}, "journal": 4, "original_year": 2.5}):
        rec = B.RecordObject.from_json(raw)
        assert B.compare(B.cited_object("{{cite journal |title=A}}", "en"), rec).object == B.OBJ_INSUFFICIENT
    for raw in (None, 5, [], {"titles": "x", "authors": [3]}):
        assert B.compare(B.CitedObject.from_json(raw), _record({"title": "A"})).object == B.OBJ_INSUFFICIENT
    assert B.cited_object("{{cite journal |title=A}}", "fr") is None


def test_bib2_extends_the_pinned_bib1_profile_and_keeps_the_parser() -> None:
    """BIBLIOGRAPHIC_SPEC_2.md 2.2: bib-1 at c3854b8 still pins ``bib-profile-1.json`` (unchanged); the production bib-2
    pins ``bib-profile-2.json``, which holds every bib-1 alias list unchanged, from the same CS1 revisions, plus the
    keys TitleType and TitleNote; the parser pin is unchanged."""
    import hashlib

    data = REPO / "src" / "citerift" / "investigation" / "data"
    raw1, raw2 = (data / "bib-profile-1.json").read_bytes(), (data / "bib-profile-2.json").read_bytes()
    assert hashlib.sha256(raw1).hexdigest() == B.PROFILE_SHA256
    assert hashlib.sha256(raw2).hexdigest() == PROD.PROFILE_SHA256
    p1, p2 = json.loads(raw1), json.loads(raw2)
    assert set(p1["wikis"]) == set(p2["wikis"]) == {"ar", "en"}
    for wiki in p1["wikis"]:
        a1, a2 = p1["wikis"][wiki]["aliases"], p2["wikis"][wiki]["aliases"]
        assert p1["wikis"][wiki]["source"] == p2["wikis"][wiki]["source"]
        assert {k: a2[k] for k in a1} == a1 and set(a2) - set(a1) == {"TitleType", "TitleNote"}
    assert (B.BIB_VERSION, PROD.BIB_VERSION) == ("bib-1", "bib-2")
    assert B.PARSER_VERSION == PROD.PARSER_VERSION == "0.7.2"
