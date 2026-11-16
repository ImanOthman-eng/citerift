"""Step 10: D-052 external journal checkpoints and safe output paths (owner Step 10 items 24 and 25).

The checkpoint is written outside Investigation Memory and compared with the journal by ``verify --checkpoint``. The
journal forgeries here recompute the whole hash chain, as an adversary with write access to the memory root could: the
journal then opens cleanly, and only a checkpoint retained outside it shows the rewrite or the truncation.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8
import step10_support as T

from citerift.investigation import checkpoint as d052
from citerift.investigation import operations as ops
from citerift.investigation import outputs
from citerift.investigation.canonical import canon
from citerift.investigation.outputs import OperationError

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


def _args(inv: T.Inv) -> list[str | Path]:
    return ["--memory-root", inv.root, "--key", inv.key]


def _write(path: Path, value: Any) -> Path:
    path.write_bytes(canon(value) + b"\n")
    return path


def _checkpoint(inv: T.Inv, path: Path) -> dict[str, Any]:
    code, _out, err = T.run_cli("checkpoint", *_args(inv), "--out", path)
    assert code == inv.code, err
    return json.loads(path.read_bytes())


def _verify(inv: T.Inv, cp: Path) -> tuple[int, dict[str, Any]]:
    code, value = T.run_json("verify", *_args(inv), "--checkpoint", cp)
    return code, value["result"] if "result" in value else value["error"]


# Format and statement --------------------------------------------------------------------------------------------


def test_checkpoint_holds_exactly_the_d052_fields(en: T.Inv, tmp_path: Path) -> None:
    value = _checkpoint(en, tmp_path / "cp.json")
    records = en.records()
    assert value == {
        "format": "citerift-investigation-checkpoint",
        "format_version": "1",
        "investigation_key": en.key,
        "seq": records[-1]["seq"],
        "journal_digest": records[-1]["digest"],
    }
    assert (tmp_path / "cp.json").read_bytes() == canon(value) + b"\n"


def test_checkpoint_on_stdout_and_the_exact_statement(en: T.Inv) -> None:
    code, out, err = T.run_cli("checkpoint", *_args(en))
    assert code == 0 and d052.parse(out.encode()) == d052.make(en.key, en.records())
    assert err.strip() == "A checkpoint retained outside Investigation Memory can detect rewriting or truncation of " \
        "the journal prefix it covers."  # fmt: skip
    assert err.strip() == d052.STATEMENT


def test_no_security_wording_anywhere_in_the_checkpoint_code() -> None:
    import citerift.investigation.checkpoint as module

    text = (Path(module.__file__).read_text(encoding="utf-8") + d052.STATEMENT).lower()
    for word in ("signature", "signed", "authentic", "non-repudiation", "tamper-proof", "tamper proof"):
        assert word not in text, word


# Comparison ------------------------------------------------------------------------------------------------------


def test_exact_match(en: T.Inv, tmp_path: Path) -> None:
    cp = tmp_path / "cp.json"
    _checkpoint(en, cp)
    code, result = _verify(en, cp)
    assert code == 0 and result["result"] == "passed"
    assert result["checkpoint"] == {"result": "CHECKPOINT_MATCH", "statement": d052.STATEMENT}
    assert {"check": "D052_CHECKPOINT", "passed": True, "detail": "CHECKPOINT_MATCH"} in result["checks"]


def test_an_earlier_checkpoint_matches_a_journal_that_grew(tmp_path: Path, index: Path) -> None:
    root = S8.memory_root(tmp_path)
    payload = ops.created_for(ops.retained_request(S8.EN_OBOKATA, index, root))
    from citerift.investigation.memory import InvestigationMemory

    InvestigationMemory.create(root, payload).close()
    key = payload["investigation_key"]
    cp = tmp_path / "early.json"
    assert T.run_cli("checkpoint", "--memory-root", root, "--key", key, "--out", cp)[0] == 14
    assert json.loads(cp.read_bytes())["seq"] == 0
    with T.offline():
        assert T.run_cli("resume", "--memory-root", root, "--key", key)[0] == 0
    code, value = T.run_json("verify", "--memory-root", root, "--key", key, "--checkpoint", cp)
    assert code == 0 and value["result"]["checkpoint"]["result"] == "CHECKPOINT_MATCH"


def test_truncation_with_a_recomputed_chain(en: T.Inv, tmp_path: Path) -> None:
    inv = en.copy(tmp_path)
    cp = tmp_path / "cp.json"
    _checkpoint(inv, cp)
    records = inv.records()
    verify_at = next(i for i, r in enumerate(records) if r["step"] == "VERIFY")
    T.rewrite(inv.root, inv.key, records[:verify_at])  # a clean prefix: the journal still opens
    code, _value = T.run_json("show", *_args(inv))
    assert code == 14  # RUNNING: the truncated journal is a valid, incomplete one
    code, result = _verify(inv, cp)
    assert code == 5 and result["result"] == "failed"
    assert result["checkpoint"]["result"] == "CHECKPOINT_TRUNCATED"


def test_rewrite_with_a_recomputed_chain(en: T.Inv, tmp_path: Path) -> None:
    """A forged prefix that Memory accepts (an earlier ``at`` changed, every later digest recomputed)."""
    inv = en.copy(tmp_path)
    cp = tmp_path / "cp.json"
    _checkpoint(inv, cp)
    records = inv.records()
    forged = copy.deepcopy(records)
    i = next(i for i, r in enumerate(forged) if r["kind"] == "step_started")
    assert forged[i]["at"] != forged[i - 1]["at"]
    forged[i]["at"] = forged[i - 1]["at"]
    T.rewrite(inv.root, inv.key, forged)
    assert T.run_json("show", *_args(inv))[0] == 0  # the forged journal opens and looks complete
    code, result = _verify(inv, cp)
    assert code == 5 and result["checkpoint"]["result"] == "CHECKPOINT_PREFIX_REWRITTEN"
    plain_code, plain = T.run_json("verify", *_args(inv))
    assert plain_code == 0 and plain["result"]["result"] == "passed"  # without the checkpoint it is not detected


def test_wrong_investigation(en: T.Inv, ar: T.Inv, tmp_path: Path) -> None:
    cp = tmp_path / "cp.json"
    _checkpoint(ar, cp)
    code, result = _verify(en, cp)
    assert code == 5 and result["checkpoint"]["result"] == "CHECKPOINT_KEY_MISMATCH"


def test_wrong_seq_and_wrong_digest(en: T.Inv, tmp_path: Path) -> None:
    value = d052.make(en.key, en.records())
    records = en.records()
    cases = {
        "seq beyond the journal": ({**value, "seq": value["seq"] + 1}, "CHECKPOINT_TRUNCATED"),
        "seq of another record": ({**value, "seq": value["seq"] - 1}, "CHECKPOINT_PREFIX_REWRITTEN"),
        "digest of another record": ({**value, "journal_digest": records[0]["digest"]}, "CHECKPOINT_PREFIX_REWRITTEN"),
        "digest that names nothing": ({**value, "journal_digest": "f" * 64}, "CHECKPOINT_PREFIX_REWRITTEN"),
        "earlier seq with its own digest": ({**value, "seq": 3, "journal_digest": records[3]["digest"]}, None),
    }
    for name, (cp, expected) in cases.items():
        code, result = _verify(en, _write(tmp_path / "cp.json", cp))
        if expected is None:
            assert code == 0 and result["checkpoint"]["result"] == "CHECKPOINT_MATCH", name
        else:
            assert code == 5 and result["checkpoint"]["result"] == expected, name


def _malformed(en: T.Inv) -> dict[str, bytes]:
    good = d052.make(en.key, en.records())
    seq = f'"seq":{good["seq"]}'.encode()
    return {
        "empty": b"",
        "not json": b"checkpoint",
        "not canonical (spaces)": json.dumps(good, sort_keys=True).encode(),
        "not canonical (key order)": json.dumps(dict(reversed(list(good.items()))), separators=(",", ":")).encode(),
        "array": b"[]",
        "too large": b" " * (d052.MAX_BYTES + 1),
        "two newlines": canon(good) + b"\n\n",
        "missing field": canon({k: v for k, v in good.items() if k != "seq"}),
        "extra field": canon({**good, "at": "2026-01-01T00:00:00Z"}),
        "wrong format": canon({**good, "format": "citerift-investigation-other"}),
        "wrong version": canon({**good, "format_version": "2"}),
        "negative seq": canon({**good, "seq": -1}),
        "seq as text": canon({**good, "seq": str(good["seq"])}),
        "seq as boolean": canon({**good, "seq": True}),
        "float seq": canon(good).replace(seq, seq + b".0"),
        "upper-case digest": canon({**good, "journal_digest": good["journal_digest"].upper()}),
        "short key": canon({**good, "investigation_key": good["investigation_key"][:-1]}),
    }


def test_malformed_checkpoints_are_invalid_input(en: T.Inv, tmp_path: Path) -> None:
    before = en.journal_bytes()
    for name, data in _malformed(en).items():
        path = tmp_path / "cp.json"
        path.write_bytes(data)
        code, value = T.run_json("verify", *_args(en), "--checkpoint", path)
        assert code == 3 and value["error"]["code"] == "CHECKPOINT_INVALID", name
    code, value = T.run_json("verify", *_args(en), "--checkpoint", tmp_path / "absent.json")
    assert code == 3 and value["error"]["code"] == "CHECKPOINT_INVALID"
    assert en.journal_bytes() == before


# Output paths (owner item 25) --------------------------------------------------------------------------------------


def test_checkpoint_is_never_written_inside_the_memory_root(en: T.Inv, tmp_path: Path) -> None:
    before = sorted(p.relative_to(en.root) for p in en.root.rglob("*"))
    for out in (en.root / "cp.json", en.dir / "cp.json", en.dir / "blobs" / "cp.json", en.root):
        code, value = T.run_json("checkpoint", *_args(en), "--out", out)
        assert code == 3 and value["error"]["code"] in ("OUTPUT_PATH_UNSAFE", "OUTPUT_EXISTS"), out
    link = tmp_path / "link"
    link.symlink_to(en.root)  # a path outside that resolves inside
    code, value = T.run_json("checkpoint", *_args(en), "--out", link / "cp.json")
    assert code == 3 and value["error"]["code"] == "OUTPUT_PATH_UNSAFE"
    code, value = T.run_json("export", *_args(en), "--out", link / "export")
    assert code == 3 and value["error"]["code"] == "OUTPUT_PATH_UNSAFE"
    assert sorted(p.relative_to(en.root) for p in en.root.rglob("*")) == before


def test_no_overwrite_unless_asked_and_never_through_a_symlink(en: T.Inv, tmp_path: Path) -> None:
    cp = tmp_path / "cp.json"
    cp.write_bytes(b"keep")
    code, value = T.run_json("checkpoint", *_args(en), "--out", cp)
    assert code == 3 and value["error"]["code"] == "OUTPUT_EXISTS" and cp.read_bytes() == b"keep"
    assert T.run_cli("checkpoint", *_args(en), "--out", cp, "--overwrite")[0] == 0
    assert d052.parse(cp.read_bytes())["investigation_key"] == en.key
    target = tmp_path / "elsewhere"
    target.write_bytes(b"keep")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    for extra in ([], ["--overwrite"]):
        code, value = T.run_json("checkpoint", *_args(en), "--out", link, *extra)
        assert code == 3 and value["error"]["code"] == "OUTPUT_PATH_UNSAFE"
    assert target.read_bytes() == b"keep"
    (tmp_path / "dir").mkdir()
    code, value = T.run_json("checkpoint", *_args(en), "--out", tmp_path / "dir", "--overwrite")
    assert code == 3 and value["error"]["code"] == "OUTPUT_PATH_UNSAFE"
    code, value = T.run_json("checkpoint", *_args(en), "--out", tmp_path / "missing" / "cp.json")
    assert code == 3 and value["error"]["code"] == "OUTPUT_PATH_UNSAFE"


def test_existing_export_target_is_never_replaced(en: T.Inv, tmp_path: Path) -> None:
    out = tmp_path / "export"
    out.mkdir()
    (out / "mine").write_bytes(b"keep")
    code, value = T.run_json("export", *_args(en), "--out", out)
    assert code == 3 and value["error"]["code"] == "OUTPUT_EXISTS"
    assert os.listdir(out) == ["mine"]


@pytest.mark.parametrize("fail_at", ["rename", "fsync", "write"])
def test_a_failed_write_leaves_no_target_and_no_temporary(
    en: T.Inv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_at: str
) -> None:
    def boom(*args: Any, **kwargs: Any) -> Any:
        raise OSError(28, "No space left on device")

    if fail_at == "rename":
        monkeypatch.setattr(outputs.os, "rename", boom)
        monkeypatch.setattr(outputs.os, "link", boom)
    elif fail_at == "fsync":
        monkeypatch.setattr(outputs.os, "fsync", boom)
    else:
        monkeypatch.setattr(outputs, "write_all", boom)
    code, value = T.run_json("export", *_args(en), "--out", tmp_path / "export")
    assert code == 3 and value["error"]["code"] == "OUTPUT_WRITE_FAILED"
    code, value = T.run_json("checkpoint", *_args(en), "--out", tmp_path / "cp.json")
    assert code == 3 and value["error"]["code"] == "OUTPUT_WRITE_FAILED"
    assert os.listdir(tmp_path) == []


def test_a_failed_overwrite_keeps_the_old_file(en: T.Inv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cp = tmp_path / "cp.json"
    cp.write_bytes(b"old")

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(outputs.os, "replace", boom)
    code, value = T.run_json("checkpoint", *_args(en), "--out", cp, "--overwrite")
    assert code == 3 and value["error"]["code"] == "OUTPUT_WRITE_FAILED"
    assert cp.read_bytes() == b"old" and os.listdir(tmp_path) == ["cp.json"]


def test_unsafe_names_are_refused(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    root.mkdir()
    for out in (tmp_path / "..", Path("/"), tmp_path / "."):
        with pytest.raises(OperationError) as exc:
            outputs.target(out, root)
        assert exc.value.code in ("OUTPUT_PATH_UNSAFE", "OUTPUT_EXISTS"), out
