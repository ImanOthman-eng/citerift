"""Owner decisions D-086 and D-087: the bibliographic-object consistency layer bib-2 and rules D-13a, D-13b, D-13c.

- The fail-first corpus (``docs/verification/stage-04/final-cycle/corpus/BIB2_CORPUS.json``: every bib-1 case with its
  bib-2 verdict, and the D-086/D-087 cases, written from BIBLIOGRAPHIC_SPEC_2.md before production was compared with
  it) gives, through production and through the independent reference model (``simulations/stage04/
  bib2_reference.py``, written from the specification alone), exactly the expected verdict of every case.
- Production equals the reference over seeded generated templates and records (format characters, packed author
  values, every author form, bounds), and never yields a pass where bib-1 (c3854b8, read from git) yields a conflict
  (property B4); a description bib-1 could not produce is UNAVAILABLE in bib-2, never natural absence (D-086).
- Through the production detector on concrete inputs: UNAVAILABLE gives D-13b, NOT_ESTABLISHED D-13c, a conflict
  D-13a, every other case dt-2's D-14; none of them overrides an earlier rule; claims validate and are supported by the
  unit's bibliographic item (which records why a check was unavailable) and the records; DETECT refuses a unit whose
  committed bibliographic result is inconsistent.
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
import step9_support as S9

from citerift.investigation import bibliographic as B
from citerift.investigation import dt1, sets
from citerift.investigation.adapters.detect import DetectFailure
from citerift.investigation.adapters.detector import dt1_detector
from citerift.investigation.explanations import REASON_TEXT
from citerift.investigation.schemas import CLAIM, COMMON, problems, ref_problems

REPO = Path(__file__).resolve().parents[2]
SIM = REPO / "simulations" / "stage04"
CORPUS = REPO / "docs" / "verification" / "stage-04" / "final-cycle" / "corpus" / "BIB2_CORPUS.json"
sys.path.insert(0, str(SIM))

import bib2_reference as BR2  # noqa: E402
import bib_reference as BR1  # noqa: E402
import dt4_reference as R4  # noqa: E402

pytestmark = pytest.mark.unit

CASES: list[dict[str, Any]] = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]
PROFILE = BR2.load_profile(SIM / "bib2-reference-profile.json")
BIB1 = H.bib1()
UNAVAILABLE = "UNAVAILABLE"


def _source(case: dict[str, Any]) -> bytes:
    hexed = case.get("source_bytes_hex")
    return bytes.fromhex(hexed) if hexed else case["source"].encode("utf-8")


def _verdict(cited: B.CitedObject | B.Unavailable, record: Any) -> dict[str, Any]:
    """The production result of one (unit, record) pair in the corpus's terms."""
    if isinstance(cited, B.Unavailable):
        return {"object": UNAVAILABLE, "reasons": [cited.reason], "unavailable": cited.reason}
    out = B.compare(cited, B.RecordObject.from_json(record) if record is not None else None).to_json()
    out.pop("version")
    return out


def _reference(case: dict[str, Any]) -> dict[str, Any]:
    described = BR2.describe(_source(case), case["wiki"], PROFILE)
    if described["state"] == UNAVAILABLE:
        return {"object": UNAVAILABLE, "reasons": [described["reason"]], "unavailable": described["reason"]}
    return BR2.compare(described["fields"], case["record"])


