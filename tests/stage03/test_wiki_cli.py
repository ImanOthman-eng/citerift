"""The ``citerift-wiki`` command line: JSON on stdout, diagnostics on stderr, stable exit codes, no exit 0 on failure.

Captures use a scripted transport injected in place of the network (``capture_revision`` is wrapped); everything
else runs the real commands on SYNTHETIC bundles.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from wiki_support import (
    HTML_TYPE,
    JSON_TYPE,
    REVISION,
    ScriptedClock,
    api_answer,
    bundle,
    parsoid,
    response,
    scripted,
)

from citerift.wiki import cli
from citerift.wiki.capture import capture_revision
from citerift.wiki.fetch import FetchPolicy

TEXT = 'A.<ref name="a">{{cite journal |title=T |doi=10.1000/x}}</ref> B.<ref name="a" />\n'


def run(argv: list[str], capsys: Any) -> tuple[int, Any, str]:
    code = cli.main(argv)
    out, err = capsys.readouterr()
    data = json.loads(out) if out.strip() else None
    return code, data, err


def with_answers(monkeypatch: Any, answers: list[Any]) -> list[str]:
    transport, seen = scripted(answers)

    def fake(request: Any, fetch_policy: Any = None, *, out: Any = None, **_: Any) -> Any:
        return capture_revision(request, FetchPolicy(), out=out, transport=transport, clock=ScriptedClock())

    monkeypatch.setattr(cli, "capture_revision", fake)
    return seen


def api(text: str = TEXT, **kw: Any) -> Any:
    return response(200, {"content-type": JSON_TYPE}, json.dumps(api_answer(text, **kw)).encode())


def html(text: str = TEXT) -> Any:
    return response(200, {"content-type": HTML_TYPE, "content-revision-id": str(REVISION)}, parsoid("<p>A.</p>", text))


# ------------------------------------------------------------------------------------------------ usage


@pytest.mark.negative
@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["capture"],
        ["capture", "--wiki", "fr", "--title", "X", "--out", "o"],
        ["capture", "--wiki", "en", "--page-id", "-1", "--out", "o"],
        ["capture", "--wiki", "en", "--page-id", "1e3", "--out", "o"],
        ["capture", "--wiki", "en", "--page-id", "+5", "--out", "o"],
        ["capture", "--wiki", "en", "--title", "X", "--page-id", "5", "--out", "o"],
        ["extract", "--bundle", "b"],
        ["frobnicate"],
    ],
)
def test_usage_errors_exit_2_with_nothing_on_stdout(argv: list[str], capsys: Any) -> None:
    code, data, err = run(argv, capsys)
    assert code == 2 and data is None and "error" in err


# ---------------------------------------------------------------------------------------------- capture


@pytest.mark.integration
@pytest.mark.parametrize(
    ("answers", "argv_extra", "exit_code", "status"),
    [
        ([api(), html()], [], 0, "complete"),
        ([api()], ["--no-render"], 0, "complete"),
        ([api(), response(429, {"retry-after": "900"}, b"")], [], 6, "partial"),
        ([response(429, {"retry-after": "900"}, b"")], [], 8, "deferred"),
        ([response(403, {}, b"")], [], 4, "failed"),
        ([api(ns=2)], [], 7, "failed"),
        ([api(model="css")], [], 7, "failed"),
        ([api(sha1="0" * 40)], [], 5, "failed"),
        ([api("#REDIRECT [[B]]")], [], 7, "failed"),
    ],
)
def test_capture_exit_codes(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
    answers: list[Any],
    argv_extra: list[str],
    exit_code: int,
    status: str,
) -> None:
    with_answers(monkeypatch, answers)
    out = tmp_path / "b"
    code, data, err = run(
        ["capture", "--wiki", "en", "--revision", str(REVISION), "--out", str(out), *argv_extra], capsys
    )
    assert (code, data["status"]) == (exit_code, status), err
    assert data["capture"]["status"] == status
    assert (data["bundle"] is not None) == (status in ("complete", "partial")) == out.exists()
    if code != 0:
        assert err.strip()


@pytest.mark.security
def test_capture_never_overwrites_and_never_requests_for_an_invalid_title(
    tmp_path: Path, monkeypatch: Any, capsys: Any
) -> None:
    seen = with_answers(monkeypatch, [api(), html()])
    out = tmp_path / "b"
    out.mkdir()
    code, data, _ = run(["capture", "--wiki", "en", "--revision", str(REVISION), "--out", str(out)], capsys)
    assert code == 3 and data["status"] == "failed" and list(out.iterdir()) == []
    seen.clear()
    code, data, _ = run(["capture", "--wiki", "en", "--title", "A|B", "--out", str(tmp_path / "c")], capsys)
    assert code == 3 and seen == [] and not (tmp_path / "c").exists()


# ------------------------------------------------------------------------------------- extract / verify / replay


@pytest.mark.integration
def test_extract_verify_replay_round_trip(tmp_path: Path, capsys: Any) -> None:
    b = bundle(tmp_path, TEXT)
    out = tmp_path / "x.json"
    code, summary, _ = run(["extract", "--bundle", str(b), "--out", str(out)], capsys)
    # a source-only bundle extracts with reconciliation unavailable: partial, exit 6, never 0
    assert (code, summary["status"]) == (6, "partial") and out.is_file()
    assert summary["components"]["render"]["state"] == "not_requested"
    assert summary["extraction_digest"] == json.loads(out.read_text(encoding="utf-8"))["extraction_digest"]
    code, report, _ = run(["verify", "--bundle", str(b), "--extraction", str(out)], capsys)
    assert code == 0 and report["verified"]
    code, report, _ = run(["replay", "--bundle", str(b), "--extraction", str(out)], capsys)
    assert code == 0 and report["replay"]["state"] == "reproduced"
    code, report, _ = run(["replay", "--bundle", str(b)], capsys)
    # P3-12: nothing compared, so the exit code is the new extraction's (partial: 6), never 0 by default
    assert code == 6 and report["replay"]["state"] == "not_compared"


@pytest.mark.negative
def test_extract_refuses_an_existing_output_and_a_bad_bundle(tmp_path: Path, capsys: Any) -> None:
    b = bundle(tmp_path, TEXT)
    out = tmp_path / "x.json"
    out.write_text("keep", encoding="utf-8")
    code, data, err = run(["extract", "--bundle", str(b), "--out", str(out)], capsys)
    assert code == 3 and data is None and "BUNDLE_PATH_UNSAFE" in err and out.read_text(encoding="utf-8") == "keep"
    code, data, err = run(["extract", "--bundle", str(tmp_path / "missing"), "--out", str(tmp_path / "y")], capsys)
    assert code == 3 and data["status"] == "failed" and (tmp_path / "y").exists()  # the failure is a document


@pytest.mark.negative
def test_verify_and_replay_exit_codes_on_damage(tmp_path: Path, capsys: Any) -> None:
    b = bundle(tmp_path, TEXT)
    out = tmp_path / "x.json"
    assert run(["extract", "--bundle", str(b), "--out", str(out)], capsys)[0] == 6
    code, report, _ = run(["verify", "--bundle", str(tmp_path / "missing")], capsys)
    assert code == 3 and not report["verified"]
    doc = json.loads(out.read_text(encoding="utf-8"))
    doc["identifiers"][0]["source"]["cp_start"] += 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(doc), encoding="utf-8")
    code, report, err = run(["verify", "--bundle", str(b), "--extraction", str(bad)], capsys)
    assert code == 5 and not report["verified"] and "BUNDLE_DIGEST_MISMATCH" in err
    code, report, _ = run(["replay", "--bundle", str(b), "--extraction", str(bad)], capsys)
    assert code == 5 and report["replay"]["state"] != "reproduced"
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"max_depth": 10}), encoding="utf-8")
    code, report, _ = run(["replay", "--bundle", str(b), "--extraction", str(out), "--config", str(cfg)], capsys)
    assert code == 5 and report["replay"]["state"] == "not_compared"
    cfg.write_text('{"max_depth": 10, "max_depth": 11}', encoding="utf-8")
    code, report, err = run(["replay", "--bundle", str(b), "--config", str(cfg)], capsys)
    assert code == 3 and report is None and "duplicate" in err.lower()


@pytest.mark.integration
def test_the_installed_entry_point_runs(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "citerift.wiki.cli", "verify", "--bundle", str(tmp_path / "missing")],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 3 and json.loads(proc.stdout)["verified"] is False and proc.stderr.strip()
