"""Local open-model adapter (AI Protocol v2; SPECIFICATION.md 12.4). The scorer here is a test double: the
real downloaded model is exercised by separate, pinned evidence runs (docs/verification/stage-02/ai/v2),
never by the collected test suite, so these tests need neither torch nor the weights."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import pytest
import rde_support as S

from citerift.retraction import advisory, ambiguity, cli, local_model
from citerift.retraction.local_model import Budget, LocalAmbiguityModel, ModelUnavailable
from citerift.retraction.query import Index, lookup

MANIFEST: dict[str, Any] = {
    "format": local_model.MANIFEST_FORMAT,
    "model_id": "test/double",
    "source": {"repository": "test/double", "revision": "0" * 40},
    "license": {"spdx": "Apache-2.0"},
    "files": {"model.safetensors": {"size": 4, "sha256": hashlib.sha256(b"abcd").hexdigest()}},
    "architecture": "DoubleForCausalLM",
    "runtime": {"torch": "0", "transformers": "0", "threads": 4, "dtype": "float32"},
    "template": {
        "prefix": "<p>",
        "body": "{instruction}|Q:{query}|D:{document}",
        "suffix": "<s>",
        "instruction": "same work?",
        "true_token": "yes",
        "true_token_id": 1,
        "false_token": "no",
        "false_token_id": 0,
    },
    "encoding": {"author_limits": [20, 3, 1]},
    "wrapper": {"tau_s": 2.0, "tau_m": 1.0},
}


class Double:
    """Scores a pair by a lookup on the candidate's title; counts characters as tokens."""

    def __init__(self, scores: dict[str, float]):
        self.scores = scores
        self.seen: list[str] = []

    def count(self, text: str) -> int:
        return len(text)

    def score(self, text: str) -> float:
        self.seen.append(text)
        title = text.split("|D:Title: ", 1)[1].split("\n", 1)[0]
        return self.scores[title]


def model(scores: dict[str, float], calls: list[int] | None = None, **kwargs: Any) -> LocalAmbiguityModel:
    calls = calls if calls is not None else []

    def loader(_dir: Path, _manifest: dict[str, Any]) -> Double:
        calls.append(1)
        return Double(scores)

    return LocalAmbiguityModel(Path("unused"), loader=loader, **kwargs)


def bundle(*titles: str, query_title: str = "Effects of X on Y") -> dict[str, Any]:
    return advisory.make_bundle(
        {"title": query_title, "authors": "A Tester;B Other", "journal": "J", "original_year": 2010},
        [{"title": t, "authors": "A Tester", "journal": "J", "original_year": 2010} for t in titles],
    )


@pytest.mark.unit
def test_rde_local_model_selects_only_above_threshold_and_margin() -> None:
    m = model({"same": 5.0, "other": 1.0, "close": 4.5})
    a = m.rank(bundle("other", "same"), MANIFEST)
    assert (a.decision, a.candidate_id) == ("select", "c2")
    assert [c for c, _ in a.ranked] == ["c2", "c1"]
    assert a.usage["pairs"] == 2 and a.usage["tokens"] > 0
    assert "/candidates/1/title" in a.evidence_pointers and a.to_json()["advisory"] is True
    assert a.score_type.startswith("reranker yes/no logit difference")
    near = m.rank(bundle("same", "close"), MANIFEST)  # margin 0.5 < tau_m
    assert (near.decision, near.reason_codes) == ("abstain", ("BELOW_THRESHOLD_OR_MARGIN",))
    low = model({"weak": 1.5}).rank(bundle("weak"), MANIFEST)  # single candidate below tau_s
    assert low.decision == "abstain"
    single = model({"same": 2.0}).rank(bundle("same"), MANIFEST)  # inclusive threshold, no second candidate
    assert single.decision == "select"


