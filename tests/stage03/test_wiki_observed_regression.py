"""Regression on two observed Wikipedia revisions (tests/stage03/fixtures/observed, CC BY-SA 4.0, see ATTRIBUTION.md).

The articles cite the two retracted 2014 STAP papers and their retraction notices in both languages, so they pin the
behavior that matters most downstream: the cited works are primary citation fields, the notices are marker targets
and never promoted, and an Arabic red link to a missing template is kept apart from a rendered warning.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from citerift.wiki.extract import extract_bundle
from citerift.wiki.verify import replay_bundle, verify_bundle

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "observed"
EXPECTED = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))


@pytest.mark.regression
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_observed_revision_extracts_as_recorded(name: str) -> None:
    b = FIXTURES / name
    assert verify_bundle(b)["verified"]
    doc = extract_bundle(b)
    want = EXPECTED[name]
    got = {
        "status": doc["status"],
        "extraction_digest": doc["extraction_digest"],
        "containers": doc["accounting"]["containers"],
        "uses": doc["accounting"]["uses"],
        "identifiers_by_role": doc["accounting"]["identifiers_by_role"],
        "exceptions": dict(sorted(Counter(e["code"] for e in doc["exceptions"]).items())),
        "markers": doc["accounting"]["markers"],
        "primary_keys": sorted(
            {
                i["normalization"]["normalized"]
                for i in doc["identifiers"]
                if i["role"] == "primary_citation_field" and i["normalization"]["normalized"]
            }
        ),
        "marker_target_keys": sorted(
            {
                i["normalization"]["normalized"]
                for i in doc["identifiers"]
                if i["role"] == "marker_target" and i["normalization"]["normalized"]
            }
        ),
    }
    assert got == want
    assert verify_bundle(b, doc)["verified"]
    assert replay_bundle(b, None, doc)["replay"]["state"] == "reproduced"


@pytest.mark.regression
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_retraction_notices_are_never_cited_works(name: str) -> None:
    doc = extract_bundle(FIXTURES / name)
    notices = set(EXPECTED[name]["marker_target_keys"])
    cited = {i["normalization"]["normalized"] for i in doc["identifiers"] if i["role"] == "primary_citation_field"}
    assert notices and not notices & cited
    assert {"10.1038/nature12968", "10.1038/nature12969"} <= cited


@pytest.mark.regression
def test_arabic_red_template_link_is_not_a_rendered_warning() -> None:
    doc = extract_bundle(FIXTURES / "ar-76190003")
    states = Counter(m["state"] for m in doc["markers"])
    assert states["missing_template_link_only"] == 2 and states["recognized_warning_text"] == 0
