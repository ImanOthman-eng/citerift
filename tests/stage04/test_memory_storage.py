"""Step 6: blob store, single-writer lock, concurrency and path safety (SPEC 8.2, 10.1, S-15.3; Step 6 items 5, 9,
11 and 12).

Child processes are real processes (``subprocess``); the lock is the kernel's ``flock``. Nothing here simulates a
lease or a timeout: ownership is the kernel lock alone, so a killed holder releases it.
"""

from __future__ import annotations

import ast
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from memory_support import Clock, bundle_payload, drive, h, memory_root, new_memory

from citerift.investigation import blobs as blobs_module
from citerift.investigation.blobs import MAX_BLOB_BYTES, BlobStore
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.errors import (
    BlobError,
    Busy,
    CanonError,
    CorruptInvestigation,
    InvestigationMemoryError,
    PathUnsafe,
    StorageError,
)
from citerift.investigation.fold import Folder
from citerift.investigation.fsutil import open_dir
from citerift.investigation.journal import read_journal
from citerift.investigation.memory import InvestigationMemory, created_payload

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "citerift" / "investigation"


def _run_child(script: str, *args: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-c", script, *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=ROOT,
    )


_HOLD = """
import sys
from citerift.investigation.memory import InvestigationMemory, created_payload
mem = InvestigationMemory.open(sys.argv[1], sys.argv[2])
print("held", flush=True)
if sys.stdin.readline().strip() == "close":
    mem.close()
    print("closed", flush=True)
    sys.stdin.readline()
# exit without close: the kernel releases the lock
"""


# Blobs ------------------------------------------------------------------------------------------------------------


@pytest.mark.unit
def test_blob_publication_is_idempotent_and_leaves_no_temporary(tmp_path: Path) -> None:
    mem, root = new_memory(tmp_path)
    with mem:
        d1 = mem.put_blob({"x": [1, 2, 3], "r": 0.25})
        d2 = mem.put_blob({"r": 0.25, "x": [1, 2, 3]})  # same canonical bytes
        assert d1 == d2 == sha256_hex(canon({"x": [1, 2, 3], "r": 0.25}, allow_float=True))
        blob_dir = root / mem.key / "blobs"
        assert sorted(os.listdir(blob_dir)) == [d1]
        st = os.stat(blob_dir / d1)
        mem.put_blob({"x": [1, 2, 3], "r": 0.25})
        assert os.stat(blob_dir / d1).st_ino == st.st_ino  # not rewritten


@pytest.mark.negative
def test_existing_blob_with_incompatible_bytes_is_never_overwritten(tmp_path: Path) -> None:
    mem, root = new_memory(tmp_path)
    with mem:
        value = {"x": 1}
        digest = sha256_hex(canon(value))
        path = root / mem.key / "blobs" / digest
        path.write_bytes(b'{"x":2}')  # a name whose bytes do not hash to it
        with pytest.raises(BlobError) as exc:
            mem.put_blob(value)
        assert exc.value.code == "BLOB_CORRUPT"
        assert path.read_bytes() == b'{"x":2}'
        assert mem.blobs.temporaries() == []


@pytest.mark.negative
@pytest.mark.parametrize(
    ("data", "error"),
    [
        (b'{"a": 1}', CanonError),  # not canonical
        (b'{"a":NaN}', CanonError),
        (b'{"a":1,"a":1}', CanonError),
    ],
)
def test_blob_bytes_must_be_canonical_json(tmp_path: Path, data: bytes, error: type[Exception]) -> None:
    mem, _ = new_memory(tmp_path)
    with mem, pytest.raises(error):
        mem.put_blob_bytes(data)


@pytest.mark.security
def test_oversized_blob_is_refused_without_reading_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mem, _ = new_memory(tmp_path)
    with mem:
        digest = mem.put_blob({"x": "y" * 100})
        monkeypatch.setattr(blobs_module, "MAX_BLOB_BYTES", 50)
        with pytest.raises(BlobError) as exc:
            mem.put_blob_bytes(canon({"x": "z" * 100}))
        assert exc.value.code == "BLOB_TOO_LARGE"
        with pytest.raises(BlobError) as exc:
            mem.blobs.get(digest, limit=50)
        assert exc.value.code == "BLOB_TOO_LARGE"
    assert MAX_BLOB_BYTES == 256 * 1024 * 1024