@pytest.mark.unit
def test_rde_local_model_wrapper_ties_and_order() -> None:
    w = {"tau_s": 0.0, "tau_m": 0.0}
    assert local_model.decide([], w) == ("abstain", None)
    assert local_model.decide([("c2", 1.0), ("c1", 1.0)], w) == ("select", "c1")
    assert local_model.decide([("c1", 1.0), ("c2", 1.0)], {"tau_s": 0.0, "tau_m": 0.1}) == ("abstain", None)


@pytest.mark.unit
def test_rde_local_model_loads_once_and_lazily() -> None:
    calls: list[int] = []
    m = model({"same": 5.0}, calls)
    assert calls == []  # nothing is loaded before an explicit call
    m.rank({"query": {}, "candidates": "x"}, MANIFEST)
    assert calls == []  # an invalid bundle never loads the model
    m.rank(bundle("same"), MANIFEST)
    m.rank(bundle("same"), MANIFEST)
    assert calls == [1]
    m.rank(bundle("same"), {**MANIFEST, "wrapper": {"tau_s": 9.0, "tau_m": 0.0}})
    assert calls == [1, 1]  # another manifest is another artifact: loaded again, never mixed


@pytest.mark.negative
@pytest.mark.parametrize(
    ("bad", "fragment"),
    [
        ({"query": {"title": "t"}}, "exactly the keys"),
        ({"query": {"title": "t"}, "candidates": [{"candidate_id": "c9", "title": "x"}]}, "distinct c1..c5"),
        ({"query": {"title": "t"}, "candidates": [{"candidate_id": "c1"}, {"candidate_id": "c1"}]}, "distinct"),
        ({"query": {"title": "t"}, "candidates": [{"candidate_id": f"c{i}"} for i in range(1, 7)]}, "at most 5"),
        ({"query": {"title": "t", "doi": "10.1/x"}, "candidates": []}, "unexpected fields"),
        ({"query": {"title": "t", "original_year": "2010"}, "candidates": []}, "not an integer"),
        ({"query": {"title": "t", "original_year": True}, "candidates": []}, "not an integer"),
        ({"query": {"title": 5}, "candidates": []}, "not text"),
        ({"query": {"title": " "}, "candidates": []}, "no title"),
        ("not a bundle", "exactly the keys"),
    ],
)
def test_rde_local_model_invalid_bundles_abstain(bad: Any, fragment: str) -> None:
    a = model({}).rank(bad, MANIFEST)
    assert (a.decision, a.reason_codes) == ("abstain", ("INVALID_BUNDLE",))
    assert any(fragment in p for p in a.problems), a.problems


@pytest.mark.negative
def test_rde_local_model_no_candidates_abstains_without_loading() -> None:
    calls: list[int] = []
    a = model({}, calls).rank(bundle(), MANIFEST)
    assert (a.decision, a.reason_codes, calls) == ("abstain", ("NO_CANDIDATES",), [])


@pytest.mark.security
def test_rde_local_model_missing_or_corrupt_weights_abstain_as_unavailable(tmp_path: Path) -> None:
    missing = LocalAmbiguityModel(tmp_path / "absent").rank(bundle("same"), MANIFEST)
    assert (missing.decision, missing.reason_codes) == ("abstain", ("MODEL_UNAVAILABLE",))
    (tmp_path / "m").mkdir()
    (tmp_path / "m" / "model.safetensors").write_bytes(b"abce")  # same size, other bytes
    corrupt = LocalAmbiguityModel(tmp_path / "m").rank(bundle("same"), MANIFEST)
    assert (corrupt.decision, corrupt.reason_codes) == ("abstain", ("MODEL_ARTIFACT_MISMATCH",))
    (tmp_path / "m" / "model.safetensors").write_bytes(b"abcdef")
    resized = LocalAmbiguityModel(tmp_path / "m").rank(bundle("same"), MANIFEST)
    assert resized.reason_codes == ("MODEL_ARTIFACT_MISMATCH",)
    # Never a negative finding: an unavailable model is an abstention, with no ranking and no pointers.
    for a in (missing, corrupt, resized):
        assert a.candidate_id is None and a.ranked == () and a.evidence_pointers == ()


