"""Final corrective cycle (owner decision D-083): the bibliographic-object consistency layer bib-1 and rule D-13a.

- The adversarial corpus (``docs/verification/stage-04/final-cycle/corpus/BIB_CORPUS.json``, written from the
  specification before the production comparison was checked against it) gives, through the production code and through
  the independent reference model (``simulations/stage04/bib_reference.py``, written from the specification alone),
  exactly the expected verdict fields of every case.
- Production and reference agree on the whole output over seeded generated templates and records (differential).
- Through the production detector on concrete inputs: a matched retracted-work candidate whose deciding records are in
  MATERIAL_CONFLICT with its own description abstains by D-13a, every other corpus case keeps dt-2's D-14; D-13a never
  overrides an earlier rule (role collision, notice only); the claim validates and is supported by the description and
  the records it was decided on.
"""

from __future__ import annotations

import ast
import json
import random
import sys
from pathlib import Path
from typing import Any

import pytest
import step9_support as S9

from citerift.investigation import bibliographic as B
from citerift.investigation import sets
from citerift.investigation.adapters.detector import dt1_detector
from citerift.investigation.schemas import CLAIM, COMMON, problems, ref_problems

REPO = Path(__file__).resolve().parents[2]
SIM = REPO / "simulations" / "stage04"
CORPUS = REPO / "docs" / "verification" / "stage-04" / "final-cycle" / "corpus" / "BIB_CORPUS.json"
sys.path.insert(0, str(SIM))

import bib_reference as BR  # noqa: E402
import dt3_reference as R3  # noqa: E402

pytestmark = pytest.mark.unit

CASES: list[dict[str, Any]] = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]
PROFILE = BR.load_profile(SIM / "bib-reference-profile.json")


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
    prod = B.profile()
    assert prod["profile_version"] == "bib-profile-1"
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


def test_production_equals_the_reference_on_generated_cases() -> None:
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


# Detector level -------------------------------------------------------------------------------------------------------


class _WithBib:
    """An abstract case whose unit description and deciding records are a corpus case's (``step9_support.bib``)."""

    def __init__(self, case: Any, cited: dict[str, Any] | None, record: dict[str, Any]) -> None:
        self._case = case
        self.bib = (cited, record)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._case, name)


def _matched_doi() -> Any:
    return R3.Case("CITED", "DOI", frozenset(), False, ("matched", "vf:retracted", False), None, None)


def _record_fields(raw: Any) -> dict[str, Any]:
    """The corpus record as LOOKUP records it (schema types; a mistyped field is not representable there: null)."""

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


DETECTOR_CASES = [c for c in CASES if c["record"] is not None]


@pytest.mark.parametrize("case", DETECTOR_CASES, ids=[c["id"] for c in DETECTOR_CASES])
def test_detector_decides_each_corpus_case(case: dict[str, Any]) -> None:
    cited = B.cited_object(case["source"], case["wiki"])
    fields = _record_fields(case["record"])
    verdict = B.compare(cited, B.RecordObject.from_json(fields))
    claim, value_set, evidence, inp = _decide(_WithBib(_matched_doi(), cited.to_json() if cited else None, fields))
    assert problems(claim, CLAIM) == []
    assert sets.evidence_set_problem(value_set) == "" and sets.claim_set_problem(claim, value_set) == ""
    for e in evidence.values():
        assert ref_problems(e, COMMON + "#/$defs/evidence") == []
    if verdict.object == B.MATERIAL_CONFLICT:
        assert (claim["rule"], claim["class"], claim["status"], claim["value"]) == (
            "D-13a", "UNRESOLVED_IDENTITY", "uncertain", None,
        )  # fmt: skip
        assert set(claim["reasons"]) == {"BIBLIOGRAPHIC_OBJECT_CONFLICT", *verdict.reasons}
    else:
        assert (claim["rule"], claim["class"]) == ("D-14", "RETRACTED_WORK_CITED")
        assert not any(r.startswith("BIB") for r in claim["reasons"])
    kinds = sorted(evidence[i]["kind"] for i in value_set["supporting"] if i in evidence)
    assert "lookup_record" in kinds
    unit = inp.candidate_inputs["units"][0]
    if cited is not None:
        assert unit["evidence"]["cited_bibliography"] in value_set["supporting"]


