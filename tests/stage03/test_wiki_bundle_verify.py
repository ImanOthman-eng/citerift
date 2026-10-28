"""Bundle safety, offline verification, replay and worker isolation, on SYNTHETIC captures.

Every bundle here is produced by the production capture code with a scripted transport (``wiki_support``); the
tests then damage it the way a disk, a copy or an adversary could and check that each damage is refused with its
stable code, and that nothing is ever replaced or read through a symbolic link.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, doi_link, note_li, ref_sup, references

from citerift.wiki.bundle import BundleError, open_bundle, publish_bundle, publish_file, read_artifact
from citerift.wiki.canonical import canonical_bytes, digest, sha256_hex
from citerift.wiki.extract import ExtractConfig, extract_bundle
from citerift.wiki.verify import replay_bundle, verify_bundle

TEXT = 'Alpha.<ref name="a">{{cite journal |title=T |doi=10.1234/abc |pmid=123}}</ref> Beta.<ref name="a" />\n'
BODY = (
    "<p>Alpha."
    + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
    + " Beta."
    + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-1", name="a")
    + "</p>"
    + references([note_li("cite_note-a-1", ["cite_ref-a_1-0", "cite_ref-a_1-1"], "T " + doi_link("10.1234/abc"))])
)


def made(tmp: Path) -> Path:
    return bundle(tmp, TEXT, BODY)


def issue_codes(report: dict[str, Any]) -> set[str]:
    return {i["code"] for i in report["issues"]}


def capture_json(path: Path) -> dict[str, Any]:
    return json.loads((path / "capture.json").read_text(encoding="utf-8"))


def rewrite_capture(path: Path, change: Any) -> None:
    cap = capture_json(path)
    change(cap)
    (path / "capture.json").write_text(json.dumps(cap, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------------------------------------- publication


@pytest.mark.security
def test_publication_never_replaces_an_existing_path(tmp_path: Path) -> None:
    (tmp_path / "taken").mkdir()
    with pytest.raises(BundleError) as err:
        publish_bundle(tmp_path / "taken", {"x": 1}, {})
    assert err.value.issue.code == "BUNDLE_PATH_UNSAFE"
    os.symlink(tmp_path / "nowhere", tmp_path / "dangling")
    with pytest.raises(BundleError):
        publish_bundle(tmp_path / "dangling", {"x": 1}, {})
    (tmp_path / "out.json").write_bytes(b"old")
    with pytest.raises(BundleError):
        publish_file(tmp_path / "out.json", b"new")
    assert (tmp_path / "out.json").read_bytes() == b"old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dangling", "out.json", "taken"]  # no temporary left


@pytest.mark.security
def test_publication_refuses_a_symlinked_parent_and_mislabelled_artifacts(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    os.symlink(real, tmp_path / "link")
    with pytest.raises(BundleError) as err:
        publish_bundle(tmp_path / "link" / "b", {"x": 1}, {})
    assert err.value.issue.code == "BUNDLE_PATH_UNSAFE"
    with pytest.raises(BundleError) as err:
        publish_bundle(real / "b", {"x": 1}, {"0" * 64: b"not that"})
    assert err.value.issue.code == "BUNDLE_ARTIFACT_CORRUPT" and not (real / "b").exists()


# ------------------------------------------------------------------------------------------------ reading


@pytest.mark.security
def test_symlinks_anywhere_in_a_bundle_are_refused(tmp_path: Path) -> None:
    b = made(tmp_path)
    os.symlink(b, tmp_path / "alias")
    assert issue_codes(verify_bundle(tmp_path / "alias")) == {"BUNDLE_PATH_UNSAFE"}
    victim = tmp_path / "victim"
    shutil.copytree(b, victim)
    art = next((victim / "artifacts").iterdir())
    data = art.read_bytes()
    outside = tmp_path / "outside"
    outside.write_bytes(data)
    art.unlink()
    os.symlink(outside, art)
    with pytest.raises(BundleError) as err:
        read_artifact(victim, art.name)
    assert err.value.issue.code == "BUNDLE_PATH_UNSAFE"
    report = verify_bundle(victim)
    assert not report["verified"] and "BUNDLE_PATH_UNSAFE" in issue_codes(report)


@pytest.mark.security
@pytest.mark.parametrize("name", ["../capture.json", "/etc/passwd", "A" * 64, "0" * 63, "x"])
def test_artifact_names_must_be_sha256(tmp_path: Path, name: str) -> None:
    b = made(tmp_path)
    with pytest.raises(BundleError) as err:
        read_artifact(b, name)
    assert err.value.issue.code == "BUNDLE_PATH_UNSAFE"


@pytest.mark.negative
def test_capture_json_must_be_strict_json_object(tmp_path: Path) -> None:
    b = made(tmp_path)
    (b / "capture.json").write_text('{"schema": "a", "schema": "b"}', encoding="utf-8")
    with pytest.raises(BundleError) as err:
        open_bundle(b)
    assert err.value.issue.code == "BUNDLE_MALFORMED" and "duplicate" in err.value.issue.detail.lower()
    (b / "capture.json").write_text("[1, 2]", encoding="utf-8")
    assert issue_codes(verify_bundle(b)) == {"BUNDLE_MALFORMED"}
    (b / "capture.json").unlink()
    assert issue_codes(verify_bundle(b)) == {"BUNDLE_MALFORMED"}


# ------------------------------------------------------------------------------------------- verification


@pytest.mark.integration
def test_a_fresh_bundle_and_its_extraction_verify(tmp_path: Path) -> None:
    b = made(tmp_path)
    doc = extract_bundle(b, isolated=False)
    report = verify_bundle(b, doc)
    assert report["verified"] and report["issues"] == []
    assert report["extraction_digest"] == doc["extraction_digest"]


@pytest.mark.negative
def test_unlisted_files_are_reported(tmp_path: Path) -> None:
    b = made(tmp_path)
    (b / "notes.txt").write_text("x", encoding="utf-8")
    stray = b"stray"
    (b / "artifacts" / sha256_hex(stray)).write_bytes(stray)
    report = verify_bundle(b)
    # A stray file changes no claim of the capture, so it is a warning that is always reported, not a failure.
    assert report["verified"] and issue_codes(report) == {"BUNDLE_UNLISTED_FILE"}
    assert len(report["issues"]) == 2 and {i["severity"] for i in report["issues"]} == {"warning"}


@pytest.mark.negative
def test_a_corrupted_or_missing_artifact_is_refused(tmp_path: Path) -> None:
    b = made(tmp_path)
    src = capture_json(b)["source"]["artifact"]
    path = b / "artifacts" / src
    data = bytearray(path.read_bytes())
    data[0] ^= 1
    path.write_bytes(bytes(data))
    assert "BUNDLE_ARTIFACT_CORRUPT" in issue_codes(verify_bundle(b))
    path.unlink()
    assert "BUNDLE_ARTIFACT_MISSING" in issue_codes(verify_bundle(b))
    assert extract_bundle(b, isolated=False)["status"] == "failed"


@pytest.mark.negative
@pytest.mark.parametrize(
    ("change", "code"),
    [
        (lambda c: c.pop("page"), "BUNDLE_SCHEMA_INVALID"),
        (lambda c: c.update(schema_version="9.0.0"), "BUNDLE_SCHEMA_INVALID"),
        (lambda c: c["page"].update(sha1="0" * 40), "BUNDLE_ARTIFACT_CORRUPT"),
        (lambda c: c["page"].update(revision_id=c["page"]["revision_id"] + 1), None),
        (lambda c: c["page"].update(page_id=c["page"]["page_id"] + 1), None),
        (lambda c: c["page"].update(title="Another title"), None),
        (lambda c: c["request"].update(wiki="fr"), None),
    ],
)
def test_a_tampered_capture_record_does_not_verify(tmp_path: Path, change: Any, code: str | None) -> None:
    b = made(tmp_path)
    rewrite_capture(b, change)
    report = verify_bundle(b)
    assert not report["verified"]
    if code is not None:
        assert code in issue_codes(report)
    assert extract_bundle(b, isolated=False)["status"] == "failed"


def tampered(doc: dict[str, Any], change: Any, *, redigest: bool = True) -> dict[str, Any]:
    out = json.loads(json.dumps(doc))
    change(out)
    if redigest:
        out["extraction_digest"] = digest({k: v for k, v in out.items() if k != "extraction_digest"})
    return out


@pytest.mark.negative
def test_tampered_extractions_are_refused_even_when_redigested(tmp_path: Path) -> None:
    b = made(tmp_path)
    doc = extract_bundle(b, isolated=False)

    def shift_anchor(d: dict[str, Any]) -> None:
        d["identifiers"][0]["source"]["cp_start"] += 1

    def forge_raw(d: dict[str, Any]) -> None:
        d["identifiers"][0]["source"]["raw"] = "10.9999/forged"

    def move_locator(d: dict[str, Any]) -> None:
        loc = d["uses"][1]["render"]["locator"]
        loc["path"] = d["uses"][0]["render"]["locator"]["path"]

    def other_capture(d: dict[str, Any]) -> None:
        d["capture"]["capture_sha256"] = "0" * 64

    for change, code in (
        (shift_anchor, "ANCHOR_MISMATCH"),
        (forge_raw, "ANCHOR_MISMATCH"),
        (move_locator, "LOCATOR_MISMATCH"),
        (other_capture, "BUNDLE_DIGEST_MISMATCH"),
    ):
        report = verify_bundle(b, tampered(doc, change))
        assert not report["verified"] and code in issue_codes(report), (change.__name__, issue_codes(report))
    unsigned = tampered(doc, lambda d: d["accounting"].update(), redigest=False)
    unsigned["status"] = "partial" if doc["status"] == "complete" else "complete"
    assert "BUNDLE_DIGEST_MISMATCH" in issue_codes(verify_bundle(b, unsigned))


@pytest.mark.negative
def test_extraction_file_with_duplicate_keys_is_malformed(tmp_path: Path) -> None:
    b = made(tmp_path)
    path = tmp_path / "x.json"
    path.write_text('{"schema": "a", "schema": "b"}', encoding="utf-8")
    report = verify_bundle(b, path)
    assert not report["verified"] and "BUNDLE_MALFORMED" in issue_codes(report)


# ------------------------------------------------------------------------------------------------ replay


@pytest.mark.reproducibility
def test_replay_reproduces_the_recorded_extraction(tmp_path: Path) -> None:
    b = made(tmp_path)
    doc = extract_bundle(b)
    report = replay_bundle(b, None, doc)
    assert report["verified"] and report["replay"]["state"] == "reproduced"
    assert report["replay"]["new_digest"] == doc["extraction_digest"]


@pytest.mark.reproducibility
def test_extraction_is_byte_identical_in_process_and_isolated(tmp_path: Path) -> None:
    b = made(tmp_path)
    assert canonical_bytes(extract_bundle(b, isolated=False)) == canonical_bytes(extract_bundle(b))


@pytest.mark.negative
def test_replay_refuses_forged_mismatched_and_foreign_records(tmp_path: Path) -> None:
    b = made(tmp_path)
    doc = extract_bundle(b, isolated=False)
    forged = tampered(doc, lambda d: d["identifiers"][0]["normalization"].update(normalized="10.1/x"), redigest=False)
    report = replay_bundle(b, None, forged)
    assert report["replay"]["state"] != "reproduced" and "BUNDLE_DIGEST_MISMATCH" in issue_codes(report)
    resigned = tampered(doc, lambda d: d["identifiers"][0]["normalization"].update(normalized="10.1/x"))
    report = replay_bundle(b, None, resigned)
    assert report["replay"]["state"] == "differs" and "REPLAY_DIFFERS" in issue_codes(report)
    report = replay_bundle(b, ExtractConfig(max_depth=59), doc)
    assert report["replay"]["state"] == "not_compared" and "REPLAY_CONFIG_MISMATCH" in issue_codes(report)
    old = tampered(doc, lambda d: d["extractor"].update(version="0.0.1"))
    report = replay_bundle(b, None, old)
    assert report["replay"]["state"] == "not_compared" and "REPLAY_IDENTITY_MISMATCH" in issue_codes(report)
    other = bundle(tmp_path, TEXT.replace("Beta", "Gamma"), BODY.replace("Beta", "Gamma"), name="other")
    report = replay_bundle(other, None, doc)
    assert report["replay"]["state"] == "differs"


# ------------------------------------------------------------------------------------------- isolation


@pytest.mark.security
def test_the_worker_refuses_every_network_connection() -> None:
    code = (
        "from citerift.wiki.worker import forbid_network; forbid_network(); import socket\n"
        "for call in (lambda: socket.create_connection(('127.0.0.1', 9)), lambda: socket.getaddrinfo('x', 1),\n"
        "             lambda: socket.socket().connect(('127.0.0.1', 9))):\n"
        "    try:\n        call()\n    except PermissionError:\n        print('refused')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True, timeout=60)
    assert out.stdout.split() == ["refused"] * 3


@pytest.mark.security
def test_the_worker_has_no_inherited_environment(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    (tmp_path / "citerift").mkdir()
    (tmp_path / "citerift" / "__init__.py").write_text("raise SystemExit('shadowed')\n", encoding="utf-8")
    b = made(tmp_path)
    doc = extract_bundle(b)
    assert doc["status"] == "complete"


@pytest.mark.security
def test_the_wall_deadline_kills_the_worker(tmp_path: Path) -> None:
    b = made(tmp_path)
    doc = extract_bundle(b, ExtractConfig(worker_wall_s=0.001))
    assert doc["status"] == "failed" and {i["code"] for i in doc["issues"]} == {"EXTRACTION_DEADLINE_EXCEEDED"}
    assert verify_bundle(b, doc)["verified"]  # a failure document is itself a valid, verifiable document


@pytest.mark.security
def test_the_memory_limit_ends_in_a_stable_failure(tmp_path: Path) -> None:
    text = "".join(
        f'P{i}.<ref name="n{i}">{{{{cite journal |title=T{i} |doi=10.1234/x{i}}}}}</ref>\n' for i in range(3000)
    )
    b = bundle(tmp_path, text)
    doc = extract_bundle(b, ExtractConfig(worker_memory_mib=64))
    assert doc["status"] == "failed" and {i["code"] for i in doc["issues"]} == {"EXTRACTION_MEMORY_EXCEEDED"}
    assert verify_bundle(b, doc)["verified"]


@pytest.mark.negative
@pytest.mark.parametrize(
    ("config", "code"),
    [
        (ExtractConfig(max_depth=1), "LIMIT_DEPTH"),
        (ExtractConfig(max_refs=1), "LIMIT_OCCURRENCES"),
        (ExtractConfig(max_templates=1), "LIMIT_OCCURRENCES"),
        (ExtractConfig(max_nodes=5), "LIMIT_NODES"),
    ],
)
def test_structural_limits_fail_closed_with_their_code(tmp_path: Path, config: ExtractConfig, code: str) -> None:
    text = TEXT + "{{a|{{b|{{c|x}}}}}}<ref>{{cite web |url=https://doi.org/10.1/x}}</ref>\n"
    b = bundle(tmp_path, text)
    doc = extract_bundle(b, config, isolated=False)
    assert doc["status"] == "failed" and code in {i["code"] for i in doc["issues"]}, doc["issues"]
    assert doc["identifiers"] == [] and verify_bundle(b, doc)["verified"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "values",
    [
        {"worker_wall_s": 0},
        {"worker_wall_s": True},
        {"worker_wall_s": 3601},
        {"worker_memory_mib": 63},
        {"max_nodes": 0},
        {"max_refs": 1.5},
        {"max_candidates": "9"},
    ],
)
def test_invalid_configurations_are_refused(values: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="not allowed"):
        ExtractConfig(**values)
    with pytest.raises(ValueError, match="unknown configuration keys"):
        ExtractConfig.from_json({"max_nodes": 5, "bogus": 1})