@pytest.mark.security
def test_rde_local_model_runtime_failures_abstain() -> None:
    def no_runtime(_d: Path, _m: dict[str, Any]) -> Any:
        raise ModelUnavailable("RUNTIME_UNAVAILABLE", "optional inference stack not installed")

    def broken(_d: Path, _m: dict[str, Any]) -> Any:
        raise OSError("disk")

    for loader, code in ((no_runtime, "RUNTIME_UNAVAILABLE"), (broken, "MODEL_UNAVAILABLE")):
        a = LocalAmbiguityModel(Path("x"), loader=loader).rank(bundle("same"), MANIFEST)
        assert (a.decision, a.reason_codes) == ("abstain", (code,))

    class Raising(Double):
        def score(self, text: str) -> float:
            raise RuntimeError("out of memory")

    a = LocalAmbiguityModel(Path("x"), loader=lambda _d, _m: Raising({})).rank(bundle("same"), MANIFEST)
    assert a.reason_codes == ("RUNTIME_ERROR",)


@pytest.mark.security
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_rde_local_model_nonfinite_scores_abstain(value: float) -> None:
    a = model({"same": 5.0, "odd": value}).rank(bundle("same", "odd"), MANIFEST)
    assert (a.decision, a.reason_codes, a.ranked) == ("abstain", ("NONFINITE_SCORE",), ())


@pytest.mark.security
def test_rde_local_model_deadline_abstains() -> None:
    # rank start, load start and end, scoring start, first pair check; the second pair check is past the deadline
    ticks = iter([0.0, 0.0, 0.0, 0.0, 0.0, 40.0, 40.0, 40.0])
    m = model({"same": 5.0, "other": 1.0}, clock=lambda: next(ticks))
    a = m.rank(bundle("same", "other"), MANIFEST, Budget(deadline_s=30.0))
    assert (a.decision, a.reason_codes) == ("abstain", ("TIMEOUT",))
    assert a.usage["pairs"] == 1


@pytest.mark.negative
def test_rde_local_model_long_author_lists_are_shortened_and_long_titles_abstain() -> None:
    authors = ";".join(f"Author{i} Name" for i in range(60))
    b = advisory.make_bundle(
        {"title": "Effects of X on Y", "authors": authors, "journal": "J", "original_year": 2010},
        [{"title": "same", "authors": authors, "journal": "J", "original_year": 2010}],
    )
    a = model({"same": 5.0}).rank(b, MANIFEST, Budget(max_pair_tokens=400))
    assert a.decision == "select" and "AUTHORS_SHORTENED" in a.reason_codes
    long = bundle("same", query_title="T" * 600)
    a2 = model({"same": 5.0}).rank(long, MANIFEST, Budget(max_pair_tokens=512))
    assert (a2.decision, a2.reason_codes) == ("abstain", ("INPUT_TOO_LONG",))


@pytest.mark.unit
def test_rde_local_model_rendering_is_field_aware_and_unicode_safe() -> None:
    text, cut = local_model.render_record(
        {"title": "تأثير\u200f X\x00 على Y", "authors": "أحمد علي;B", "journal": None, "original_year": None}, 1
    )
    assert cut is True
    assert text.splitlines() == [
        "Title: تأثير\u200f X  على Y".replace("\u200f", " "),
        "Authors: أحمد علي (and 1 more)",
        "Journal: unknown",
        "Year: unknown",
    ]
    decomposed = local_model.render_record({"title": "Café"}, 3)[0]
    assert decomposed.splitlines()[0] == "Title: Café"  # NFC
    arabic = advisory.make_bundle(
        {"title": "دراسة", "authors": "", "journal": "", "original_year": 2020},
        [{"title": "دراسة", "authors": "", "journal": "", "original_year": 2020}],
    )
    a = model({"دراسة": 5.0}).rank(arabic, MANIFEST)
    assert a.decision == "select" and len(a.input_sha256) == 64