def _garry() -> tuple[dict[str, Any] | None, dict[str, Any]]:
    case = next(c for c in CASES if c["id"] == "garry-exact")
    cited = B.cited_object(case["source"], case["wiki"])
    assert cited is not None
    return cited.to_json(), _record_fields(case["record"])


def test_garry_abstains_and_its_true_original_stays_positive() -> None:
    claim, *_ = _decide(_WithBib(_matched_doi(), *_garry()))
    assert claim["rule"] == "D-13a" and claim["class"] == "UNRESOLVED_IDENTITY"
    want = {"BIBLIOGRAPHIC_OBJECT_CONFLICT", "BIB_AUTHORS_DISJOINT", "BIB_TITLE_RELATED_OBJECT"}
    assert set(claim["reasons"]) == want
    true = next(c for c in CASES if c["id"] == "garry-true-original")
    cited = B.cited_object(true["source"], true["wiki"])
    assert cited is not None
    claim, *_ = _decide(_WithBib(_matched_doi(), cited.to_json(), _record_fields(true["record"])))
    assert (claim["rule"], claim["class"]) == ("D-14", "RETRACTED_WORK_CITED")


def test_d13a_never_overrides_an_earlier_rule() -> None:
    """Spec B7: a role-collided or notice-only candidate is decided exactly as without the conflicting description."""
    cited, record = _garry()
    for base in (
        R3.Case("CITED", "DOI", frozenset(), False, ("matched", "vf:retracted", True), None, None, rc=True),
        R3.Case("CITED", "DOI", frozenset(), False, ("notice_only", "unc:notice", False), None, None),
        R3.Case("UNUSED", "DOI", frozenset(), False, ("matched", "vf:retracted", False), None, None),
    ):
        plain, *_ = _decide(base)
        with_bib, *_ = _decide(_WithBib(base, cited, record))
        assert plain["rule"] != "D-14" and plain["rule"] == with_bib["rule"], base
        assert (plain["class"], sorted(plain["reasons"])) == (with_bib["class"], sorted(with_bib["reasons"]))


def test_a_record_bound_to_another_event_fails_closed() -> None:
    """The records must name the observation's events, in order, with their row hashes (else ADAPTER_INCONSISTENT)."""
    from citerift.investigation.adapters.detect import DetectFailure

    inp, _ = S9.concretize(_WithBib(_matched_doi(), *_garry()))
    for lookup in inp.lookup_plan["lookups"]:
        obs = inp.read_blob(lookup["observation"])
        obs["records"][0]["event_id"] = "ev-another"
    with pytest.raises(DetectFailure) as exc:
        dt1_detector(inp)
    assert exc.value.code == "ADAPTER_INCONSISTENT"


@pytest.mark.parametrize("field", ["title", "journal"])
def test_a_record_contradicting_its_public_event_fails_closed(field: str) -> None:
    """Reviewer finding B-06: a record whose title or journal differs from its own public event's is refused
    (ADAPTER_INCONSISTENT); before the fix a changed record title changed the decision to D-13a."""
    from citerift.investigation.adapters.detect import DetectFailure

    inp, _ = S9.concretize(_WithBib(_matched_doi(), *_garry()))
    claim = dict(dt1_detector(inp).claims[0][0])
    assert claim["rule"] == "D-13a"
    for lookup in inp.lookup_plan["lookups"]:
        obs = inp.read_blob(lookup["observation"])
        obs["records"][0][field] = "Totally different words here"
    with pytest.raises(DetectFailure) as exc:
        dt1_detector(inp)
    assert exc.value.code == "ADAPTER_INCONSISTENT"


@pytest.mark.parametrize("entity", ["&#xD800;", "&#xDFFF;", "&#55296;"])
def test_normalize_replaces_a_surrogate_and_keeps_the_value(entity: str) -> None:
    """Reviewer findings E-01, F-02 and C-01: a numeric entity that decodes to a lone surrogate made the unit's
    cited_bibliography evidence uncanonicalizable, and the whole NORMALIZE step failed; then the value was dropped,
    which could remove a conflicting author. Now the surrogate becomes U+FFFD (spec 2.1 step 4): the value keeps its
    words, the evidence is canonical, and every other unit of the page keeps its own description."""
    from citerift.investigation.adapters.normalize import cited_description
    from citerift.investigation.anchors import SourceArtifact
    from citerift.investigation.canonical import canon, sha256_hex

    bad = "{{cite journal |title=Retraction of X" + entity + " |last1=Hon}}"
    good = "{{cite journal |title=Thermal drift |last1=Lindqvist}}"
    data = (bad + "\n" + good).encode("utf-8")
    source = SourceArtifact(data, sha256_hex(data))
    split = len(bad.encode("utf-8"))

    def unit(start: int, end: int) -> dict[str, Any]:
        return {"kind": "citation_template", "source": {"byte_start": start, "byte_end": end}}

    partial = cited_description(unit(0, split), source, "en")
    assert partial is not None and partial["titles"] == ["Retraction of X\ufffd"] and partial["authors"] == ["Hon"]
    kept = cited_description(unit(split + 1, len(data)), source, "en")
    assert kept is not None and kept["titles"] == ["Thermal drift"]
    canon({"bad": partial, "good": kept})


