"""The D-036 campaign scripts are copies of the frozen 2026-11 scripts (through the D-035 copies), changed only as
AMENDMENT_2026-11-04_D036_CONFIRMATION.md section 2 lists: the docstrings, and in ``select_confirmation.py`` the
salt, the unused challenge salt and the campaign name. ``make_packets_partial.py`` is the D-035 wrapper with one
docstring paragraph added."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "docs/verification/stage-03/evaluation"
OLD = EVAL / "confirmation-2026-11/scripts"
D035 = EVAL / "confirmation-d035/scripts"
NEW = EVAL / "confirmation-d036/scripts"
SAME = [
    "disagreements_v2.py",
    "exposure_set.py",
    "intervals.py",
    "reserve_step.py",
    "run_confirmation.py",
    "warning_challenge.py",
]
CHANGED_NAMES = frozenset({"SALT", "CHALLENGE_SALT", "STRATA"})


def _body(path: Path, drop: frozenset[str] = frozenset()) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    body = tree.body[1:] if isinstance(tree.body[0], ast.Expr) else tree.body
    kept = []
    for node in body:
        targets = (
            [t.id for t in node.targets if isinstance(t, ast.Name)]
            if isinstance(node, ast.Assign)
            else [node.target.id]
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
            else []
        )
        if not set(targets) & drop:
            kept.append(node)
    text = ast.dump(ast.Module(body=kept, type_ignores=[]))
    for name in ("confirmation-2026-11", "confirmation-d035", "confirmation-d036"):
        text = text.replace(name, "CAMPAIGN")
    return text


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"d036_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.regression
@pytest.mark.parametrize("name", SAME)
def test_d036_copied_script_code_is_unchanged(name: str) -> None:
    assert _body(NEW / name) == _body(OLD / name) == _body(D035 / name)


@pytest.mark.regression
def test_d036_make_packets_partial_code_is_the_d035_wrapper() -> None:
    assert _body(NEW / "make_packets_partial.py") == _body(D035 / "make_packets_partial.py")


@pytest.mark.regression
def test_d036_select_differs_only_in_salt_strata_and_campaign_name() -> None:
    assert _body(NEW / "select_confirmation.py", CHANGED_NAMES) == _body(OLD / "select_confirmation.py", CHANGED_NAMES)
    new = _load(NEW / "select_confirmation.py")
    old = _load(OLD / "select_confirmation.py")
    d035 = _load(D035 / "select_confirmation.py")
    assert new.SALT == "citerift-stage03-confirmation-d036-2026-11-04-v1"
    assert new.SALT not in (old.SALT, d035.SALT)
    assert new.STRATA == {"ar": [], "en": []}
    assert (new.INITIAL, new.MAXIMUM, new.BLOCK, new.MAX_BATCHES) == (
        old.INITIAL,
        old.MAXIMUM,
        old.BLOCK,
        old.MAX_BATCHES,
    )


@pytest.mark.regression
def test_d036_select_makes_no_challenge_request_and_plans_no_challenge() -> None:
    new = _load(NEW / "select_confirmation.py")
    calls: list[str] = []

    def get(url: str) -> dict[str, object]:
        calls.append(url)
        raise AssertionError("no request expected")

    assert new.challenge(get, "en", set(), set()) == {}
    assert new.challenge(get, "ar", set(), set()) == {}
    assert calls == []
    selection = {
        "frame": {w: {"initial": [{"page_id": 1}], "reserve_blocks": [[{"page_id": 2}]]} for w in ("ar", "en")},
        "challenge": {"ar": {}, "en": {}},
    }
    plan = new.plan(selection, {"en": 1}, with_challenge=False)
    assert plan["campaign"] == "confirmation-d036"
    assert [a["split"] for a in plan["articles"]] == ["holdout", "holdout", "reserve1"]


@pytest.mark.security
def test_d036_secret_gate_withholds_a_matching_file_and_records_no_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _load(NEW / "secret_gate.py")
    key_id = "AK" + "IA" + "Q" * 16  # built at run time: no tracked file holds the pattern
    (tmp_path / "capture").mkdir()
    planted = tmp_path / "capture" / "render.html"
    planted.write_text(f"<a href='https://example.invalid/x?AWSAccessKeyId={key_id}'>x</a>", encoding="utf-8")
    clean = tmp_path / "capture" / "source.wikitext"
    clean.write_text("no secret here", encoding="utf-8")
    monkeypatch.setattr(gate, "untracked", lambda campaign: [planted, clean])
    assert gate.main(["secret_gate.py", str(tmp_path)]) == 3
    ledger = (tmp_path / "WITHHELD_FILES.json").read_text(encoding="utf-8")
    assert key_id not in ledger
    assert json.loads(ledger)["files"][0]["path"] == "capture/render.html"
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines() == ["/capture/render.html"]
    assert planted.read_text(encoding="utf-8").count(key_id) == 1  # kept on disk unchanged
    assert gate.main(["secret_gate.py", str(tmp_path)]) == 0  # already withheld: nothing new
    monkeypatch.setattr(gate, "untracked", lambda campaign: [clean])
    assert gate.main(["secret_gate.py", str(tmp_path)]) == 0


@pytest.mark.security
def test_d036_secret_gate_uses_the_stage00_patterns_and_more() -> None:
    gate = _load(NEW / "secret_gate.py")
    stage00 = _load(ROOT / "tests/stage00/test_repository.py")
    found = [p.pattern for p in gate.patterns()]
    assert found[: len(stage00.SECRET_PATTERNS)] == [p.pattern for p in stage00.SECRET_PATTERNS]
    assert found[len(stage00.SECRET_PATTERNS) :] == [p.pattern for p in gate.EXTRA_PATTERNS]


# Review B-3: access-bearing shapes the Stage 00 list misses. Every sample is FAKE, built from repeated characters at
# run time.
B3_SAMPLES = {
    "s3 sigv4 sts": "https://b.s3.example.invalid/o?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential="
    + "AS"
    + "IA"
    + "Q" * 16
    + "%2F20261104%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Security-Token="
    + "F" * 300
    + "&X-Amz-Signature="
    + "a" * 64,
    "s3 percent-encoded key id": "https://b.s3.example.invalid/o?X-Amz-Credential=%41KIA" + "Q" * 16 + "%2F2026",
    "s3 sigv2 html-escaped": "https://s3.example.invalid/b/o?AWSAccessKeyId=" + "X" * 20 + "&amp;Expires=1",
    "gcs v4": "https://storage.example.invalid/b/o?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Signature=" + "a" * 512,
    "azure sas": "https://acct.blob.example.invalid/c/o?sv=2022-11-02&se=2026-12-01&sp=r&sig=" + "A" * 43 + "%3D",
    "azure sas html-escaped, sig first": "https://acct.blob.example.invalid/c/o?sig=" + "A" * 43 + "&amp;sv=2022-11-02",
    "google api key": "key=" + "AI" + "za" + "B" * 35,
    "slack webhook": "https://hooks.slack.com/services/T" + "0" * 8 + "/B" + "0" * 8 + "/" + "x" * 24,
    # re-review R-03
    "gcs v2": "https://storage.example.invalid/b/o.pdf?GoogleAccessId=svc@p.example.invalid&Expires=1&Signature="
    + "A" * 40,
    "cloudfront": "https://d1.example.invalid/f.pdf?Expires=1&Signature=" + "B" * 40 + "&Key-Pair-Id=K" + "Q" * 13,
    "s3 sigv4 nested in a redirect": "https://r.example.invalid/url?q=https://b.example.invalid/o%3FX-Amz-Credential%3D%2541KIA"
    + "Q" * 16
    + "%252F2026%26X-Amz-Signature%3D"
    + "a" * 64,
    "azure sas nested in a redirect": "https://r.example.invalid/url?q=https://a.example.invalid/c/o%3Fsv%3D2022-11-02%26sig%3D"
    + "A" * 43,
    "lowercase sigv4 names": "https://b.example.invalid/o?x-amz-credential=x&x-amz-signature=" + "a" * 64,
}


@pytest.mark.security
@pytest.mark.parametrize("name", sorted(B3_SAMPLES))
def test_d036_secret_gate_catches_access_bearing_urls_stage00_misses(name: str) -> None:
    gate = _load(NEW / "secret_gate.py")
    stage00 = _load(ROOT / "tests/stage00/test_repository.py")
    sample = B3_SAMPLES[name]
    assert not any(p.search(sample) for p in stage00.SECRET_PATTERNS)
    assert any(p.search(text) for text in gate.scanned(sample.encode()) for p in gate.patterns())


@pytest.mark.security
@pytest.mark.negative
def test_d036_secret_gate_leaves_ordinary_citation_urls_alone() -> None:
    gate = _load(NEW / "secret_gate.py")
    ordinary = (
        '<a href="https://doi.org/10.1000/xyz">doi</a> '
        '<a href="https://books.example.invalid/books?id=abc&amp;pg=PA5&amp;sig=ACfU3U0">book</a> '
        '<a href="https://archive.example.invalid/web/20200101000000/https://example.org/?sv=1">archive</a>'
    )
    assert not any(p.search(text) for text in gate.scanned(ordinary.encode()) for p in gate.patterns())
