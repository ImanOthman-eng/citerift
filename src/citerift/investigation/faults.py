"""Named persistence boundaries, for fault injection (owner Step 6 item 10; gate 04-E).

Production code calls ``point(name, **context)`` at each boundary; with no handler installed it does nothing. A test
installs a handler that kills the process there (``os._exit``), optionally after writing a partial prefix of the
pending bytes with the file descriptor it is given, so the production write path is the same with and without
injection. The handler is process-local and is never installed outside tests.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Handler = Callable[[str, dict[str, Any]], None]

POINTS = (
    "create.prepared",  # investigation directory written in its temporary location, before the rename
    "create.renamed",  # after the rename into place, before the memory root fsync
    "blob.before_write",  # temporary file created, nothing written
    "blob.during_write",  # handler may write a prefix of the bytes (fd, data) and die
    "blob.after_fsync",  # temporary file complete and fsynced, digest not yet re-verified
    "blob.before_link",  # digest verified, before publication
    "blob.after_link",  # published under its digest, before the directory fsync
    "blob.published",  # directory fsynced; before any journal record names the blob
    "journal.before_append",  # record built and checked, nothing written
    "journal.during_append",  # handler may write a prefix of the line (fd, data) and die
    "journal.after_write",  # line written, before fsync
    "journal.after_fsync",  # line durable
    "torn.copied",  # torn tail preserved as journal.jsonl.torn-<k>, before the valid prefix is written
    "torn.prefix_written",  # valid prefix written and fsynced to a temporary file, before it replaces the journal
)

_installed: list[Handler] = []


def install(handler: Handler | None) -> None:
    _installed.clear()
    if handler is not None:
        _installed.append(handler)


def point(name: str, **context: Any) -> None:
    for handler in _installed:
        handler(name, context)
