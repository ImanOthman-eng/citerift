"""MF-1: the C tokenizer of mwparserfromhell could segfault under the worker's memory limit, so a memory failure was
reported as EXTRACTION_WORKER_FAILED. The engine uses the library's pure-Python tokenizer. SYNTHETIC."""

from __future__ import annotations

from pathlib import Path

import mwparserfromhell
import pytest
from mwparserfromhell.parser.tokenizer import Tokenizer
from wiki_support import bundle

import citerift.wiki.source  # noqa: F401 - importing the engine selects the tokenizer
from citerift.wiki.extract import ExtractConfig, extract_bundle


@pytest.mark.regression
def test_the_engine_parses_with_the_python_tokenizer() -> None:
    assert mwparserfromhell.parser.use_c is False
    assert type(mwparserfromhell.parser.Parser()._tokenizer) is Tokenizer


@pytest.mark.security
def test_the_memory_limit_is_reported_as_such_every_time(tmp_path: Path) -> None:
    text = "".join(
        f'P{i}.<ref name="n{i}">{{{{cite journal |title=T{i} |doi=10.1234/x{i}}}}}</ref>\n' for i in range(20000)
    )
    b = bundle(tmp_path, text)
    codes = [{i["code"] for i in extract_bundle(b, ExtractConfig(worker_memory_mib=64))["issues"]} for _ in range(8)]
    assert codes == [{"EXTRACTION_MEMORY_EXCEEDED"}] * 8