@pytest.mark.security
@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo"])
def test_blob_name_that_is_not_a_regular_file_is_corrupt(tmp_path: Path, kind: str) -> None:
    mem, root = new_memory(tmp_path)
    with mem:
        value = {"x": kind}
        digest = sha256_hex(canon(value))
        path = root / mem.key / "blobs" / digest
        target = tmp_path / "elsewhere"
        target.write_bytes(canon(value))
        if kind == "symlink":
            path.symlink_to(target)  # even a link to the right bytes is refused
        elif kind == "directory":
            path.mkdir()
        else:
            os.mkfifo(path)
        with pytest.raises(BlobError) as exc:
            mem.put_blob(value)
        assert exc.value.code == "BLOB_CORRUPT"
        assert not path.is_file() or path.is_symlink()


_PUBLISH = """
import json, os, sys
from citerift.investigation.blobs import BlobStore
from citerift.investigation.canonical import canon
from citerift.investigation.fsutil import open_dir
store = BlobStore(open_dir(sys.argv[1]))
sys.stdin.readline()  # start together
out = [store.put(canon({"shared": "x" * 200000, "n": 0}))]
for i in range(20):
    out.append(store.put(canon({"own": sys.argv[2], "i": i})))
print(json.dumps(out))
"""


@pytest.mark.integration
def test_concurrent_blob_publication_is_safe(tmp_path: Path) -> None:
    """Eight processes publish the same large blob and their own blobs at once: one complete file per name, all
    verified, no temporaries; every publisher gets the same digest for the shared value."""
    mem, root = new_memory(tmp_path)
    blob_dir = root / mem.key / "blobs"
    children = [_run_child(_PUBLISH, str(blob_dir), str(n)) for n in range(8)]
    for c in children:
        assert c.stdin is not None
        c.stdin.write("go\n")
        c.stdin.flush()
    results = []
    for c in children:
        out, err = c.communicate(timeout=120)
        assert c.returncode == 0, err
        results.append(json.loads(out))
    shared = {r[0] for r in results}
    assert len(shared) == 1
    names = mem.blobs.names()
    assert len(names) == 1 + 8 * 20
    for name in names:
        mem.blobs.verify(name)
    assert mem.blobs.temporaries() == []
    mem.close()


_WRITER = """
import sys
sys.path.insert(0, sys.argv[3])
from memory_support import Clock, drive
from citerift.investigation.memory import InvestigationMemory, created_payload
mem = InvestigationMemory.open(sys.argv[1], sys.argv[2], clock=Clock())
for i in range(int(sys.argv[4])):
    mem.put_blob({"big": "x" * 300000, "i": i})
drive(mem)
mem.close()
"""


@pytest.mark.integration
def test_lockless_readers_never_see_partial_data(tmp_path: Path) -> None:
    """While a writer publishes blobs and appends records, a lockless reader sees only verified blobs and a valid
    chain prefix of records; an unfinished final line is at most a torn tail, never a record."""
    mem, root = new_memory(tmp_path)
    key = mem.key
    mem.close()
    inv_fd = open_dir(root / key)
    blobs_fd = open_dir("blobs", dir_fd=inv_fd)
    store = BlobStore(blobs_fd)
    writer = _run_child(_WRITER, str(root), key, str(ROOT / "tests" / "stage04"), "40")
    reads = 0
    seen_records = 0
    try:
        while writer.poll() is None or reads < 3:
            for name in store.names():
                store.verify(name)  # complete and canonical, or absent
            read = read_journal(inv_fd)
            folder = Folder(None, expected_key=key)
            for rec in read.records:
                folder.apply(rec)  # chain, digests and invariants of everything visible
            seen_records = max(seen_records, len(read.records))
            reads += 1
    finally:
        _, err = writer.communicate(timeout=120)
        os.close(blobs_fd)
        os.close(inv_fd)
    assert writer.returncode == 0, err
    assert reads >= 3 and seen_records >= 1


# The lock ---------------------------------------------------------------------------------------------------------


