"""Step 6: the D-043 unit anchor (SR-03 option A) over retained Stage 03 bytes (SPEC 4.3, S-12.1).

``unit_span_sha256 = SHA-256(source_artifact_bytes[byte_start:byte_end])``, half-open, over the exact retained
source artifact. The observed Stage 03 fixtures are read through the accepted Stage 03 functions; nothing in Stage 03
is changed.
"""

from __future__ import annotations

import copy
import hashlib
import shutil
from pathlib import Path
from typing import Any

import pytest
from memory_support import STAGE04, SUBJECT, Clock, bundle_request, drive, h, memory_root

from citerift.investigation import ids
from citerift.investigation.anchors import SourceArtifact, read_retained_source, unit_span_sha256, verify_unit_span
from citerift.investigation.errors import SpanError
from citerift.investigation.memory import InvestigationMemory, created_payload
from citerift.wiki.extract import extract_bundle

OBSERVED = Path(__file__).resolve().parents[1] / "stage03" / "fixtures" / "observed"
AR = OBSERVED / "ar-76190003"
EN = OBSERVED / "en-1372543632"


def _extraction(bundle: Path) -> dict[str, Any]:
    return extract_bundle(bundle, None, isolated=False)


@pytest.fixture(scope="module")
def ar() -> dict[str, Any]:
    return _extraction(AR)


@pytest.fixture(scope="module")
def en() -> dict[str, Any]:
    return _extraction(EN)


def _source(bundle: Path, doc: dict[str, Any]) -> SourceArtifact:
    return read_retained_source(bundle, doc["capture"], doc["capture"]["capture_sha256"])


def _derive(src: SourceArtifact, doc: dict[str, Any], span: dict[str, Any], **kw: Any) -> str:
    return unit_span_sha256(
        src,
        span,
        extraction_capture=kw.pop("capture", doc["capture"]),
        root_capture_sha256=kw.pop("root", doc["capture"]["capture_sha256"]),
        identifiers=kw.pop("identifiers", doc["identifiers"]),
    )


def _synthetic(text: str) -> tuple[SourceArtifact, dict[str, Any]]:
    data = text.encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    capture = {"capture_sha256": h("capture"), "source_artifact": sha}
    return SourceArtifact(data, sha), capture


def _span(text: str, c0: int, c1: int) -> dict[str, int]:
    return {
        "cp_start": c0,
        "cp_end": c1,
        "byte_start": len(text[:c0].encode()),
        "byte_end": len(text[:c1].encode()),
    }


# Positive: the hash is the SHA-256 of the exact retained bytes ------------------------------------------------------


@pytest.mark.unit
def test_ascii_span(en: dict[str, Any]) -> None:
    src = _source(EN, en)
    ascii_units = [u for u in en["units"] if u["source"]["byte_end"] - u["source"]["byte_start"]
                   == u["source"]["cp_end"] - u["source"]["cp_start"]]  # fmt: skip
    assert ascii_units
    for unit in ascii_units:
        s = unit["source"]
        assert _derive(src, en, s) == hashlib.sha256(src.data[s["byte_start"] : s["byte_end"]]).hexdigest()
    text = "Smith (2014). doi:10.1000/xyz"
    syn, cap = _synthetic(text)
    assert unit_span_sha256(syn, _span(text, 0, 5), extraction_capture=cap, root_capture_sha256=h("capture")) == (
        hashlib.sha256(b"Smith").hexdigest()
    )


@pytest.mark.unit
def test_arabic_multibyte_spans_hash_bytes_not_code_points(ar: dict[str, Any]) -> None:
    src = _source(AR, ar)
    multibyte = [u for u in ar["units"] if u["source"]["byte_end"] - u["source"]["byte_start"]
                 != u["source"]["cp_end"] - u["source"]["cp_start"]]  # fmt: skip
    assert len(multibyte) >= 20  # the observed Arabic revision: 26 of 32 units are multibyte
    for unit in ar["units"]:
        s = unit["source"]
        digest = _derive(src, ar, s)
        assert digest == hashlib.sha256(src.data[s["byte_start"] : s["byte_end"]]).hexdigest()
        # The bytes are the UTF-8 encoding of the code-point slice: the two spans name the same text.
        assert src.data[s["byte_start"] : s["byte_end"]] == src.text[s["cp_start"] : s["cp_end"]].encode()
    text = "مرجع: ١٠٫١٠٠٠"
    syn, cap = _synthetic(text)
    span = _span(text, 0, 4)
    assert span["byte_end"] == 8  # four two-byte letters
    assert unit_span_sha256(syn, span, extraction_capture=cap, root_capture_sha256=h("capture")) == (
        hashlib.sha256("مرجع".encode()).hexdigest()
    )


