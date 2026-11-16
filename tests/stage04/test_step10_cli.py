"""Step 10: ``citerift-investigate`` contract tests (owner Step 10 items 16 to 23, 26, 27).

Every exit code of the one table (``operations.EXIT``) is produced by a real command on a real investigation, in text
and JSON. Investigations are of the previously exposed design bundles (VS-1..VS-3, VS-4) and run with every socket
refused; BLOCKED uses a deferring live-ACQUIRE stand-in (no network, labeled), and the busy case holds the
investigation lock from this process.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8
import step10_support as T

from citerift.investigation import cli
from citerift.investigation import operations as ops
from citerift.investigation.adapters import Deferred, StepRequest
from citerift.investigation.adapters.plan import Integration
from citerift.investigation.memory import InvestigationMemory

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


@pytest.fixture(scope="module")
def en(tmp_path_factory: pytest.TempPathFactory, index: Path) -> T.Inv:
    return T.Inv(tmp_path_factory.mktemp("en"), S8.EN_OBOKATA, index)


@pytest.fixture(scope="module")
def ar(tmp_path_factory: pytest.TempPathFactory, index: Path) -> T.Inv:
    return T.Inv(tmp_path_factory.mktemp("ar"), S8.AR_OBOKATA, index)


@pytest.fixture(scope="module")
def mmr(tmp_path_factory: pytest.TempPathFactory, index: Path) -> T.Inv:
    return T.Inv(tmp_path_factory.mktemp("mmr"), S8.EN_MMR, index)


def _key_args(inv: T.Inv) -> list[str | Path]:
    return ["--memory-root", inv.root, "--key", inv.key]


# The exit-code table ---------------------------------------------------------------------------------------------


def test_the_table_is_one_mapping_with_distinct_codes() -> None:
    assert len(set(ops.EXIT.values())) == len(ops.EXIT)
    assert ops.EXIT == {
        "completed": 0, "internal": 1, "usage": 2, "invalid": 3, "not_found": 4, "verify_failed": 5, "partial": 6,
        "blocked": 8, "failed": 9, "needs_resolution": 10, "stale": 11, "corrupt": 12, "busy": 13, "incomplete": 14,
    }  # fmt: skip
    # The documented table in the command's help text is the same table.
    for status, code in ops.EXIT.items():
        assert f"{code:<4}  {status}" in (cli.__doc__ or ""), status


def test_exit_0_completed(en: T.Inv) -> None:
    assert en.code == 0 and en.out["status"] == "completed"
    for command in ("show", "verify", "replay"):
        code, value = T.run_json(command, *_key_args(en))
        assert (code, value["status"]) == (0, "completed"), command
    code, value = T.run_json("verify", *_key_args(en))
    assert value["result"]["result"] == "passed"
    assert all(c["passed"] for c in value["result"]["checks"])
    names = [c["check"] for c in value["result"]["checks"]]
    assert {"D054_REPORT_GRAPH", "V1_PROJECTIONS", "MEMORY_OPEN", "INPUT_IDENTITIES_CURRENT"} <= set(names)


def test_exit_1_internal_error_exports_nothing(en: T.Inv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("a defect")

    monkeypatch.setattr(ops.exporter, "write", boom)
    code, out, err = T.run_cli("export", *_key_args(en), "--out", tmp_path / "x")
    assert code == 1 and out == "" and "internal error: RuntimeError: a defect" in err
    assert not (tmp_path / "x").exists()


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["frobnicate"],
        ["show", "--memory-root", "/no/such/root"],
        ["show", "--memory-root", "/no/such/root", "--key", "ABC"],
        ["show", "--memory-root", "/no/such/root", "--key", "0" * 63],
        ["run", "--wiki", "en", "--revision", "0", "--index", "/i", "--memory-root", "/m"],
        ["run", "--wiki", "fr", "--revision", "1", "--index", "/i", "--memory-root", "/m"],
        ["run", "--bundle", "/b", "--wiki", "en"],
        ["verify", "--memory-root", "/no/such/root", "--key", "0" * 64, "--format", "yaml"],
    ],
)
def test_exit_2_usage(argv: list[str]) -> None:
    code, out, err = T.run_cli(*argv)
    assert code == 2 and out == "" and "usage:" in err


@pytest.mark.parametrize(
    "extra",
    [
        ["--wiki", "en"],  # --wiki needs --revision
        ["--bundle", "/b", "--revision", "3"],  # --revision belongs to --wiki
    ],
)
def test_exit_2_usage_after_parsing(extra: list[str], tmp_path: Path) -> None:
    code, value = T.run_json("run", *extra, "--index", tmp_path / "i", "--memory-root", tmp_path / "m")
    assert code == 2 and value["error"]["code"] == "USAGE"


def test_exit_2_request_excludes_other_inputs(tmp_path: Path) -> None:
    code, value = T.run_json("run", "--request", tmp_path / "r.json", "--memory-root", tmp_path)
    assert code == 2 and value["error"]["code"] == "USAGE"


@pytest.mark.parametrize(
    ("content", "error"),
    [
        (b"{not json", "REQUEST_INVALID"),
        (b'{"a": 1, "a": 2}', "REQUEST_INVALID"),  # duplicate key
        (b"[]", "REQUEST_INVALID"),
        (b'{"schema": "urn:citerift:schema:investigation:v1:request"}', "REQUEST_INVALID"),
        (b" " * (ops.MAX_REQUEST_BYTES + 1), "REQUEST_INVALID"),
    ],
)
def test_exit_3_invalid_request(tmp_path: Path, content: bytes, error: str) -> None:
    path = tmp_path / "request.json"
    path.write_bytes(content)
    code, value = T.run_json("run", "--request", path)
    assert code == 3 and value["error"]["code"] == error
    assert not list(tmp_path.glob("*/journal.jsonl"))


def test_exit_3_request_variants(tmp_path: Path, index: Path) -> None:
    root = S8.memory_root(tmp_path)
    good = ops.retained_request(S8.EN_OBOKATA, index, root)
    variants = {
        "relative memory root": {**good, "memory_root": "memory"},
        "retained bundle with a fetch policy": {**good, "config": {**good["config"], "fetch_policy_sha256": "a" * 64}},
        "live capture with another policy": {
            **ops.live_request("en", 1, index, root),
            "config": {**ops.live_request("en", 1, index, root)["config"], "fetch_policy_sha256": "b" * 64},
        },
        "missing bundle": {**good, "subject": {**good["subject"], "bundle_path": str(tmp_path / "none")}},
    }
    for name, request in variants.items():
        path = tmp_path / "request.json"
        path.write_text(json.dumps(request), encoding="utf-8")
        code, value = T.run_json("run", "--request", path)
        assert code == 3, (name, value)
    assert os.listdir(root) == []  # nothing was created


@pytest.mark.parametrize("damage", ["missing", "capture.json truncated", "artifact changed", "revision id changed"])
def test_missing_or_corrupt_bundle_fails_closed(tmp_path: Path, index: Path, damage: str) -> None:
    """A bundle Stage 03 cannot open is invalid input (nothing is created); one it opens but whose content does not
    verify fails ACQUIRE terminally. Neither has a claim, a report or an export."""
    bundle = tmp_path / "bundle"
    if damage != "missing":
        shutil.copytree(S8.EN_OBOKATA, bundle)
    capture = bundle / "capture.json"
    if damage == "capture.json truncated":
        capture.write_bytes(capture.read_bytes()[:200])
    elif damage == "artifact changed":
        T.flip(sorted((bundle / "artifacts").iterdir())[0])
    elif damage == "revision id changed":
        data = capture.read_bytes()
        assert data.count(b'"revision_id": 1372543632') == 2  # the page record and the request
        capture.write_bytes(data.replace(b'"revision_id": 1372543632', b'"revision_id": 1372543633'))
    root = S8.memory_root(tmp_path)
    with T.offline():
        code, value = T.run_json("run", "--bundle", bundle, "--index", index, "--memory-root", root)
    if damage in ("missing", "capture.json truncated"):
        assert code == 3 and value["error"]["code"] == "BUNDLE_UNREADABLE"
        assert os.listdir(root) == []
        return
    assert code == 9 and value["result"]["report"] is None
    assert value["result"]["terminated_by"]["step"] in ("VALIDATE", "ACQUIRE")
    key = value["result"]["investigation_key"]
    assert not [r for r in T.journal(root, key) if r["kind"] in ("claim_recorded", "report_recorded")]
    code, _ = T.run_json("export", "--memory-root", root, "--key", key, "--out", tmp_path / "x")
    assert code == 9 and not (tmp_path / "x").exists()


def test_exit_4_not_found(tmp_path: Path) -> None:
    root = S8.memory_root(tmp_path)
    for command in ("show", "verify", "replay", "resume", "checkpoint"):
        code, value = T.run_json(command, "--memory-root", root, "--key", "a" * 64)
        assert code == 4 and value["error"]["code"] == "INVESTIGATION_NOT_FOUND", command
    code, value = T.run_json("export", "--memory-root", root, "--key", "a" * 64, "--out", tmp_path / "x")
    assert code == 4 and not (tmp_path / "x").exists()


def test_exit_5_checkpoint_mismatch(en: T.Inv, tmp_path: Path) -> None:
    cp = tmp_path / "cp.json"
    assert T.run_cli("checkpoint", *_key_args(en), "--out", cp)[0] == 0
    value = json.loads(cp.read_bytes())
    value["journal_digest"] = "0" * 64
    cp.write_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n")
    code, out = T.run_json("verify", *_key_args(en), "--checkpoint", cp)
    assert code == 5 and out["result"]["result"] == "failed"
    assert out["result"]["checkpoint"]["result"] == "CHECKPOINT_PREFIX_REWRITTEN"


def test_exit_6_partial(mmr: T.Inv) -> None:
    assert mmr.code == 6 and mmr.out["report"]["outcome"] == "partial"
    code, value = T.run_json("verify", *_key_args(mmr))
    assert (code, value["result"]["result"]) == (6, "passed")


class _Deferring:
    """A stand-in for live ACQUIRE that defers (as Stage 03 does on Retry-After) and never touches the network."""

    def __init__(self, not_before: datetime) -> None:
        self.not_before, self.calls = not_before, 0

    def __call__(self, req: StepRequest) -> Deferred:
        self.calls += 1
        return Deferred(not_before=self.not_before)


def test_exit_8_blocked_is_reported_without_waiting(
    tmp_path: Path, index: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    later = datetime.now(UTC) + timedelta(hours=1)
    fake = _Deferring(later)
    monkeypatch.setattr(ops, "integration_for", lambda request: Integration(live=fake))
    root = S8.memory_root(tmp_path)
    with T.offline():
        code, value = T.run_json("run", "--wiki", "en", "--revision", "1372543632", "--index", index,
                                 "--memory-root", root)  # fmt: skip
    assert code == 8 and fake.calls == 1
    res = value["result"]
    acquire = next(s for s in res["steps"] if s["step"] == "ACQUIRE")
    assert acquire["state"] == "deferred" and acquire["not_before"].startswith(later.strftime("%Y-%m-%dT%H:%M"))
    assert res["next"]["action"] == "wait" and res["next"]["rule"] == "T-RESTART"
    key = res["investigation_key"]
    before = (root / key / "journal.jsonl").read_bytes()
    with T.offline():
        code, value = T.run_json("resume", "--memory-root", root, "--key", key)
    assert code == 8 and fake.calls == 1  # not restarted before not_before, and nothing slept
    assert (root / key / "journal.jsonl").read_bytes() == before
    code, _ = T.run_json("export", "--memory-root", root, "--key", key, "--out", tmp_path / "x")
    assert code == 8 and not (tmp_path / "x").exists()


def test_exit_9_failed(tmp_path: Path) -> None:
    root = S8.memory_root(tmp_path)
    with T.offline():
        code, value = T.run_json("run", "--bundle", S8.EN_OBOKATA, "--index", tmp_path / "missing.sqlite",
                                 "--memory-root", root)  # fmt: skip
    assert code == 9
    t = value["result"]["terminated_by"]
    assert (t["step"], t["code"], t["reason"]) == ("VALIDATE", "INPUT_INVALID", "INDEX_PATH_INVALID")
    key = value["result"]["investigation_key"]
    code, out = T.run_json("verify", "--memory-root", root, "--key", key)
    assert code == 9 and out["result"]["result"] == "failed"
    code, out = T.run_json("export", "--memory-root", root, "--key", key, "--out", tmp_path / "x")
    assert code == 9 and out["error"]["code"] == "EXPORT_REFUSED" and not (tmp_path / "x").exists()
    code, out = T.run_json("replay", "--memory-root", root, "--key", key)
    assert code == 9 and out["error"]["code"] == "NOT_REPLAYABLE"


def test_exit_10_needs_resolution(ar: T.Inv) -> None:
    assert ar.code == 10 and ar.out["lifecycle"] == "NEEDS_RESOLUTION"
    for command in ("show", "verify", "replay"):
        code, value = T.run_json(command, *_key_args(ar))
        assert code == 10, command
    code, value = T.run_json("verify", *_key_args(ar))
    assert value["result"]["result"] == "passed"


def test_exit_11_stale_after_the_index_changed(tmp_path: Path) -> None:
    index = S8.build_index(tmp_path / "rw")
    inv = T.Inv(tmp_path / "inv", S8.EN_OBOKATA, index)
    assert inv.code == 0
    with open(index, "ab") as f:
        f.write(b"\0")
    code, value = T.run_json("verify", *_key_args(inv))
    assert code == 11 and value["result"]["result"] == "stale" and value["result"]["stale"]["changed"] == ["index"]
    code, value = T.run_json("replay", *_key_args(inv))
    assert code == 11 and value["result"] == {**value["result"], "result": "stale", "changed": ["index"]}
    code, value = T.run_json("export", *_key_args(inv), "--out", tmp_path / "x")
    assert code == 11 and not (tmp_path / "x").exists()


def test_exit_12_corrupt_blob(en: T.Inv, tmp_path: Path) -> None:
    inv = en.copy(tmp_path)
    T.flip(inv.dir / "blobs" / inv.report_record()["report"])
    for command in ("show", "verify", "replay", "resume", "checkpoint"):
        code, _ = T.run_json(command, *_key_args(inv))
        assert code == 12, command
    code, _value = T.run_json("export", *_key_args(inv), "--out", tmp_path / "x")
    assert code == 12 and not (tmp_path / "x").exists()


def test_exit_13_busy(en: T.Inv, tmp_path: Path) -> None:
    with InvestigationMemory.open(en.root, en.key, writable=False):
        for command in ("show", "verify", "replay", "resume", "checkpoint"):
            code, _value = T.run_json(command, *_key_args(en))
            assert code == 13, command
        code, _ = T.run_json("export", *_key_args(en), "--out", tmp_path / "x")
        assert code == 13 and not (tmp_path / "x").exists()
        with T.offline():
            code, _ = T.run_json("run", "--bundle", S8.EN_OBOKATA, "--index", Path(en.request["index_path"]),
                                 "--memory-root", en.root)  # fmt: skip
        assert code == 13


def test_exit_14_incomplete(tmp_path: Path, index: Path) -> None:
    root = S8.memory_root(tmp_path)
    payload = ops.created_for(ops.retained_request(S8.EN_OBOKATA, index, root))
    InvestigationMemory.create(root, payload).close()
    key = payload["investigation_key"]
    code, value = T.run_json("show", "--memory-root", root, "--key", key)
    assert code == 14 and value["result"]["lifecycle"] == "CREATED"
    assert value["result"]["next"]["rule"] == "T-START"
    code, value = T.run_json("verify", "--memory-root", root, "--key", key)
    assert code == 14 and value["result"]["result"] == "failed"
    code, value = T.run_json("export", "--memory-root", root, "--key", key, "--out", tmp_path / "x")
    assert code == 14 and not (tmp_path / "x").exists()
    with T.offline():  # resume runs it to its end, offline
        code, value = T.run_json("resume", "--memory-root", root, "--key", key)
    assert code == 0 and value["result"]["lifecycle"] == "COMPLETED"


# run, resume and output ------------------------------------------------------------------------------------------


def test_run_twice_reopens_the_same_investigation_and_does_not_rerun(en: T.Inv, index: Path) -> None:
    before = en.journal_bytes()
    with T.offline():
        code, value = T.run_json("run", "--bundle", S8.EN_OBOKATA, "--index", index, "--memory-root", en.root)
    assert code == 0 and value["result"]["investigation_key"] == en.key
    assert en.journal_bytes() == before
    assert os.listdir(en.root) == [en.key]
    with T.offline():
        code, _ = T.run_json("resume", *_key_args(en))
    assert code == 0 and en.journal_bytes() == before


def test_the_same_key_with_another_request_is_refused(en: T.Inv, index: Path, tmp_path: Path) -> None:
    """The key is the capture digest, plan and configuration (S-4.7): the same bundle at another path is the same
    key with another creation payload, which is refused and changes nothing. Another configuration is another key."""
    inv = en.copy(tmp_path)
    before = inv.journal_bytes()
    bundle = tmp_path / "bundle"
    shutil.copytree(S8.EN_OBOKATA, bundle)
    with T.offline():
        code, value = T.run_json("run", "--bundle", bundle, "--index", index, "--memory-root", inv.root)
    assert code == 3 and value["error"]["code"] == "INVESTIGATION_REQUEST_DIFFERS"
    assert inv.journal_bytes() == before and os.listdir(inv.root) == [inv.key]
    with T.offline():
        code, value = T.run_json("run", "--bundle", S8.EN_OBOKATA, "--index", index, "--memory-root", inv.root,
                                 "--lookup-budget", str(1 << 20))  # fmt: skip
    assert code == 0 and value["result"]["investigation_key"] != inv.key
    assert sorted(os.listdir(inv.root)) == sorted([inv.key, value["result"]["investigation_key"]])


def test_read_only_commands_write_nothing(ar: T.Inv) -> None:
    before = {p: p.read_bytes() for p in ar.dir.rglob("*") if p.is_file()}
    with T.offline():
        for command in ("show", "verify", "replay", "checkpoint"):
            T.run_cli(command, *_key_args(ar))
            T.run_cli(command, *_key_args(ar), "--format", "json")
    after = {p: p.read_bytes() for p in ar.dir.rglob("*") if p.is_file()}
    assert after == before


def test_text_and_json_carry_the_same_status(ar: T.Inv) -> None:
    for command in ("show", "verify", "replay"):
        code, text, _ = T.run_cli(command, *_key_args(ar))
        jcode, value = T.run_json(command, *_key_args(ar))
        assert code == jcode and text.startswith(f"{command}: {value['status']} (exit {code})")


def test_show_names_the_next_transition_and_its_rule(ar: T.Inv, en: T.Inv) -> None:
    for inv in (ar, en):
        _, value = T.run_json("show", *_key_args(inv))
        nxt = value["result"]["next"]
        assert nxt["action"] == "terminal" and nxt["rule"] == "W-5"
        assert value["result"]["report"]["positive_works"] == value["result"]["report"]["projection_count"]


def test_show_claims_explains_every_claim_from_templates(ar: T.Inv) -> None:
    code, value = T.run_json("show", *_key_args(ar), "--claims")
    claims = value["result"]["report"]["claims"]
    assert code == 10 and len(claims) == sum(value["result"]["report"]["claims_by_class"].values())
    kinds = {c["kind"] for c in claims}
    assert {"finding", "not_found", "identity_conflict", "out_of_scope"} <= kinds
    code, text, _ = T.run_cli("show", *_key_args(ar), "--claims")
    assert "[identity_conflict] The identifiers of this citation conflict and require resolution." in text


def test_replay_reproduces_offline(ar: T.Inv, mmr: T.Inv) -> None:
    for inv in (ar, mmr):
        with T.offline():
            code, value = T.run_json("replay", *_key_args(inv))
        assert value["result"]["result"] == "reproduced" and value["result"]["first_difference"] is None
        assert value["result"]["report"] == inv.report_record()["report"]
        assert value["result"]["projection_set"] == inv.report_record()["projection_set"]
        assert code == inv.code
    # VS-2: the identity conflict is preserved by replay.
    _, value = T.run_json("replay", *_key_args(ar))
    assert len(value["result"]["identity_conflicts"]) == 1


def test_every_offline_command_opens_no_socket(en: T.Inv, tmp_path: Path) -> None:
    with T.offline() as guard:
        for argv in (
            ["show", *_key_args(en), "--claims"],
            ["verify", *_key_args(en)],
            ["replay", *_key_args(en)],
            ["checkpoint", *_key_args(en)],
            ["export", *_key_args(en), "--out", tmp_path / "x"],
        ):
            assert T.run_cli(*argv)[0] == 0, argv
    assert guard.attempts == []


def test_show_counts_committed_claims_and_prints_no_blob_content(ar: T.Inv) -> None:
    _, value = T.run_json("show", *_key_args(ar))
    res = value["result"]
    assert res["claims_by_class"] == res["report"]["claims_by_class"]
    assert res["open_questions"] == 1 and res["report"]["open_questions"] == 1
    text = T.run_cli("show", *_key_args(ar))[1]
    assert "claims: IDENTITY_CONFLICT 1" in text
    # No captured page content and no evidence blob is printed: only digests, counts and fixed text.
    capture = json.loads((S8.AR_OBOKATA / "capture.json").read_bytes())
    assert capture["page"]["title"] not in text and "items" not in text


def test_corrupt_or_foreign_index_fails_closed(tmp_path: Path, index: Path) -> None:
    """An index file that is not a Stage 02 index: no lookup, no claim (FAILED), nothing to export."""
    bad = tmp_path / "index.sqlite"
    bad.write_bytes(b"not an index" * 100)
    root = S8.memory_root(tmp_path)
    with T.offline():
        code, value = T.run_json("run", "--bundle", S8.EN_OBOKATA, "--index", bad, "--memory-root", root)
    assert code == 9, value
    key = value["result"]["investigation_key"]
    assert value["result"]["terminated_by"]["step"] in ("VALIDATE", "LOOKUP")
    assert not [r for r in T.journal(root, key) if r["kind"] in ("claim_recorded", "report_recorded")]


def test_corrupt_journal_is_corrupt_and_never_repaired(en: T.Inv, tmp_path: Path) -> None:
    inv = en.copy(tmp_path)
    path = inv.dir / "journal.jsonl"
    path.chmod(0o600)
    lines = path.read_bytes().split(b"\n")
    lines[3] = lines[3].replace(b'"attempt":1', b'"attempt":2', 1)
    path.write_bytes(b"\n".join(lines))
    damaged = path.read_bytes()
    for command in ("show", "verify", "replay", "resume", "checkpoint"):
        assert T.run_json(command, *_key_args(inv))[0] == 12, command
    with T.offline():
        code, _ = T.run_json("run", "--bundle", S8.EN_OBOKATA, "--index", Path(en.request["index_path"]),
                             "--memory-root", inv.root)  # fmt: skip
    assert code == 12
    assert path.read_bytes() == damaged  # nothing repaired, dropped or rewritten
    assert T.run_json("export", *_key_args(inv), "--out", tmp_path / "x")[0] == 12 and not (tmp_path / "x").exists()
