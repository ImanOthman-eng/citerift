"""MF-1: the C tokenizer of mwparserfromhell could segfault under the worker's memory limit, so a memory failure was
reported as EXTRACTION_WORKER_FAILED. The first repair (b00fa65) switched the engine to the pure-Python tokenizer;
review R7 (RF7-1, RF7-2) showed that this changed extraction of bare URLs followed by ``:`` ``;`` ``!`` and made
unclosed constructs far slower. The engine keeps the C tokenizer, and the worker runner classifies a native crash by
one more run with the pure-Python tokenizer, whose output is never returned as an extraction. SYNTHETIC."""

from __future__ import annotations

import json
import signal
from pathlib import Path
from typing import Any

import mwparserfromhell
import pytest
from wiki_support import bundle

import citerift.wiki.source  # noqa: F401 - importing the engine must not change the tokenizer
from citerift.wiki import extract as ex
from citerift.wiki.extract import ExtractConfig, extract_bundle


@pytest.mark.regression
def test_the_engine_parses_with_the_c_tokenizer() -> None:
    assert mwparserfromhell.parser.use_c is True
    assert type(mwparserfromhell.parser.Parser()._tokenizer).__name__ == "CTokenizer"


@pytest.mark.regression
@pytest.mark.parametrize("tail", [": Smith 2001", "; Smith 2001", "! Smith", ". Smith", ", Smith"])
def test_sentence_punctuation_after_a_bare_doi_url_is_outside_the_link(tmp_path: Path, tail: str) -> None:
    """RF7-1: as MediaWiki and the C tokenizer, a bare link ends before ``,;.:!`` that a space follows."""
    doc = extract_bundle(bundle(tmp_path, f"Claim.<ref>https://doi.org/10.1234/abc{tail}</ref>\n"))
    assert [i["normalization"]["normalized"] for i in doc["identifiers"]] == ["10.1234/abc"]


@pytest.mark.security
def test_the_memory_limit_is_reported_as_such_every_time(tmp_path: Path) -> None:
    text = "".join(
        f'P{i}.<ref name="n{i}">{{{{cite journal |title=T{i} |doi=10.1234/x{i}}}}}</ref>\n' for i in range(20000)
    )
    b = bundle(tmp_path, text)
    codes = [{i["code"] for i in extract_bundle(b, ExtractConfig(worker_memory_mib=64))["issues"]} for _ in range(8)]
    assert codes == [{"EXTRACTION_MEMORY_EXCEEDED"}] * 8


class FakeProc:
    def __init__(self, returncode: int, stderr: bytes = b"", stdout: bytes = b"") -> None:
        self.returncode, self.out, self.err, self.pid = returncode, stdout, stderr, 0

    def communicate(self, timeout: float | None = None) -> tuple[bytes, bytes]:
        return self.out, self.err


def _scripted(monkeypatch: pytest.MonkeyPatch, procs: list[FakeProc]) -> list[list[str]]:
    calls: list[list[str]] = []

    def popen(cmd: list[str], **_: Any) -> FakeProc:
        calls.append(cmd)
        return procs.pop(0)

    monkeypatch.setattr(ex.subprocess, "Popen", popen)
    return calls


@pytest.mark.regression
@pytest.mark.parametrize("sig", [signal.SIGSEGV, signal.SIGBUS])
def test_a_native_crash_confirmed_as_memory_by_the_python_tokenizer_is_memory_exceeded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sig: int
) -> None:
    b = bundle(tmp_path, "Text.")
    calls = _scripted(monkeypatch, [FakeProc(-sig), FakeProc(3, b"MemoryError")])
    doc = extract_bundle(b, ExtractConfig(worker_memory_mib=64))
    assert {i["code"] for i in doc["issues"]} == {"EXTRACTION_MEMORY_EXCEEDED"}
    assert "python-tokenizer" not in calls[0] and calls[1][-1] == "python-tokenizer"


@pytest.mark.negative
def test_a_native_crash_that_is_not_memory_stays_a_worker_failure_and_no_python_output_is_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    b = bundle(tmp_path, "Text.")
    good = extract_bundle(b, isolated=False)
    _scripted(monkeypatch, [FakeProc(-signal.SIGSEGV), FakeProc(0, stdout=json.dumps(good).encode())])
    doc = extract_bundle(b)
    assert doc["status"] == "failed" and {i["code"] for i in doc["issues"]} == {"EXTRACTION_WORKER_FAILED"}


@pytest.mark.negative
def test_other_worker_failures_are_not_run_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    b = bundle(tmp_path, "Text.")
    calls = _scripted(monkeypatch, [FakeProc(1, b"Traceback\nValueError: x")])
    doc = extract_bundle(b)
    assert {i["code"] for i in doc["issues"]} == {"EXTRACTION_WORKER_FAILED"} and len(calls) == 1
