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


def main(argv: list[str]) -> int:
    forbid_network()
    # Imported only after the network is closed, so that no import can open a connection first.
    from citerift.wiki.bundle import BundleError, open_bundle  # noqa: PLC0415
    from citerift.wiki.canonical import canonical_bytes  # noqa: PLC0415
    from citerift.wiki.extract import ExtractConfig, extract_document, failure_document  # noqa: PLC0415

    bundle_path, config_json = argv[0], argv[1]
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
    sys.stdout.buffer.write(canonical_bytes(doc))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