@pytest.mark.integration
def test_second_writer_is_refused_and_lock_released_after_close(tmp_path: Path) -> None:
    mem, root = new_memory(tmp_path)
    key = mem.key
    with pytest.raises(Busy) as exc:
        InvestigationMemory.open(root, key, clock=Clock())
    assert exc.value.code == "INVESTIGATION_BUSY"
    with pytest.raises(Busy):
        InvestigationMemory.open(root, key, writable=False, clock=Clock())  # SPEC 10.1: readers lock too
    with pytest.raises(Busy):
        InvestigationMemory.create(root, bundle_payload(root), clock=Clock())
    mem.close()
    with InvestigationMemory.open(root, key, clock=Clock()):
        pass


@pytest.mark.integration
@pytest.mark.parametrize("ending", ["close", "exit", "SIGKILL"])
def test_lock_is_released_when_the_holder_ends(tmp_path: Path, ending: str) -> None:
    mem, root = new_memory(tmp_path)
    key = mem.key
    mem.close()
    child = _run_child(_HOLD, str(root), key)
    assert child.stdout is not None and child.stdin is not None
    assert child.stdout.readline().strip() == "held"
    with pytest.raises(Busy):
        InvestigationMemory.open(root, key, clock=Clock())
    if ending == "close":
        child.stdin.write("close\n")
        child.stdin.flush()
        assert child.stdout.readline().strip() == "closed"
        with InvestigationMemory.open(root, key, clock=Clock()):  # the child is still alive
            pass
        child.stdin.write("\n")
        child.stdin.flush()
    elif ending == "exit":
        child.stdin.write("exit\n")
        child.stdin.flush()
    else:
        os.kill(child.pid, signal.SIGKILL)
    child.communicate(timeout=60)
    if ending == "SIGKILL":
        assert child.returncode == -signal.SIGKILL
    with InvestigationMemory.open(root, key, clock=Clock()) as again:
        drive(again, ("VALIDATE",))


@pytest.mark.security
def test_lock_file_contents_do_not_imply_ownership(tmp_path: Path) -> None:
    mem, root = new_memory(tmp_path)
    key = mem.key
    mem.close()
    lock = root / key / "lock"
    for content in (f"pid {os.getpid()} since {time.time():.0f}\n", "pid 1 since 0\n", "garbage", ""):
        lock.write_text(content)  # stale or forged content: no process holds the kernel lock
        with InvestigationMemory.open(root, key, clock=Clock()) as again:
            assert again.key == key
    lock.unlink()  # an absent lock file is refused, never recreated (R6-7)
    with pytest.raises(PathUnsafe):
        InvestigationMemory.open(root, key, clock=Clock())
    assert not lock.exists()


# Path safety (S-15.3, MR-13) --------------------------------------------------------------------------------------


@pytest.mark.security
def test_unsafe_memory_roots_are_refused(tmp_path: Path) -> None:
    good = memory_root(tmp_path)
    payload = bundle_payload(good)
    cases: list[Path | str] = ["relative/memory"]
    link = tmp_path / "link"
    link.symlink_to(good)
    cases.append(link)
    shared = tmp_path / "shared"
    shared.mkdir()
    shared.chmod(0o777)
    cases.append(shared)
    group = tmp_path / "group"
    group.mkdir()
    group.chmod(0o770)
    cases.append(group)
    afile = tmp_path / "afile"
    afile.write_text("x")
    cases.append(afile)
    cases.append(tmp_path / "missing")
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    inside = repo / "memory"
    inside.mkdir(mode=0o700)
    inside.chmod(0o700)
    cases.append(inside)
    for case in cases:
        with pytest.raises(PathUnsafe) as exc:
            InvestigationMemory.create(case, payload, clock=Clock())
        assert exc.value.code == "MEMORY_ROOT_UNSAFE", case
    assert os.listdir(good) == []
    outside_repo = tmp_path / "plain"
    outside_repo.mkdir(mode=0o700)
    outside_repo.chmod(0o700)
    with pytest.raises(PathUnsafe):
        InvestigationMemory.create(outside_repo, bundle_payload(outside_repo), clock=Clock(), repository=tmp_path)


@pytest.mark.security
@pytest.mark.parametrize("key", ["../escape", "a" * 63, "A" * 64, "/" + "a" * 63, "a" * 64 + "/..", ""])
def test_investigation_keys_are_hex_names_only(tmp_path: Path, key: str) -> None:
    root = memory_root(tmp_path)
    with pytest.raises(PathUnsafe):
        InvestigationMemory.open(root, key, clock=Clock())
    payload = bundle_payload(root)
    payload["investigation_key"] = key
    with pytest.raises(PathUnsafe):
        InvestigationMemory.create(root, payload, clock=Clock())
    assert os.listdir(root) == []