@pytest.mark.unit
def test_empty_span_is_the_hash_of_no_bytes() -> None:
    text = "abc"
    syn, cap = _synthetic(text)
    span = _span(text, 3, 3)
    assert unit_span_sha256(syn, span, extraction_capture=cap, root_capture_sha256=h("capture")) == h("")


@pytest.mark.unit
def test_same_span_identifier_parity_on_observed_anchors(ar: dict[str, Any], en: dict[str, Any]) -> None:
    """Where a Stage 03 identifier anchor covers the same span, its raw_sha256 equals the derived hash."""
    for bundle, doc in ((AR, ar), (EN, en)):
        src = _source(bundle, doc)
        assert doc["identifiers"]
        for ident in doc["identifiers"]:
            anchor = ident["source"]
            span = {k: anchor[k] for k in ("cp_start", "cp_end", "byte_start", "byte_end")}
            assert _derive(src, doc, span) == anchor["raw_sha256"]


# Negative: every mismatch fails closed; nothing falls back to another identity -----------------------------------


@pytest.mark.negative
def test_identifier_parity_mismatch_is_refused(ar: dict[str, Any]) -> None:
    src = _source(AR, ar)
    idents = copy.deepcopy(ar["identifiers"])
    anchor = idents[0]["source"]
    anchor["raw_sha256"] = h("another text")
    span = {k: anchor[k] for k in ("cp_start", "cp_end", "byte_start", "byte_end")}
    with pytest.raises(SpanError) as exc:
        _derive(src, ar, span, identifiers=idents)
    assert exc.value.code == "ANCHOR_MISMATCH"


@pytest.mark.negative
@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"byte_end": 10**9}, "SPAN_INVALID"),  # out of range
        ({"byte_start": -1}, "SPAN_INVALID"),
        ({"cp_end": 10**9}, "SPAN_INVALID"),
        ({"byte_start": 9, "byte_end": 8}, "SPAN_INVALID"),  # reversed
        ({"byte_start": 1}, "SPAN_INVALID"),  # inside the first two-byte letter: not a boundary
        ({"byte_end": 7}, "SPAN_INVALID"),  # ends inside a letter
        ({"cp_end": 3}, "SPAN_INVALID"),  # byte span and code-point span disagree
        ({"byte_end": True}, "SPAN_INVALID"),  # a boolean is not an integer
        ({"byte_end": 8.0}, "SPAN_INVALID"),  # nor is a float
    ],
)
def test_boundary_and_range_errors(change: dict[str, Any], code: str) -> None:
    text = "مرجع: ١٠٫١٠٠٠"
    syn, cap = _synthetic(text)
    span = {**_span(text, 0, 4), **change}
    with pytest.raises(SpanError) as exc:
        unit_span_sha256(syn, span, extraction_capture=cap, root_capture_sha256=h("capture"))
    assert exc.value.code == code


@pytest.mark.negative
def test_modified_source_is_refused(tmp_path: Path, ar: dict[str, Any]) -> None:
    sha = ar["capture"]["source_artifact"]
    data = (AR / "artifacts" / sha).read_bytes()
    with pytest.raises(SpanError) as exc:
        SourceArtifact(data.replace("ا".encode(), "ب".encode(), 1), sha)
    assert exc.value.code == "SOURCE_DIGEST_MISMATCH"
    copy_dir = tmp_path / "bundle"
    shutil.copytree(AR, copy_dir)
    victim = copy_dir / "artifacts" / sha
    victim.chmod(0o644)
    victim.write_bytes(data[:-1] + b" ")
    with pytest.raises(SpanError) as exc:
        _source(copy_dir, ar)
    assert exc.value.code == "SOURCE_DIGEST_MISMATCH"


@pytest.mark.negative
def test_span_from_another_root_or_extraction_is_refused(ar: dict[str, Any], en: dict[str, Any]) -> None:
    src = _source(AR, ar)
    span = ar["units"][0]["source"]
    with pytest.raises(SpanError) as exc:
        _derive(src, ar, span, root=en["capture"]["capture_sha256"])  # the bound root is another capture
    assert exc.value.code == "ROOT_IDENTITY_MISMATCH"
    with pytest.raises(SpanError) as exc:
        _derive(src, ar, span, capture={**ar["capture"], "source_artifact": en["capture"]["source_artifact"]})
    assert exc.value.code == "SOURCE_DIGEST_MISMATCH"
    with pytest.raises(SpanError) as exc:
        read_retained_source(AR, ar["capture"], en["capture"]["capture_sha256"])
    assert exc.value.code == "ROOT_IDENTITY_MISMATCH"
    with pytest.raises(SpanError) as exc:
        read_retained_source(EN, ar["capture"], en["capture"]["capture_sha256"])  # the bundle names another source
    assert exc.value.code == "SOURCE_DIGEST_MISMATCH"


