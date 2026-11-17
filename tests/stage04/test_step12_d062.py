"""Stage 04 Step 12: the canonical Stage 02 index identity of owner decision D-062.

The identity LOOKUP records and the controller keys on is Stage 02's content identity (snapshot id, policy version,
lookup schema version, ``artifact_digest``, ``semantic_digest``, ``export_lines``), accepted only after Stage 02's own
checks prove it from the content. These tests show:

- two independent builds of the same source, and a byte-different but canonically equal copy, have one identity and
  give the same investigation content (equivalent rebuild);
- each tampering case fails closed (``INDEX_CORRUPT``), including content changed with consistent forged metadata;
- the process-local verification cache never changes a result: cache-disabled runs are identical, and any change of the
  file (in place, size-preserving, or a replaced inode) is verified again;
- a canonically different index is STALE for a committed investigation, and an unverifiable one is refused, not STALE.

Inputs: the attributed Retraction Watch subset of ``step8_support`` and the VS-2 design bundle; DETECT is the
SYNTHETIC test detector of ``step8_support`` (not dt-1). Offline.
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8

from citerift.investigation.adapters import Failed, StepRequest
from citerift.investigation.adapters import lookup as L
from citerift.investigation.adapters.plan import Integration
from citerift.investigation.controller import IdentityUnavailable
from citerift.investigation.memory import InvestigationMemory
from citerift.investigation.operations import readonly_request
from citerift.retraction import export
from citerift.retraction.query import Index
from citerift.retraction.store import manifest_path_for

pytestmark = pytest.mark.integration


def copy_index(index: Path, to: Path) -> Path:
    """The index and its build manifest at ``to`` (a new directory)."""
    to.mkdir(parents=True, exist_ok=True)
    out = to / index.name
    shutil.copyfile(index, out)
    shutil.copyfile(manifest_path_for(index), manifest_path_for(out))
    return out


def sql(index: Path, *statements: str) -> None:
    conn = sqlite3.connect(index, isolation_level=None)
    try:
        for s in statements:
            conn.execute(s)
    finally:
        conn.close()


def identity(index: Path, **kw: Any) -> dict[str, Any]:
    return L.IndexVerifier(enabled=False, **kw).identity(index)


def refused(index: Path) -> str:
    with pytest.raises(L.IndexNotVerified) as exc:
        identity(index)
    assert exc.value.code == "INDEX_CORRUPT"
    return exc.value.detail


@pytest.fixture(scope="module")
def offline() -> Any:
    with pytest.MonkeyPatch.context() as mp:
        yield S8.NoNetwork(mp)


@pytest.fixture(scope="module")
def builds(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Two independent Stage 02 builds of the same source, in two directories."""
    return (
        S8.build_index(tmp_path_factory.mktemp("build-a")),
        S8.build_index(tmp_path_factory.mktemp("build-b")),
    )


@pytest.fixture
def index(tmp_path: Path, builds: tuple[Path, Path]) -> Path:
    """A private copy of build A that a test may change."""
    return copy_index(builds[0], tmp_path / "idx")


# Identity and equivalent rebuild ----------------------------------------------------------------------------------


def test_the_identity_is_the_canonical_stage02_identity(builds: tuple[Path, Path]) -> None:
    ident = identity(builds[0])
    with Index(builds[0]) as idx:
        digests = export.compute_digests(idx.conn)
        meta = dict(idx.conn.execute("SELECT key, value FROM meta").fetchall())
        snapshot = idx.snapshot_id
    assert set(ident) == {
        "snapshot_id",
        "policy_version",
        "lookup_schema_version",
        "artifact_digest",
        "semantic_digest",
        "export_lines",
    }
    assert ident["snapshot_id"] == snapshot
    assert ident["artifact_digest"] == digests["artifact_digest"] == meta["artifact_digest"]
    assert ident["semantic_digest"] == digests["semantic_digest"] == meta["semantic_digest"]
    assert ident["export_lines"] == int(digests["export_lines"])
    assert "sha256" not in json.dumps(ident) and "index_sha256" not in ident


def test_two_independent_builds_have_one_identity(builds: tuple[Path, Path]) -> None:
    assert identity(builds[0]) == identity(builds[1])
    full = []
    for b in builds:  # Stage 02's complete verify (with the event JSON-Schema pass) agrees on both builds
        with Index(b) as ix:
            report = export.verify(ix.conn, manifest_path=manifest_path_for(b))
        assert report["ok"], report["problems"]
        full.append(dict(report["digests"]))
    assert full[0] == full[1]
    assert {k: identity(builds[0])[k] for k in ("artifact_digest", "semantic_digest")} == {
        k: full[0][k] for k in ("artifact_digest", "semantic_digest")
    }