@pytest.mark.security
@pytest.mark.parametrize("target", ["journal.jsonl", "blobs", "lock", "investigation"])
def test_symbolic_link_substitution_is_refused(tmp_path: Path, target: str) -> None:
    mem, root = new_memory(tmp_path)
    drive(mem, ("VALIDATE",))
    key = mem.key
    mem.close()
    inv = root / key
    elsewhere = tmp_path / "elsewhere"
    if target == "investigation":
        inv.rename(elsewhere)
        inv.symlink_to(elsewhere)
    else:
        (inv / target).rename(elsewhere)
        (inv / target).symlink_to(elsewhere)
    with pytest.raises((PathUnsafe, CorruptInvestigation)) as exc:
        InvestigationMemory.open(root, key, clock=Clock())
    assert exc.value.code in {"PATH_UNSAFE", "CORRUPT"}


@pytest.mark.security
@pytest.mark.parametrize("kind", ["directory", "fifo"])
def test_journal_that_is_not_a_regular_file_is_corrupt(tmp_path: Path, kind: str) -> None:
    mem, root = new_memory(tmp_path)
    key = mem.key
    mem.close()
    journal = root / key / "journal.jsonl"
    journal.unlink()
    if kind == "directory":
        journal.mkdir()
    else:
        os.mkfifo(journal)
    with pytest.raises(CorruptInvestigation) as exc:
        InvestigationMemory.open(root, key, clock=Clock())
    assert exc.value.cause.code == "JOURNAL_CORRUPT"


@pytest.mark.security
def test_no_path_is_built_from_request_text(tmp_path: Path) -> None:
    """A title or path in the request never names a file: only the key (a hash) and fixed names appear."""
    root = memory_root(tmp_path)
    payload = bundle_payload(root)
    payload["request"]["subject"]["bundle_path"] = "/data/../../etc/passwd"  # absolute (schema), with traversal
    payload = created_payload(payload["request"], payload["stage04"], bundle_capture_sha256=h("c"))
    with InvestigationMemory.create(root, payload, clock=Clock()) as mem:
        drive(mem, ("VALIDATE",))
        assert os.listdir(root) == [mem.key]
        assert sorted(os.listdir(root / mem.key)) == ["blobs", "journal.jsonl", "lock"]


@pytest.mark.security
def test_new_files_are_private(tmp_path: Path) -> None:
    mem, root = new_memory(tmp_path)
    with mem:
        drive(mem, ("VALIDATE",))
    inv = root / mem.key
    assert os.stat(inv).st_mode & 0o077 == 0
    assert os.stat(inv / "blobs").st_mode & 0o077 == 0
    for name in ("lock", "journal.jsonl", *(f"blobs/{n}" for n in os.listdir(inv / "blobs"))):
        assert os.stat(inv / name).st_mode & 0o077 == 0, name


@pytest.mark.contracts
def test_investigation_memory_does_not_import_governance() -> None:
    """S-15.1: no module of the investigation package imports citerift.governance."""
    offenders = []
    for path in sorted(SRC.glob("*.py")):
        tree = ast.parse(path.read_text(), str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            offenders += [f"{path.name}: {n}" for n in names if n.startswith("citerift.governance")]
    assert offenders == []


# Review findings R6-3, R6-5, R6-7, R6-8, R6-10, R6-11 ------------------------------------------------------------


@pytest.mark.integration
def test_an_existing_blob_is_made_durable_again_before_it_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R6-3: a put that finds its name already published fsyncs the file and the blobs directory again, because
    the earlier put may have failed before its directory fsync."""
    mem, _ = new_memory(tmp_path)
    with mem:
        mem.put_blob({"x": 1})
        synced: list[int] = []
        real = os.fsync
        monkeypatch.setattr(os, "fsync", lambda fd: (synced.append(fd), real(fd))[1])
        mem.put_blob({"x": 1})
        assert mem.blobs.dir_fd in synced and len(synced) == 2


@pytest.mark.integration
def test_writable_open_makes_directory_entries_durable_and_reports_leftovers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R6-5: after a crash between the creation rename and the memory root fsync, the next writable open fsyncs the
    memory root, the investigation directory and blobs before any append. Prepared directories are reported."""
    mem, root = new_memory(tmp_path)
    key = mem.key
    mem.close()
    (root / ".creating-0123456789abcdef").mkdir(mode=0o700)
    synced: list[int] = []
    real = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: (synced.append(os.fstat(fd).st_ino), real(fd))[1])
    with InvestigationMemory.open(root, key, clock=Clock()):
        pass
    monkeypatch.undo()
    for d in (root, root / key, root / key / "blobs"):
        assert os.stat(d).st_ino in synced, d
    assert InvestigationMemory.creation_leftovers(root) == [".creating-0123456789abcdef"]


