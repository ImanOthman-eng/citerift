"""The extraction worker: one bundle in, one canonical extraction document on stdout (run by ``extract.py``).

The parent sets the address-space and CPU limits before this code runs and kills the process group at the wall
deadline. The worker refuses every network connection: replay and extraction are offline by construction, and a
connection attempt is an error, not a silent fallback.
"""

from __future__ import annotations

import _socket
import json
import socket
import sys
from typing import Any, NoReturn


def _no_network(*args: Any, **kwargs: Any) -> NoReturn:
    raise PermissionError("the extraction worker makes no network connection")


class _NoNetworkSocket(_socket.socket):
    """The C-level socket type with every way to reach a peer refused."""

    def connect(self, *args: Any, **kwargs: Any) -> Any:
        return _no_network()

    def connect_ex(self, *args: Any, **kwargs: Any) -> Any:
        return _no_network()

    def sendto(self, *args: Any, **kwargs: Any) -> Any:
        return _no_network()

    def sendmsg(self, *args: Any, **kwargs: Any) -> Any:
        return _no_network()


def forbid_network() -> None:
    """Refuse connections in this process: the socket module's functions and the C-level socket type the module
    builds on. This is an in-process guard for the project's own extractor, not a sandbox (RISK_ANALYSIS.md)."""
    socket.socket.connect = _no_network  # type: ignore[method-assign]
    socket.socket.connect_ex = _no_network  # type: ignore[method-assign]
    socket.socket.sendto = _no_network  # type: ignore[method-assign]
    socket.socket.sendmsg = _no_network  # type: ignore[method-assign]
    socket.create_connection = _no_network
    socket.getaddrinfo = _no_network
    _socket.socket = _NoNetworkSocket  # type: ignore[misc]
    _socket.SocketType = _NoNetworkSocket
    _socket.getaddrinfo = _no_network


# CPython 3.12 and 3.13 raise this SystemError, not MemoryError, when a Python call cannot get a new frame-stack
# chunk under the address-space limit (the chunk allocation fails without setting an exception). Which allocation
# fails first depends on the memory layout, so a memory failure can surface this way instead of as MemoryError.
_NO_EXCEPTION_SET = "error return without exception set"
# A frame-stack chunk is 16 KiB unless one frame needs more; 1 MiB of headroom covers it with a wide margin.
_PEAK_MARGIN_BYTES = 1 << 20


def _peak_address_space() -> int | None:
    """The process's peak virtual size in bytes (Linux ``VmPeak``), or None where it cannot be read."""
    try:
        with open("/proc/self/status", encoding="ascii") as fh:
            for line in fh:
                if line.startswith("VmPeak:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def interpreter_memory_failure(exc: BaseException) -> bool:
    """Whether a SystemError is the interpreter's own allocation failure at the address-space limit: the message
    of a call that failed without setting an exception, and a peak address space that reached the limit. Without
    both (or where either cannot be read) the error stays a worker failure."""
    if type(exc) is not SystemError or str(exc) != _NO_EXCEPTION_SET:
        return False
    import resource  # noqa: PLC0415 - POSIX only; the parent runs this worker on POSIX only

    limit = resource.getrlimit(resource.RLIMIT_AS)[0]
    peak = _peak_address_space()
    if limit == resource.RLIM_INFINITY or peak is None:
        return False
    return peak >= limit - _PEAK_MARGIN_BYTES


def main(argv: list[str]) -> int:
    forbid_network()
    # Imported only after the network is closed, so that no import can open a connection first.
    from citerift.wiki.bundle import BundleError, open_bundle  # noqa: PLC0415
    from citerift.wiki.canonical import canonical_bytes  # noqa: PLC0415
    from citerift.wiki.extract import ExtractConfig, extract_document, failure_document  # noqa: PLC0415

    bundle_path, config_json = argv[0], argv[1]
    if len(argv) > 3 and argv[3] == "python-tokenizer":
        # Only to classify a native crash (MF-1): the result of this run is never returned as an extraction.
        import mwparserfromhell.parser  # noqa: PLC0415

        mwparserfromhell.parser.use_c = False
    config = ExtractConfig.from_json(json.loads(config_json))
    try:
        bundle = open_bundle(bundle_path)  # type: ignore[arg-type]
        if len(argv) > 2 and argv[2] == "markers":
            from citerift.wiki.verify import _reconstruct_markers  # noqa: PLC0415

            doc = _reconstruct_markers(bundle, config)
        else:
            doc = extract_document(bundle, config)
    except BundleError as exc:
        doc = failure_document(None, config, exc.issue.code, exc.issue.detail)
    except MemoryError:
        print("MemoryError", file=sys.stderr)
        return 3
    except SystemError as exc:
        if not interpreter_memory_failure(exc):
            raise
        print("MemoryError (interpreter frame allocation failed at the address-space limit)", file=sys.stderr)
        return 3
    sys.stdout.buffer.write(canonical_bytes(doc))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