def test_the_reference_models_import_no_production_code() -> None:
    for name in ("bib2_reference.py", "dt4_reference.py"):
        tree = ast.parse((SIM / name).read_text(encoding="utf-8"))
        names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        names |= {str(n.module) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not any(m.startswith(("citerift", "bib_reference", "dt3_reference", "dt2_reference")) for m in names)


def test_the_corpus_covers_every_required_category() -> None:
    required = {
        "garry", "true_original", "comment", "reply", "erratum", "withdrawal", "retraction_notice", "eoc", "arabic",
        "unavailable", "unavailable_boundary", "natural_absence", "format_character", "format_character_arabic",
        "weak_compatibility", "packed_authors",
    }  # fmt: skip
    assert required <= {c["category"] for c in CASES}
    assert len({c["id"] for c in CASES}) == len(CASES)
    assert {c["expect"]["object"] for c in CASES} == {
        "COMPATIBLE", "INSUFFICIENT", "NOT_ESTABLISHED", "MATERIAL_CONFLICT", UNAVAILABLE,
    }  # fmt: skip
    reasons = {r for c in CASES for r in c["expect"]["reasons"]}
    assert set(B.REASONS) <= reasons, set(B.REASONS) - reasons
    assert {c["requirement"] for c in CASES} == {"bib-1", "D-086", "D-087 G-04", "D-087 A-02"}


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_corpus_case_production_and_reference(case: dict[str, Any]) -> None:
    cited = B.describe(_source(case), case["wiki"])
    got = _verdict(cited, case["record"])
    for field, want in case["expect"].items():
        assert got.get(field) == want, (field, got.get(field), want)
    ref = _reference(case)
    if isinstance(cited, B.Unavailable):
        assert ref == got
    else:
        described = BR2.describe(_source(case), case["wiki"], PROFILE)
        assert described == {"state": "DESCRIBED", "fields": cited.to_json()}
        assert ref == got


# Generated cases ------------------------------------------------------------------------------------------------------

# Invisible characters (spec 3.1): category Cf, and Default_Ignorable code points of other categories (a letter, an
# unassigned code point, marks, a tag character).
FORMAT = [
    "\u00ad", "\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u200f", "\u061c", "\u202a", "\u3164", "\u2065",
    "\ufe0f", "\u034f", "\u180b", "\U000e0041",
]  # fmt: skip
WORDS = [
    "Thermal", "drift", "of", "synthetic", "lattice", "sensors", "a", "field", "study", "Coastal", "erosion",
    "budgets", "Comment", "comments", "Reply", "Erratum", "Correction", "corrigendum", "Retraction", "Withdrawal",
    "Expression", "concern", "response", "to", "RETRACTED:", "Retracted", "article:", "Letter:", "Remarks", "α",
    "naïve", "Ⅻ", "x_y", "—", ":", "'", ";", ",", "and", "&", "2010", "١٩٩٩", "تعليق", "الرد", "تصحيح", "سحب",
    "دراسة", "ميدانية", "والرد", "،", "؛", "Müller", "O'Brien", "et", "al.", "et al", "Jr.", "ﬁeld", "Lindqvist",
    "Oyelaran", "Quill", "M", "MQ", "Q.", "و",
]  # fmt: skip
MARKUP = [
    "''", "[[Lattice|lattice]]", "<!-- c -->", "&amp;", "{{lang|fr|terme}}", "<i>x</i>", "\n", "&#xD800;", "{{snd}}",
    "{{{1}}}",
]  # fmt: skip
NAMES = [
    "Mara Q Lindqvist", "Tomas Oyelaran", "Hana Brezinova", "L Iorio", "Kam L E Hon", "محمد علي", "Sa\u00adad Ali",
]  # fmt: skip
TITLES = [
    "Thermal drift of synthetic lattice sensors: a field study", "Comment on the lattice debate", "تعليق على دراسة",
]  # fmt: skip
EN_PARAMS = [
    "title", "script-title", "trans-title", "chapter", "author", "author1", "last", "last1", "first1", "last2",
    "people", "credits", "vauthors", "authors", "editor1", "journal", "date", "year", "volume", "pages", "doi",
    "Title", "title ", " last3", "title<!-- c -->", "{{echo|title}}",
]  # fmt: skip
AR_PARAMS = [
    "عنوان", "الأخير1", "الأول1", "مؤلف", "المؤلفون", "authors", "عدة مؤلفين", "صحيفة", "تاريخ", "سنة", "title",
    "last1", "host",
]  # fmt: skip


def _value(rng: random.Random) -> str:
    parts = [rng.choice(WORDS + MARKUP) for _ in range(rng.randint(0, 8))]
    if rng.random() < 0.3:
        word = rng.randrange(len(parts) + 1)
        parts.insert(word, rng.choice(FORMAT))
    if rng.random() < 0.2 and parts:
        k = rng.randrange(len(parts))
        w = parts[k]
        cut = rng.randrange(len(w) + 1)
        parts[k] = w[:cut] + rng.choice(FORMAT) + w[cut:]
    sep = rng.choice([" ", " ", " ", ""])
    return sep.join(parts)


def _template(rng: random.Random, wiki: str) -> str:
    names = AR_PARAMS if wiki == "ar" else EN_PARAMS
    head = rng.choice(["cite journal", "Cite journal", "استشهاد بدورية محكمة", "citation"])
    params = []
    for _ in range(rng.randint(0, 7)):
        if rng.random() < 0.08:
            params.append(_value(rng))
        elif rng.random() < 0.15:
            params.append(f"{rng.choice(names)}={rng.choice(TITLES)}{rng.choice(['', ': x', ' (Reply)'])}")
        else:
            params.append(f"{rng.choice(names)}={_value(rng)}")
    text = "{{" + head + "".join(" |" + p for p in params) + "}}"
    roll = rng.random()
    if roll < 0.04:
        text = rng.choice(["", " ", "x "]) + text + rng.choice(["", " ", " {{x}}"])
    elif roll < 0.06:
        text = text[:-1]
    elif roll < 0.07:
        text = text[:-2] + " |quote=" + "x" * rng.choice([16300, 16400]) + "}}"
    elif roll < 0.08:
        text = text[:-2] + "".join(f" |last{i}=Q{i}" for i in range(1, rng.choice([64, 66]))) + "}}"
    elif roll < 0.09:
        text = text[:-2] + " |trans-title=" + "y" * rng.choice([4000, 4100]) + "}}"
    return text


def _record_raw(rng: random.Random) -> dict[str, Any]:
    def title() -> Any:
        if rng.random() < 0.3:
            return rng.choice(TITLES) + rng.choice(["", rng.choice(FORMAT)])
        return rng.choice([None, "", 5, " ".join(rng.choice(WORDS) for _ in range(rng.randint(1, 8)))])

    def authors() -> Any:
        return rng.choice([None, "", ["x"], ";".join(rng.sample(NAMES, rng.randint(1, 3)))])

    return {
        "title": title(),
        "authors": authors(),
        "journal": rng.choice([None, "Virology Journal", "Cell", 3]),
        "original_year": rng.choice([None, 2010, 2011, 1999, True, "2010"]),
    }


def _generated(n: int, seed: int) -> list[tuple[str, str, dict[str, Any]]]:
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        wiki = rng.choice(["en", "ar"])
        out.append((wiki, _template(rng, wiki), _record_raw(rng)))
    return out


GENERATED = _generated(6000, 20261120)


def test_production_equals_the_reference_on_generated_cases() -> None:
    differ: list[Any] = []
    seen: set[str] = set()
    for wiki, source, raw in GENERATED:
        cited = B.describe(source.encode("utf-8"), wiki)
        ref = BR2.describe(source.encode("utf-8"), wiki, PROFILE)
        if isinstance(cited, B.Unavailable):
            if ref != {"state": UNAVAILABLE, "reason": cited.reason}:
                differ.append(("describe", wiki, source))
            seen.add(cited.reason)
            continue
        if ref != {"state": "DESCRIBED", "fields": cited.to_json()}:
            differ.append(("describe", wiki, source))
            continue
        got = B.compare(cited, B.RecordObject.from_json(raw)).to_json()
        got.pop("version")
        if got != BR2.compare(ref["fields"], raw):
            differ.append(("compare", wiki, source, raw))
        seen.add(got["object"])
        seen.add(f"readings={got['readings']}")
    assert differ == []
    want = {"COMPATIBLE", "INSUFFICIENT", "NOT_ESTABLISHED", "MATERIAL_CONFLICT", "readings=1", "readings=3"}
    assert want | set(B.UNAVAILABLE_REASONS) <= seen, seen


def test_b4_bib2_never_passes_what_bib1_refused_and_never_reads_a_failure_as_absence() -> None:
    """Property B4 against bib-1 as committed at c3854b8 (read from git), over the generated cases and the corpus:
    a pair bib-2 lets through (COMPATIBLE or INSUFFICIENT) is never a bib-1 MATERIAL_CONFLICT, and a unit bib-1 could
    not describe (C = ⊥) is UNAVAILABLE in bib-2 (D-086), never described."""
    pairs = [(w, s, r) for w, s, r in GENERATED]
    pairs += [(c["wiki"], c["source"], c["record"]) for c in CASES if c["source"] is not None]
    passes = 0
    for wiki, source, raw in pairs:
        old = BIB1.cited_object(source, wiki)
        new = B.describe(source.encode("utf-8"), wiki)
        if old is None:
            assert isinstance(new, B.Unavailable), source
            continue
        if isinstance(new, B.Unavailable):
            continue
        result = B.compare(new, B.RecordObject.from_json(raw)).object
        if result in (B.OBJ_COMPATIBLE, B.OBJ_INSUFFICIENT):
            passes += 1
            assert BIB1.compare(old, BIB1.RecordObject.from_json(raw)).object != BIB1.MATERIAL_CONFLICT, (source, raw)
    assert passes > 500, passes


def test_b9_one_reading_without_invisible_characters() -> None:
    for wiki, source, raw in GENERATED:
        cited = B.describe(source.encode("utf-8"), wiki)
        if isinstance(cited, B.Unavailable):
            continue
        record = B.RecordObject.from_json(raw)
        strings = [*cited.strings(), *(record.strings() if record is not None else ())]
        if not any(B.has_invisible(s) for s in strings):
            assert B.compare(cited, record).readings == 1


def test_the_bib1_reference_still_describes_the_corpus_sources_it_did() -> None:
    """The independent bib-1 reference agrees with bib-1 at c3854b8 on every bib-2 corpus source (B4's base)."""
    profile1 = BR1.load_profile(SIM / "bib-reference-profile.json")
    for c in CASES:
        if c["source"] is None:
            continue
        old = BIB1.cited_object(c["source"], c["wiki"])
        assert (old.to_json() if old is not None else None) == BR1.cited_object(c["source"], c["wiki"], profile1)


def test_no_section2_input_of_another_type_raises() -> None:
    """Spec B8: the cited side gives UNAVAILABLE(BIB_PARSE_FAILED), the record side INSUFFICIENT fields."""
    assert B.describe(None, "en") == B.Unavailable(B.U_PARSE)
    assert B.describe(b"\xff{{cite journal |title=A}}", "en") == B.Unavailable(B.U_PARSE)
    assert B.describe(b"\xed\xa0\x80", "en") == B.Unavailable(B.U_PARSE)  # an encoded lone surrogate is not UTF-8
    described = B.describe(b"{{cite journal |title=A}}", "en")
    assert isinstance(described, B.CitedObject)
    for raw in (None, 5, "x", [], {"title": ["a"], "authors": {"x": 1}, "journal": 4, "original_year": 2.5}):
        assert B.compare(described, B.RecordObject.from_json(raw)).object == B.OBJ_INSUFFICIENT
    for raw in (None, 5, [], {"titles": "x", "authors": [3]}):
        assert B.compare(B.CitedObject.from_json(raw), B.RecordObject.from_json({"title": "A"})).object in (
            B.OBJ_INSUFFICIENT,
        )
    with pytest.raises(B.EnvironmentNotPinned):
        B.describe(b"{{cite journal |title=A}}", "fr")


def test_a_parser_exception_is_parse_failed_never_absence(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-086: any exception while parsing or cleaning makes the check UNAVAILABLE(BIB_PARSE_FAILED); c3854b8 read the
    same failure as C = ⊥ (no description) and the candidate reached D-14."""
    import mwparserfromhell

    def boom(_text: str) -> Any:
        raise RecursionError("nested too deeply")

    source = "{{cite journal |author=Robert Garry |title=X – Comments}}"
    monkeypatch.setattr(mwparserfromhell, "parse", boom)
    assert B.cited_object(source, "en") == B.Unavailable(B.U_PARSE)
    monkeypatch.undo()
    monkeypatch.setattr(B, "_clean", lambda _v: (_ for _ in ()).throw(ValueError("cleaning failed")))
    assert B.cited_object(source, "en") == B.Unavailable(B.U_PARSE)


def test_the_engine_refuses_without_the_c_tokenizer(monkeypatch: pytest.MonkeyPatch) -> None:
    import mwparserfromhell

    assert mwparserfromhell.parser.use_c
    monkeypatch.setattr(mwparserfromhell.parser, "use_c", False)
    with pytest.raises(B.EnvironmentNotPinned):
        B.cited_object("{{cite journal |title=X |last1=Y}}", "en")


# Detector level -------------------------------------------------------------------------------------------------------


class _With:
    """An abstract case whose unit result and deciding records are given (``step9_support.bib_inputs``)."""

    def __init__(self, case: Any, cited: dict[str, Any] | None, record: Any, reason: str | None = None) -> None:
        self._case = case
        self.bib_pair = (cited, record, reason)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._case, name)


def _matched_doi(bib: str = "NONE") -> Any:
    return R4.Case("CITED", "DOI", frozenset(), False, ("matched", "vf:retracted", False), None, None, bib=bib)


def _record_fields(raw: Any) -> dict[str, Any]:
    def typed(v: Any, t: type) -> Any:
        return v if isinstance(v, t) and not isinstance(v, bool) else None

    return {
        "title": typed(raw.get("title"), str),
        "authors": typed(raw.get("authors"), str),
        "journal": typed(raw.get("journal"), str),
        "original_year": typed(raw.get("original_year"), int),
    }


def _decide(case: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]], Any]:
    inp, _ = S9.concretize(case)
    out = dt1_detector(inp)
    assert len(out.claims) == 1
    claim, value_set = out.claims[0]
    return dict(claim), dict(value_set), {e["evidence_id"]: dict(e) for e in out.evidence}, inp


def _pair(case: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any], str | None]:
    cited = B.describe(_source(case), case["wiki"])
    fields = _record_fields(case["record"])
    if isinstance(cited, B.Unavailable):
        return None, fields, cited.reason
    return cited.to_json(), fields, None


DETECTOR_CASES = [c for c in CASES if c["record"] is not None]


@pytest.mark.parametrize("case", DETECTOR_CASES, ids=[c["id"] for c in DETECTOR_CASES])
def test_detector_decides_each_corpus_case(case: dict[str, Any]) -> None:
    cited, fields, reason = _pair(case)
    claim, value_set, evidence, inp = _decide(_With(_matched_doi(), cited, fields, reason))
    assert problems(claim, CLAIM) == []
    assert sets.evidence_set_problem(value_set) == "" and sets.claim_set_problem(claim, value_set) == ""
    for e in evidence.values():
        assert ref_problems(e, COMMON + "#/$defs/evidence") == []
    exp = case["expect"]
    rule = {"MATERIAL_CONFLICT": "D-13a", UNAVAILABLE: "D-13b", "NOT_ESTABLISHED": "D-13c"}.get(exp["object"], "D-14")
    general = {"D-13a": dt1.BIB_CONFLICT, "D-13b": dt1.BIB_UNAVAILABLE, "D-13c": dt1.BIB_NOT_ESTABLISHED}
    if rule == "D-14":
        assert (claim["rule"], claim["class"]) == ("D-14", "RETRACTED_WORK_CITED")
        assert not any(r.startswith("BIB") for r in claim["reasons"])
    else:
        assert (claim["rule"], claim["class"], claim["status"], claim["value"]) == (
            rule, "UNRESOLVED_IDENTITY", "uncertain", None,
        )  # fmt: skip
        assert set(claim["reasons"]) == {general[rule], *exp["reasons"]}
    unit = inp.candidate_inputs["units"][0]
    assert unit["evidence"]["cited_bibliography"] in value_set["supporting"]
    kinds = sorted(evidence[i]["kind"] for i in value_set["supporting"] if i in evidence)
    assert ("lookup_record" in kinds) == (rule != "D-13b")


def _garry_pair(cid: str) -> tuple[dict[str, Any] | None, dict[str, Any], str | None]:
    return _pair(next(c for c in CASES if c["id"] == cid))


@pytest.mark.parametrize(
    ("cid", "rule", "detail"),
    [
        ("garry-oversized-source", "D-13b", "BIB_SOURCE_LIMIT_EXCEEDED"),
        ("garry-oversized-description", "D-13b", "BIB_DESCRIPTION_LIMIT_EXCEEDED"),
        ("garry-too-many-values", "D-13b", "BIB_VALUE_LIMIT_EXCEEDED"),
        ("garry-unbalanced", "D-13b", "BIB_PARSE_FAILED"),
        ("garry-trailing-text", "D-13b", "BIB_PARSE_FAILED"),
        ("garry-not-utf8", "D-13b", "BIB_PARSE_FAILED"),
        ("garry-title-soft-hyphen", "D-13a", "BIB_TITLE_RELATED_OBJECT"),
        ("garry-title-zwsp", "D-13a", "BIB_TITLE_RELATED_OBJECT"),
        ("garry-title-word-joiner", "D-13a", "BIB_TITLE_RELATED_OBJECT"),
        ("commenter-shares-surname-remarks", "D-13c", "BIB_TITLE_EXTENDED"),
        ("garry-exact", "D-13a", "BIB_AUTHORS_DISJOINT"),
    ],
)
def test_fail_first_garry_variants_never_reach_d14(cid: str, rule: str, detail: str) -> None:
    """D-086 and D-087 fail-first: each of these reached D-14 under c3854b8 (``fail-first/`` logs), except garry-exact,
    which c3854b8 already refused. Under dt-4 none is positive."""
    claim, *_ = _decide(_With(_matched_doi(), *_garry_pair(cid)))
    assert (claim["rule"], claim["class"]) == (rule, "UNRESOLVED_IDENTITY")
    assert detail in claim["reasons"]


def test_the_true_original_stays_positive_and_a_genuine_citation_above_a_bound_abstains() -> None:
    claim, *_ = _decide(_With(_matched_doi(), *_garry_pair("garry-true-original")))
    assert (claim["rule"], claim["class"]) == ("D-14", "RETRACTED_WORK_CITED")
    claim, *_ = _decide(_With(_matched_doi(), *_garry_pair("genuine-at-source-bound")))
    assert claim["rule"] == "D-14"
    claim, *_ = _decide(_With(_matched_doi(), *_garry_pair("genuine-above-source-bound")))
    assert (claim["rule"], sorted(claim["reasons"])) == (
        "D-13b",
        ["BIBLIOGRAPHIC_CHECK_UNAVAILABLE", "BIB_SOURCE_LIMIT_EXCEEDED"],
    )


def test_natural_absence_is_not_a_failure() -> None:
    """A unit that is not a citation template (no description, no reason) and a template that describes nothing
    decide as dt-2 (D-14), with no bibliographic reason (spec P4)."""
    claim, *_ = _decide(_matched_doi("NONE"))
    assert claim["rule"] == "D-14" and not any(r.startswith("BIB") for r in claim["reasons"])
    claim, *_ = _decide(_With(_matched_doi(), *_garry_pair("empty-template-is-natural-absence")))
    assert claim["rule"] == "D-14" and not any(r.startswith("BIB") for r in claim["reasons"])


class _Bib:
    def __init__(self, bib: str) -> None:
        self.bib = bib


def _with_state(base: Any, bib: str) -> _With:
    cited, reason, record = S9.bib_inputs(_Bib(bib))
    return _With(base, cited, record, reason)


@pytest.mark.parametrize("bib", ["CONFLICT", "UNAVAILABLE", "NOT_ESTABLISHED"])
def test_no_bib_rule_overrides_an_earlier_rule(bib: str) -> None:
    """Spec B7: a role-collided, notice-only or unused candidate is decided exactly as with no description."""
    for base in (
        R4.Case("CITED", "DOI", frozenset(), False, ("matched", "vf:retracted", True), None, None, rc=True),
        R4.Case("CITED", "DOI", frozenset(), False, ("notice_only", "unc:notice", False), None, None),
        R4.Case("UNUSED", "DOI", frozenset(), False, ("matched", "vf:retracted", False), None, None),
        R4.Case("CITED", "DOI", frozenset({"IDENTIFIER_UNCONFIRMED"}), False, ("matched", "vf:retracted", False),
                None, None),
        R4.Case("CITED", "DOI", frozenset(), False, ("unavailable", "none", False), None, None),
    ):  # fmt: skip
        plain, *_ = _decide(base)
        with_bib, *_ = _decide(_with_state(base, bib))
        assert plain["rule"] != "D-14" and plain["rule"] == with_bib["rule"], base
        assert (plain["class"], sorted(plain["reasons"])) == (with_bib["class"], sorted(with_bib["reasons"]))


@pytest.mark.parametrize("bib", ["CONFLICT", "UNAVAILABLE", "NOT_ESTABLISHED"])
def test_each_bib_state_blocks_every_positive_value(bib: str) -> None:
    for value in ("retracted", "expression_of_concern", "correction", "reinstated"):
        base = R4.Case("CITED", "DOI", frozenset(), False, ("matched", f"vf:{value}", False), None, None)
        plain, *_ = _decide(base)
        blocked, *_ = _decide(_with_state(base, bib))
        assert plain["rule"] == "D-14"
        assert blocked["rule"] == {"CONFLICT": "D-13a", "UNAVAILABLE": "D-13b", "NOT_ESTABLISHED": "D-13c"}[bib]
        assert blocked["class"] == "UNRESOLVED_IDENTITY"


def _corrupt(mutate: Any) -> str:
    inp, _ = S9.concretize(_matched_doi("UNAVAILABLE"))
    mutate(inp.candidate_inputs["units"][0])
    with pytest.raises(DetectFailure) as exc:
        dt1_detector(inp)
    return exc.value.code


@pytest.mark.parametrize(
    "mutate",
    [
        lambda u: u.update(bibliography=dict(S9.BC_CITED)),  # a description and a reason
        lambda u: u["evidence"].pop("cited_bibliography"),  # a reason without its evidence
        lambda u: u.update(bibliography_unavailable="BIB_TIMEOUT"),  # a reason outside bib-2
        lambda u: u.update(bibliography_unavailable=None),  # evidence without a result (read as absence before)
        lambda u: u.update(bibliography_unavailable=None, bibliography={"titles": ["A"]}),  # not a bib-2 description
        lambda u: u.update(bibliography_unavailable=None, bibliography=["A"]),
    ],
    ids=["both", "no-evidence", "unknown-reason", "evidence-only", "bib1-shape", "not-a-mapping"],
)
def test_an_inconsistent_unit_result_fails_closed(mutate: Any) -> None:
    """D-086: DETECT never reads an inconsistent committed bibliographic result as natural absence."""
    assert _corrupt(mutate) == dt1.ADAPTER_INCONSISTENT


def test_a_record_bound_to_another_event_fails_closed() -> None:
    inp, _ = S9.concretize(_matched_doi("CONFLICT"))
    for lookup in inp.lookup_plan["lookups"]:
        obs = inp.read_blob(lookup["observation"])
        obs["records"][0]["event_id"] = "ev-another"
    with pytest.raises(DetectFailure) as exc:
        dt1_detector(inp)
    assert exc.value.code == "ADAPTER_INCONSISTENT"


@pytest.mark.parametrize("field", ["title", "journal"])
def test_a_record_contradicting_its_public_event_fails_closed(field: str) -> None:
    inp, _ = S9.concretize(_matched_doi("CONFLICT"))
    assert dict(dt1_detector(inp).claims[0][0])["rule"] == "D-13a"
    for lookup in inp.lookup_plan["lookups"]:
        obs = inp.read_blob(lookup["observation"])
        obs["records"][0][field] = "Totally different words here"
    with pytest.raises(DetectFailure) as exc:
        dt1_detector(inp)
    assert exc.value.code == "ADAPTER_INCONSISTENT"


# NORMALIZE ------------------------------------------------------------------------------------------------------------


def _source_artifact(data: bytes) -> Any:
    from citerift.investigation.anchors import SourceArtifact
    from citerift.investigation.canonical import sha256_hex

    return SourceArtifact(data, sha256_hex(data))


def _unit(start: int, end: int, kind: str = "citation_template") -> dict[str, Any]:
    return {"kind": kind, "source": {"byte_start": start, "byte_end": end}}


def test_normalize_describes_or_says_why_not() -> None:
    from citerift.investigation.adapters.normalize import cited_description

    garry = next(c for c in CASES if c["id"] == "garry-oversized-source")["source"].encode("utf-8")
    good = b"{{cite journal |title=Thermal drift |last1=Lindqvist}}"
    data = garry + b"\n" + good + b"\n" + "\u00e9".encode("utf-8")
    src = _source_artifact(data)
    a, b = len(garry), len(garry) + 1 + len(good)
    assert cited_description(_unit(0, a), src, "en") == B.Unavailable(B.U_SOURCE)
    kept = cited_description(_unit(a + 1, b), src, "en")
    assert isinstance(kept, B.CitedObject) and kept.titles == ("Thermal drift",)
    # a span that cuts a character in two does not decode
    assert cited_description(_unit(b + 1, len(data) - 1), src, "en") == B.Unavailable(B.U_PARSE)
    assert cited_description(_unit(0, a, "free_text"), src, "en") is None  # ABSENT: natural absence
    assert cited_description({"kind": "citation_template", "source": {}}, src, "en") == B.Unavailable(B.U_PARSE)
    assert cited_description(_unit(5, len(data) + 9), src, "en") == B.Unavailable(B.U_PARSE)


@pytest.mark.parametrize("entity", ["&#xD800;", "&#xDFFF;", "&#55296;"])
def test_normalize_replaces_a_surrogate_and_keeps_the_value(entity: str) -> None:
    """Reviewer findings E-01, F-02 and C-01 (kept from bib-1): a lone surrogate becomes U+FFFD and the value keeps its
    words; the evidence is canonical."""
    from citerift.investigation.adapters.normalize import cited_description
    from citerift.investigation.canonical import canon

    bad = "{{cite journal |title=Retraction of X" + entity + " |last1=Hon}}"
    data = bad.encode("utf-8")
    partial = cited_description(_unit(0, len(data)), _source_artifact(data), "en")
    assert isinstance(partial, B.CitedObject)
    assert partial.titles == ("Retraction of X�",) and partial.authors == ("Hon",)
    canon(partial.to_json())


# Identity and texts ---------------------------------------------------------------------------------------------------


def test_the_engine_identity_is_new() -> None:
    """D-087: a new table identity and a new engine identity, distinct from dt-1/0.2.0, dt-2/0.3.0 and dt-3/0.4.0."""
    import hashlib

    import citerift.investigation as ci
    from citerift.investigation.adapters.detector import DETECTOR_IDENTITY
    from citerift.investigation.adapters.plan import INTEGRATION_SCHEMAS, STAGE04_IDENTITY

    raw = (REPO / "src" / "citerift" / "investigation" / "data" / "bib-profile-2.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == B.PROFILE_SHA256
    assert json.loads(raw)["profile_version"] == "bib-profile-2"
    assert (ci.__version__, dt1.TABLE_VERSION, B.BIB_VERSION, B.PARSER_VERSION) == ("0.5.0", "dt-4", "bib-2", "0.7.2")
    assert (STAGE04_IDENTITY["engine_version"], STAGE04_IDENTITY["schema_version"]) == ("0.5.0", "6.0.0")
    assert INTEGRATION_SCHEMAS["candidate-inputs"] == "3.0.0"
    assert DETECTOR_IDENTITY == "citerift-dt1-detector/5 (dt-4)"
    assert R4.TABLE_VERSION == dt1.TABLE_VERSION
    assert [r for r, _ in dt1.RULES][13:17] == ["D-13a", "D-13b", "D-13c", "D-14"]


def test_every_new_reason_has_an_explanation_and_a_schema_entry() -> None:
    schema = json.loads((REPO / "schemas" / "investigation" / "v1" / "common.schema.json").read_text(encoding="utf-8"))
    enum = set(schema["$defs"]["reason"]["enum"])
    new = {dt1.BIB_UNAVAILABLE, dt1.BIB_NOT_ESTABLISHED, *B.UNAVAILABLE_REASONS, *B.NOT_ESTABLISHED_REASONS}
    assert new <= enum and new <= set(REASON_TEXT)
    assert set(schema["$defs"]["bib_unavailable_reason"]["enum"]) == set(B.UNAVAILABLE_REASONS)