# Replay: VERIFY recomputes the recorded value from the retained bytes ---------------------------------------------


@pytest.mark.integration
def test_replay_recomputes_the_recorded_unit_anchor(tmp_path: Path, ar: dict[str, Any]) -> None:
    root = memory_root(tmp_path)
    src = _source(AR, ar)
    unit = ar["units"][1]
    recorded = _derive(src, ar, unit["source"])
    payload = created_payload(bundle_request(root), STAGE04, bundle_capture_sha256=ar["capture"]["capture_sha256"])
    with InvestigationMemory.create(root, payload, clock=Clock()) as mem:
        key = mem.key
        drive_value = {"source_artifact": ar["capture"]["source_artifact"], "unit_span_sha256": recorded}
        _record_unit(mem, ar, drive_value)
    with InvestigationMemory.open(root, key, writable=False, clock=Clock()) as again:
        ev = next(e for e in again.view.committed.evidence.values() if e["kind"] == "unit")
        assert ev["value"] == drive_value
        verify_unit_span(
            ev["value"]["unit_span_sha256"],
            _source(AR, ar),
            unit["source"],
            extraction_capture=ar["capture"],
            root_capture_sha256=ar["capture"]["capture_sha256"],
            identifiers=ar["identifiers"],
        )
        with pytest.raises(SpanError) as exc:
            verify_unit_span(
                h("a recorded value that the bytes do not give"),
                _source(AR, ar),
                unit["source"],
                extraction_capture=ar["capture"],
                root_capture_sha256=ar["capture"]["capture_sha256"],
            )
        assert exc.value.code == "ANCHOR_MISMATCH"


def _record_unit(mem: InvestigationMemory, doc: dict[str, Any], value: dict[str, str]) -> None:
    """VALIDATE, ACQUIRE (binding the observed root), EXTRACT, then NORMALIZE with one unit evidence record."""
    cap = doc["capture"]
    identity = {"wiki": cap["wiki"], "page_id": cap["page_id"], "revision_id": cap["revision_id"],
                "capture_sha256": cap["capture_sha256"]}  # fmt: skip
    root = {"root_id": ids.root_id(SUBJECT, identity),
            "subject": {"type": SUBJECT, "identity": identity, "display": {"title": cap["title"],
                                                                           "revision_sha1": cap["sha1"]}}}  # fmt: skip
    drive(mem, ("VALIDATE",))
    for step, n in (("ACQUIRE", 1), ("EXTRACT", 1), ("NORMALIZE", 1)):
        mem.append("step_started", {"step_key": h(step)}, step=step, attempt=n)
        blob = mem.put_blob({"step": step, "capture_sha256": cap["capture_sha256"]})
        if step == "ACQUIRE":
            src = {"engine": "citerift.wiki", "operation": "open_bundle", "locator": None}
            mem.append("observation_recorded", {"obs_kind": "bundle", "blob": blob, "source_ref": src}, step=step,
                       attempt=n)  # fmt: skip
        if step == "EXTRACT":
            src = {"engine": "citerift.wiki", "operation": "extract_bundle", "locator": None}
            mem.append("observation_recorded", {"obs_kind": "extraction", "blob": blob, "source_ref": src},
                       step=step, attempt=n)  # fmt: skip
            extraction = blob
        if step == "NORMALIZE":
            ev_id = ids.record_digest({"o": extraction, "p": "/units/1", "k": "unit"})
            ev = {"evidence_id": ev_id, "observation": extraction, "pointer": "/units/1", "kind": "unit", "refs": [],
                  "value": value}  # fmt: skip
            mem.append("evidence_recorded", ev, step=step, attempt=n)
        mem.append("step_succeeded", {"step_key": h(step), "outputs": [blob], "root": root if step == "ACQUIRE"
                                      else None}, step=step, attempt=n)  # fmt: skip


@pytest.mark.negative
@pytest.mark.parametrize("ident", ["not an object", {"id": "id-1", "source": "not an anchor"}])
def test_malformed_identifier_records_fail_closed(ident: Any) -> None:
    text = "abc"
    syn, cap = _synthetic(text)
    with pytest.raises(SpanError) as exc:
        unit_span_sha256(
            syn, _span(text, 0, 3), extraction_capture=cap, root_capture_sha256=h("capture"), identifiers=[ident]
        )
    assert exc.value.code == "SPAN_INVALID"