@pytest.mark.security
def test_an_unlinked_lock_file_does_not_admit_a_second_writer(tmp_path: Path) -> None:
    """R6-7: if the lock file is removed while a writer holds it, no second writer is admitted (the file is not
    recreated), and the holder stops appending (its lock no longer guards the name)."""
    mem, root = new_memory(tmp_path)
    key = mem.key
    lock = root / key / "lock"
    lock.unlink()  # an outside actor removes the name while the first writer holds the lock
    with pytest.raises(PathUnsafe):
        InvestigationMemory.open(root, key, clock=Clock())
    with pytest.raises(InvestigationMemoryError) as exc:
        mem.append("step_started", {"step_key": h("v")}, step="VALIDATE", attempt=1)
    assert exc.value.code == "LOCK_LOST"
    lock.write_text("")  # an outside actor recreates it: a new inode, so the holder's lock still does not guard it
    with pytest.raises(StorageError):
        mem.append("step_started", {"step_key": h("v")}, step="VALIDATE", attempt=1)  # poisoned
    mem.close()
    with InvestigationMemory.open(root, key, clock=Clock()) as again:
        assert len(again.view.records) == 1


@pytest.mark.security
def test_read_only_open_neither_creates_nor_rewrites_the_lock(tmp_path: Path) -> None:
    """R6-8: looking at an investigation (even a CORRUPT one) changes nothing in it."""
    mem, root = new_memory(tmp_path)
    key = mem.key
    mem.close()
    lock = root / key / "lock"
    lock.write_text("informational content\n")
    with InvestigationMemory.open(root, key, writable=False, clock=Clock()):
        pass
    assert lock.read_text() == "informational content\n"
    lock.unlink()
    with pytest.raises(PathUnsafe):
        InvestigationMemory.open(root, key, writable=False, clock=Clock())
    assert not lock.exists()


@pytest.mark.security
@pytest.mark.skipif(os.geteuid() != 0, reason="changing a directory's owner needs root")
def test_directories_owned_by_another_user_are_refused(tmp_path: Path) -> None:
    """R6-10: the memory root, investigation directory and blobs directory must belong to this user and be private;
    the check runs on the opened descriptor."""
    mem, root = new_memory(tmp_path)
    key = mem.key
    mem.close()
    for target, code in (
        (root / key / "blobs", "PATH_UNSAFE"),
        (root / key, "PATH_UNSAFE"),
        (root, "MEMORY_ROOT_UNSAFE"),
    ):
        os.chown(target, 12345, -1)
        with pytest.raises(PathUnsafe) as exc:
            InvestigationMemory.open(root, key, clock=Clock())
        assert exc.value.code == code, target
        os.chown(target, 0, -1)
    (root / key / "blobs").chmod(0o770)
    with pytest.raises(PathUnsafe):
        InvestigationMemory.open(root, key, clock=Clock())


@pytest.mark.security
def test_a_directory_named_like_a_temporary_is_left_and_does_not_break_open(tmp_path: Path) -> None:
    """R6-11: only regular files and links named like temporaries are removed."""
    mem, root = new_memory(tmp_path)
    key = mem.key
    mem.close()
    (root / key / ".journal.tmp-dir").mkdir()
    (root / key / "blobs" / ".tmp-dir").mkdir()
    with InvestigationMemory.open(root, key, clock=Clock()):
        pass
    assert (root / key / ".journal.tmp-dir").is_dir() and (root / key / "blobs" / ".tmp-dir").is_dir()
