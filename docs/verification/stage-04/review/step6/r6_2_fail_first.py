"""D-044 fail-first demonstration for review finding R6-2 (owner instruction of 2026-11-10).

Builds the synthetic Step 6 investigation, changes one hex digit of the stored digest of the complete,
newline-terminated final record, and opens the investigation read-only and then writable. Prints what Memory does.

Run from the repository root: ``uv run python docs/verification/stage-04/review/step6/r6_2_fail_first.py``.
Expected after D-044: both opens raise CORRUPT and the journal is unchanged. Before D-044 (commit 6fd799d) the record
was classified as a torn tail and the writable open removed it.
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "tests" / "stage04"))

from memory_support import Clock, drive, new_memory  # noqa: E402

from citerift.investigation.errors import CorruptInvestigation  # noqa: E402
from citerift.investigation.memory import InvestigationMemory  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        mem, root = new_memory(Path(tmp))
        drive(mem)
        key = mem.key
        mem.close()
        journal = root / key / "journal.jsonl"
        lines = journal.read_bytes().split(b"\n")[:-1]
        last = lines[-1]
        field = b'"digest":"'
        at = last.index(field) + len(field)
        flipped = last[:at] + (b"1" if last[at : at + 1] == b"0" else b"0") + last[at + 1 :]
        data = b"".join(line + b"\n" for line in lines[:-1]) + flipped + b"\n"
        journal.write_bytes(data)
        newline = b"\n"
        print(f"records stored: {len(lines)}; final record ends with newline: {data.endswith(newline)}")
        print(f"journal sha256 before open: {hashlib.sha256(data).hexdigest()}")
        for writable in (False, True):
            label = "writable" if writable else "read-only"
            try:
                with InvestigationMemory.open(root, key, writable=writable, clock=Clock()) as m:
                    torn = m.torn_tail.reason if m.torn_tail else None
                    print(f"{label} open: ACCEPTED, records folded: {len(m.view.records)}, torn tail: {torn!r}")
            except CorruptInvestigation as exc:
                print(f"{label} open: CORRUPT ({exc.cause.code}: {exc.cause.detail})")
        after = journal.read_bytes()
        print(f"journal unchanged after opens: {after == data}; records now stored: {after.count(newline)}")
        print(f"preserved copies: {sorted(p.name for p in (root / key).glob('journal.jsonl.torn-*'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
