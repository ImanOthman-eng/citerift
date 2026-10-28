"""The extraction worker: one bundle in, one canonical extraction document on stdout (run by ``extract.py``).

The parent sets the address-space and CPU limits before this code runs and kills the process group at the wall
deadline. The worker refuses every network connection: replay and extraction are offline by construction, and a
connection attempt is an error, not a silent fallback.
"""

from __future__ import annotations

import json
import socket
import sys
from typing import Any, NoReturn


def _no_network(*args: Any, **kwargs: Any) -> NoReturn:
    raise PermissionError("the extraction worker makes no network connection")


def forbid_network() -> None:
    socket.socket.connect = _no_network  # type: ignore[method-assign]
    socket.socket.connect_ex = _no_network  # type: ignore[method-assign]
    socket.create_connection = _no_network
    socket.getaddrinfo = _no_network


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