def test_the_engine_refuses_without_the_c_tokenizer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reviewer finding E-11: the pure-Python tokenizer can parse differently; bib-1 refuses to describe a unit without
    the C tokenizer (and NORMALIZE fails closed) instead of giving another description."""
    import mwparserfromhell

    assert mwparserfromhell.parser.use_c
    monkeypatch.setattr(mwparserfromhell.parser, "use_c", False)
    with pytest.raises(B.EnvironmentNotPinned):
        B.cited_object("{{cite journal |title=X |last1=Y}}", "en")


def test_both_profiles_name_the_same_module_revisions() -> None:
    """Reviewer finding D-11: both alias profiles record the CS1 configuration revision they were extracted from and
    its content SHA-256 (the raw module texts are not committed; any copy of those revisions can be checked)."""
    prod = B.profile()["wikis"]
    for wiki in ("ar", "en"):
        ref = PROFILE["wikis"][wiki]
        assert (ref["revid"], ref["content_sha256"]) == (
            prod[wiki]["source"]["revid"],
            prod[wiki]["source"]["content_sha256"],
        )


def test_a04_bridged_events_alone_never_give_a_positive(tmp_path: Path) -> None:
    """Reviewer finding B-03 (the A-04 shape at detector level, on a real Stage 02 index): the cited PMID's only
    direct event is a correction; a retraction reaches the lookup only through the DOI the two records share
    (co-occurrence bridging; a DOI query is not bridged through a PMID). dt-3 must not decide RETRACTED_WORK_CITED
    (Stage 02 rule 7f does not count bridged records toward a verified value)."""
    sys.path.insert(0, str(REPO / "tests" / "stage02"))
    import rde_support as RS

    from citerift.investigation import dt1
    from citerift.investigation.adapters.detector import lookup_view
    from citerift.investigation.adapters.lookup import observe
    from citerift.investigation.lookup import DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES
    from citerift.retraction.query import Index

    rows = [
        RS.row(**{"Record ID": "1", "RetractionNature": "Correction", "OriginalPaperDOI": "10.5555/a",
                  "OriginalPaperPubMedID": "8"}),
        RS.row(**{"Record ID": "2", "RetractionNature": "Retraction", "OriginalPaperDOI": "10.5555/a",
                  "OriginalPaperPubMedID": "7"}),
    ]  # fmt: skip
    with Index(RS.build_rows(tmp_path, rows)) as index:
        lk = lookup_view(observe(index, {}, None, "8", DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES))
    assert any(e.event_type == "retracted" and e.linked_via is not None for e in lk.events), lk.events
    assert all(e.event_type != "retracted" for e in lk.events if e.linked_via is None)
    out = dt1.decide(dt1.Candidate("CITED", None, "PMID", None, "8", (), False, ((dt1.Q1_PMID, lk),), None))
    assert out.cls != "RETRACTED_WORK_CITED", out
    assert out.rule != "D-14" or out.cls == "CORRECTION_CITED", out


def test_the_profile_and_parser_pins_belong_to_engine_0_4_0() -> None:
    """Reviewer finding D-02: a profile or parser change is a code change and needs a new engine version; this test
    pins the three together, so changing one without the others fails here."""
    import hashlib

    import citerift.investigation as ci

    raw = (REPO / "src" / "citerift" / "investigation" / "data" / "bib-profile-1.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == B.PROFILE_SHA256
    assert (ci.__version__, B.PROFILE_SHA256, B.PARSER_VERSION) == (
        "0.4.0",
        "450f17a2ec492f9066825e0ec9de3f2f480398345d4593759bfb9ace45e9808f",
        "0.7.2",
    )