@pytest.mark.unit
def test_rde_local_model_input_hash_and_manifest_reference_are_recorded() -> None:
    b = bundle("same")
    a = model({"same": 5.0}).rank(b, MANIFEST)
    assert a.input_sha256 == hashlib.sha256(local_model.canonical(b).encode()).hexdigest()
    assert a.model == {
        "model_id": "test/double",
        "revision": "0" * 40,
        "manifest_sha256": local_model.manifest_sha256(MANIFEST),
    }


@pytest.mark.unit
def test_rde_local_model_manifest_loading(tmp_path: Path) -> None:
    p = tmp_path / "m.json"
    p.write_text(json.dumps(MANIFEST), encoding="utf-8")
    assert local_model.load_manifest(p) == MANIFEST
    p.write_text(json.dumps({**MANIFEST, "format": "other"}), encoding="utf-8")
    with pytest.raises(ModelUnavailable, match="MANIFEST_INVALID"):
        local_model.load_manifest(p)
    shipped = S.REPO / "src" / "citerift" / "retraction" / "model_manifests"
    for path in sorted(shipped.glob("*.json")):
        m = local_model.load_manifest(path)
        assert m["source"]["revision"] and all(len(f["sha256"]) == 64 for f in m["files"].values())


@pytest.mark.security
def test_rde_local_model_import_does_not_load_an_inference_stack() -> None:
    code = (
        "import sys, citerift.retraction.local_model, citerift.retraction.cli, citerift.retraction.query;"
        "print(sorted(m for m in ('torch', 'transformers', 'huggingface_hub') if m in sys.modules))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"


@pytest.mark.security
def test_rde_ai_on_ai_off_factual_invariance(tmp_path: Path) -> None:
    """The same index gives the same facts whether the advisory model selects, abstains or fails."""
    common = {"RetractionNature": "Retraction", "Title": "Quantum widget stability in cold rats", "Author": "Ann Smith"}
    rows = [
        S.row(**{"Record ID": "1", "OriginalPaperDOI": "10.5555/t", **common}),
        S.row(**{"Record ID": "2", **common}),
    ]
    idx = S.build_rows(tmp_path, rows)
    digest = hashlib.sha256(idx.read_bytes()).hexdigest()
    facts_off = json.dumps(lookup(idx, "10.5555/t"), sort_keys=True)
    with Index(idx) as ix:
        probe = ambiguity.probe_for_event(ix, "ev-0000002")
        cands = ambiguity.Baseline(ix).candidates(probe)
        fields = [
            dict(
                zip(
                    advisory.BUNDLE_FIELDS,
                    ix.conn.execute(
                        "SELECT title, authors, journal, original_year FROM event WHERE event_id = ?", (c.event_id,)
                    ).fetchone(),
                    strict=True,
                )
            )
            for c in cands
        ]
    b = advisory.make_bundle(
        {"title": probe.title, "authors": probe.authors, "journal": None, "original_year": probe.original_year}, fields
    )
    outcomes = [
        model({"Quantum widget stability in cold rats": 9.0}).rank(b, MANIFEST).decision,
        model({"Quantum widget stability in cold rats": -9.0}).rank(b, MANIFEST).decision,
        LocalAmbiguityModel(tmp_path / "no-weights").rank(b, MANIFEST).decision,
    ]
    assert outcomes == ["select", "abstain", "abstain"]
    assert hashlib.sha256(idx.read_bytes()).hexdigest() == digest
    assert json.dumps(lookup(idx, "10.5555/t"), sort_keys=True) == facts_off
    with Index(idx) as ix:
        assert ix.event_by_id("ev-0000002")["original_doi"] is None  # the suggestion links nothing


@pytest.mark.security
def test_rde_local_model_bundle_shape_matches_the_advisory_boundary() -> None:
    """local_model.py repeats the bundle constants instead of importing the advisory boundary module."""
    assert local_model.BUNDLE_FIELDS == advisory.BUNDLE_FIELDS
    assert local_model.MAX_CANDIDATES == advisory.MAX_CANDIDATES


@pytest.mark.integration
def test_rde_cli_ambiguity_with_missing_weights_abstains_and_keeps_the_baseline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``ambiguity --model-dir`` adds an advisory model result; missing weights abstain, never a finding."""
    common = {"RetractionNature": "Retraction", "Title": "Quantum widget stability in cold rats", "Author": "Ann Smith"}
    idx = S.build_rows(
        tmp_path,
        [S.row(**{"Record ID": "1", "OriginalPaperDOI": "10.5555/t", **common}), S.row(**{"Record ID": "2", **common})],
    )
    assert cli.main(["ambiguity", "--index", str(idx), "--event", "ev-0000002"]) == 0
    plain = json.loads(capsys.readouterr().out)
    empty = tmp_path / "no-weights"
    empty.mkdir()
    assert cli.main(["ambiguity", "--index", str(idx), "--event", "ev-0000002", "--model-dir", str(empty)]) == 0
    out = json.loads(capsys.readouterr().out)
    model = out.pop("model_assessment")
    assert out == plain
    assert model["decision"] == "abstain" and model["reason_codes"] == ["MODEL_UNAVAILABLE"] and model["advisory"]
    assert model["model"]["model_id"] == "mixedbread-ai/mxbai-rerank-base-v2"
    with Index(idx) as ix:
        cands = ambiguity.Baseline(ix).candidates(ambiguity.probe_for_event(ix, "ev-0000002"))
        assert ambiguity.model_bundle(ix, "ev-0000002", cands)["query"]["title"] == common["Title"]
    assert cli.main(["ambiguity", "--index", str(idx), "--event", "ev-0000001", "--model-dir", str(empty)]) == 0
    assert "model_assessment" not in json.loads(capsys.readouterr().out)  # an exact identifier needs no model


@pytest.mark.security
def test_rde_local_model_real_scorer_checks_runtime_and_architecture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real backend refuses a missing or unpinned runtime and a model of another architecture."""
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "0")
    (tmp_path / "config.json").write_text(json.dumps({"architectures": ["OtherForCausalLM"]}), encoding="utf-8")
    monkeypatch.setitem(sys.modules, "torch", None)  # import fails as if not installed
    with pytest.raises(ModelUnavailable) as no_stack:
        local_model.TransformersYesNoScorer(tmp_path, MANIFEST)
    assert no_stack.value.code == "RUNTIME_UNAVAILABLE"
    fake_torch, fake_tf = types.ModuleType("torch"), types.ModuleType("transformers")
    fake_torch.__version__, fake_tf.__version__ = "9.9", "0"  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "transformers", fake_tf)
    with pytest.raises(ModelUnavailable) as wrong_runtime:
        local_model.TransformersYesNoScorer(tmp_path, MANIFEST)
    assert wrong_runtime.value.code == "RUNTIME_MISMATCH"
    fake_torch.__version__ = "0"  # type: ignore[attr-defined]
    with pytest.raises(ModelUnavailable) as wrong_arch:
        local_model.TransformersYesNoScorer(tmp_path, MANIFEST)
    assert wrong_arch.value.code == "MODEL_ARTIFACT_MISMATCH"
    assert os.environ["HF_HUB_OFFLINE"] == "1" and os.environ["TRANSFORMERS_OFFLINE"] == "1"


@pytest.mark.security
def test_rde_local_model_memory_exhaustion_abstains() -> None:
    class Exhausted(Double):
        def score(self, text: str) -> float:
            raise MemoryError

    a = LocalAmbiguityModel(Path("x"), loader=lambda _d, _m: Exhausted({})).rank(bundle("same"), MANIFEST)
    assert (a.decision, a.reason_codes, a.ranked) == ("abstain", ("RUNTIME_ERROR",), ())