def test_a_byte_different_equal_index_has_the_same_identity(tmp_path: Path, builds: tuple[Path, Path]) -> None:
    """Rewritten with another page size and VACUUM: other bytes, same Stage 02 content, same identity."""
    copy = copy_index(builds[0], tmp_path / "vac")
    sql(copy, "PRAGMA journal_mode=DELETE", "PRAGMA page_size=8192", "VACUUM")
    assert L.file_sha256(copy) != L.file_sha256(builds[0])
    assert identity(copy) == identity(builds[0])


def _content(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    recs, _ = S8.committed(root, payload)
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        cj = mem.view.content_digest()
    return {
        "kinds": [r["kind"] for r in recs],
        "observations": sorted(r["payload"]["blob"] for r in recs if r["kind"] == "observation_recorded"),
        "claims": sorted(r["payload"]["claim_id"] for r in recs if r["kind"] == "claim_recorded"),
        "questions": sorted(r["payload"]["claim_id"] for r in recs if r["kind"] == "question_opened"),
        "decisions": sorted(r["payload"]["decision_id"] for r in recs if r["kind"] == "decision_recorded"),
        "report": [r["payload"] for r in recs if r["kind"] == "report_recorded"],
        "content_digest": cj,
    }


def _investigate(tmp: Path, index: Path, integration: Integration) -> dict[str, Any]:
    root = S8.memory_root(tmp)
    payload = S8.create(root, S8.request(S8.AR_OBOKATA, index, root))
    assert S8.run(root, payload, integration).status == "NEEDS_RESOLUTION"
    return _content(root, payload)


def test_equivalent_rebuilds_give_the_same_investigation_content(
    tmp_path: Path, builds: tuple[Path, Path], offline: Any
) -> None:
    """The investigation key and C(J) do not depend on which equal build was read, nor on the verification cache."""
    vac = copy_index(builds[1], tmp_path / "vac")
    sql(vac, "PRAGMA journal_mode=DELETE", "PRAGMA page_size=8192", "VACUUM")
    a = _investigate(tmp_path / "a", builds[0], S8.TEST_INTEGRATION)
    b = _investigate(tmp_path / "b", builds[1], Integration(detector=S8.synthetic_detector))
    c = _investigate(
        tmp_path / "c", vac, Integration(detector=S8.synthetic_detector, index_verifier=L.IndexVerifier(enabled=False))
    )
    assert a == b == c
    assert offline.attempts == []


# Tampering fails closed -------------------------------------------------------------------------------------------


def test_a_modified_event_is_refused(index: Path) -> None:
    sql(index, "UPDATE event SET title = title || ' (edited)' WHERE event_id = (SELECT min(event_id) FROM event)")
    assert "DIGEST_MISMATCH: artifact_digest" in refused(index)


def test_a_modified_raw_record_is_refused(index: Path) -> None:
    sql(
        index,
        "UPDATE raw_record SET record_id = record_id || '0' WHERE ordinal = (SELECT min(ordinal) FROM raw_record)",
    )
    assert "DIGEST_MISMATCH" in refused(index)


def test_a_modified_derived_table_is_refused(index: Path) -> None:
    """The identifier table is derived (not in the artifact digest): only the derivation check can see this."""
    sql(index, "UPDATE ident SET norm = '10.9999/forged' WHERE id = (SELECT min(id) FROM ident WHERE norm IS NOT NULL)")
    detail = refused(index)
    assert "DIGEST_MISMATCH" not in detail


@pytest.mark.parametrize("key", ["artifact_digest", "semantic_digest"])
def test_a_forged_stored_digest_is_refused(index: Path, key: str) -> None:
    sql(index, f"UPDATE meta SET value = '{'0' * 64}' WHERE key = '{key}'")  # noqa: S608 - fixed keys
    assert f"DIGEST_MISMATCH: {key}" in refused(index)


def test_a_manifest_that_does_not_match_is_refused(index: Path) -> None:
    path = manifest_path_for(index)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["digests"]["artifact_digest"] = "0" * 64
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert "MANIFEST_MISMATCH: artifact_digest" in refused(index)


def test_a_missing_manifest_is_refused(index: Path) -> None:
    manifest_path_for(index).unlink()
    assert "MANIFEST_MISSING" in refused(index)


def test_changed_content_with_consistent_forged_metadata_is_refused(index: Path) -> None:
    """An event changed, and the stored digests and the manifest rewritten to the recomputed values: the digests then
    agree, so only the derivation of the events from the raw records refuses it. Metadata alone is never trusted."""
    sql(index, "UPDATE event SET title = title || ' (edited)' WHERE event_id = (SELECT min(event_id) FROM event)")
    conn = sqlite3.connect(index, isolation_level=None)
    try:
        digests = export.compute_digests(conn)
        for key, value in digests.items():
            conn.execute("UPDATE meta SET value = ? WHERE key = ?", (value, key))
    finally:
        conn.close()
    path = manifest_path_for(index)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["digests"].update(digests)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    detail = refused(index)
    assert "DIGEST_MISMATCH" not in detail and "MANIFEST_MISMATCH" not in detail


def _lookup_request(tmp: Path, index: Path) -> tuple[StepRequest, InvestigationMemory]:
    """The LOOKUP request of an investigation run up to NORMALIZE, keyed with the index identity."""
    root = S8.memory_root(tmp)
    payload = S8.create(root, S8.request(S8.AR_OBOKATA, index, root))
    S8.run_until(root, payload, S8.TEST_INTEGRATION, "NORMALIZE")
    mem = InvestigationMemory.open(root, payload["investigation_key"], writable=False)
    req = dataclasses.replace(readonly_request(mem, "LOOKUP"), identities={"index": identity(index)})
    return req, mem


def test_a_file_replaced_during_the_lookup_fails_closed(tmp_path: Path, index: Path, offline: Any) -> None:
    other = copy_index(index, tmp_path / "other")
    sql(other, "UPDATE event SET title = title || ' (edited)' WHERE event_id = (SELECT min(event_id) FROM event)")
    verifier = L.IndexVerifier()

    def replacing(path: Path) -> Index:
        opened = Index(path)
        os.replace(other, path)  # the path now names other content; the open handle still reads the old file
        return opened

    req, mem = _lookup_request(tmp_path, index)
    with mem:
        result = L.make_lookup(replacing, verifier)(req)
    assert isinstance(result, Failed) and result.code == "INDEX_CORRUPT"
    # The replaced file was never accepted under the old identity: it verifies again, and is refused.
    with pytest.raises(L.IndexNotVerified):
        verifier.identity(index)


def test_b01_lookup_refuses_an_index_other_than_the_one_it_was_keyed_with(
    tmp_path: Path, index: Path, offline: Any
) -> None:
    """Step 12, B-01: the identity LOOKUP verifies must be the identity its step key was computed from; a verified
    index of another canonical content at the path (changed between keying and the step) fails closed."""
    req, mem = _lookup_request(tmp_path, index)
    with mem:
        assert not isinstance(L.make_lookup()(req), Failed)
        other = S8.build_index(tmp_path / "other", S8.RW_FEWER)
        keyed_elsewhere = dataclasses.replace(req, identities={"index": identity(other)})
        result = L.make_lookup()(keyed_elsewhere)
    assert isinstance(result, Failed) and result.code == "INDEX_CORRUPT"
    assert result.detail == "the index identity changed after the step was keyed"


def test_a_change_after_verification_is_verified_again(index: Path) -> None:
    verifier = L.IndexVerifier()
    first = verifier.identity(index)
    assert verifier.identity(index) == first and verifier.verifications == 1
    sql(index, "UPDATE meta SET value = '" + "0" * 64 + "' WHERE key = 'semantic_digest'")
    with pytest.raises(L.IndexNotVerified):
        verifier.identity(index)
    assert verifier.verifications == 2


def test_a_replaced_inode_with_the_same_size_and_times_is_verified_again(tmp_path: Path, index: Path) -> None:
    verifier = L.IndexVerifier()
    verifier.identity(index)
    st = os.stat(index)
    forged = copy_index(index, tmp_path / "forged")
    sql(
        forged, "PRAGMA journal_mode=DELETE", "UPDATE meta SET value = '" + "0" * 64 + "' WHERE key = 'artifact_digest'"
    )
    assert os.stat(forged).st_size == st.st_size
    os.utime(forged, ns=(st.st_atime_ns, st.st_mtime_ns))
    os.replace(forged, index)
    with pytest.raises(L.IndexNotVerified):
        verifier.identity(index)
    assert verifier.verifications == 2


def test_a_size_preserving_in_place_change_with_restored_mtime_is_verified_again(index: Path) -> None:
    verifier = L.IndexVerifier()
    verifier.identity(index)
    st = os.stat(index)
    sql(index, "PRAGMA journal_mode=DELETE", "UPDATE meta SET value = '" + "0" * 64 + "' WHERE key = 'artifact_digest'")
    os.utime(index, ns=(st.st_atime_ns, st.st_mtime_ns))
    after = os.stat(index)
    assert (after.st_ino, after.st_size, after.st_mtime_ns) == (st.st_ino, st.st_size, st.st_mtime_ns)
    with pytest.raises(L.IndexNotVerified):
        verifier.identity(index)
    assert verifier.verifications == 2


def test_failures_are_never_cached(index: Path) -> None:
    manifest = manifest_path_for(index)
    saved = manifest.read_bytes()
    manifest.unlink()
    verifier = L.IndexVerifier()
    with pytest.raises(L.IndexNotVerified):
        verifier.identity(index)
    manifest.write_bytes(saved)
    assert verifier.identity(index) == identity(index)
    assert verifier.verifications == 2


def test_cache_disabled_and_enabled_give_identical_identities(builds: tuple[Path, Path]) -> None:
    on, off = L.IndexVerifier(), L.IndexVerifier(enabled=False)
    for _ in range(3):
        assert on.identity(builds[0]) == off.identity(builds[0])
    assert (on.verifications, off.verifications) == (1, 3)


def test_the_cache_is_per_verifier(builds: tuple[Path, Path]) -> None:
    a, b = L.IndexVerifier(), L.IndexVerifier()
    a.identity(builds[0])
    b.identity(builds[0])
    assert (a.verifications, b.verifications) == (1, 1)
    assert Integration().index_verifier is not Integration().index_verifier


# Staleness ---------------------------------------------------------------------------------------------------------


def _stale_changed(root: Path, payload: dict[str, Any]) -> list[str]:
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        [stale] = [r["payload"] for r in mem.view.records if r["kind"] == "stale_detected"]
    return list(stale["changed"])


def test_a_canonically_different_index_is_stale(tmp_path: Path, index: Path, offline: Any) -> None:
    root = S8.memory_root(tmp_path / "m")
    payload = S8.create(root, S8.request(S8.AR_OBOKATA, index, root))
    S8.run_until(root, payload, S8.TEST_INTEGRATION, "LOOKUP")
    other = S8.build_index(tmp_path / "other", S8.RW_FEWER)
    assert identity(other)["artifact_digest"] != identity(index)["artifact_digest"]
    shutil.copyfile(other, index)
    shutil.copyfile(manifest_path_for(other), manifest_path_for(index))
    assert S8.run(root, payload, Integration(detector=S8.synthetic_detector)).status == "STALE"
    assert _stale_changed(root, payload) == ["index"]


def test_an_equal_rebuild_at_the_path_is_not_stale(tmp_path: Path, builds: tuple[Path, Path], offline: Any) -> None:
    index = copy_index(builds[0], tmp_path / "idx")
    root = S8.memory_root(tmp_path / "m")
    payload = S8.create(root, S8.request(S8.AR_OBOKATA, index, root))
    S8.run_until(root, payload, S8.TEST_INTEGRATION, "LOOKUP")
    shutil.copyfile(builds[1], index)
    shutil.copyfile(manifest_path_for(builds[1]), manifest_path_for(index))
    assert S8.run(root, payload, Integration(detector=S8.synthetic_detector)).status == "NEEDS_RESOLUTION"


def test_a_tampered_index_is_refused_not_stale(tmp_path: Path, index: Path, offline: Any) -> None:
    """MM 10.2: an identity that cannot be established is not a new identity. The run stops without a STALE record."""
    root = S8.memory_root(tmp_path / "m")
    payload = S8.create(root, S8.request(S8.AR_OBOKATA, index, root))
    S8.run_until(root, payload, S8.TEST_INTEGRATION, "LOOKUP")
    sql(index, "UPDATE meta SET value = '" + "0" * 64 + "' WHERE key = 'artifact_digest'")
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        before = len(mem.view.records)
    with pytest.raises(IdentityUnavailable) as exc:
        S8.run(root, payload, Integration(detector=S8.synthetic_detector))
    assert (exc.value.name, exc.value.unavailable_code) == ("index", "INDEX_CORRUPT")
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        assert len(mem.view.records) == before
