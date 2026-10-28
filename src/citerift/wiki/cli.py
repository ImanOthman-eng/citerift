"""``citerift-wiki``: capture, extract, verify and replay from the command line (SPECIFICATION.md 15).

Results are JSON on stdout; diagnostics go to stderr. Exit codes are stable:

====  ===========  ==========================================================================================
code  name         meaning
====  ===========  ==========================================================================================
0     ok           capture or extraction complete; verification passed; replay reproduced
1     internal     an unexpected error (a bug); nothing is published
2     usage        the command line is wrong
3     invalid      the request, a bundle, an extraction document or an output path is invalid or unsafe
4     unavailable  the page, revision or service is unavailable (missing, hidden, network failure)
5     verify       verification failed, a replay differs, or an upstream answer contradicts itself
6     partial      the operation finished with a partial result (for example the render was rejected)
7     unsupported  outside the supported scope (wiki, namespace, content model, redirect, size limit)
8     deferred     the service asked to wait past the deadline; ``not_before`` says when to retry
9     failed       the extraction failed (resource limit, worker failure)
====  ===========  ==========================================================================================

No command reports a failure as exit 0 with an empty result.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from citerift.wiki.bundle import BundleError, publish_file
from citerift.wiki.canonical import StrictJSONError, canonical_bytes, loads_strict
from citerift.wiki.capture import CaptureRequest, capture_revision
from citerift.wiki.extract import ExtractConfig, extract_bundle
from citerift.wiki.verify import replay_bundle, verify_bundle

EXIT_OK, EXIT_INTERNAL, EXIT_USAGE, EXIT_INVALID, EXIT_UNAVAILABLE, EXIT_VERIFY = 0, 1, 2, 3, 4, 5
EXIT_PARTIAL, EXIT_UNSUPPORTED, EXIT_DEFERRED, EXIT_FAILED = 6, 7, 8, 9

_INVALID = {
    "REQUEST_INVALID",
    "TITLE_INVALID",
    "BUNDLE_PATH_UNSAFE",
    "BUNDLE_MALFORMED",
    "BUNDLE_SCHEMA_INVALID",
    "BUNDLE_SEMANTIC_INVALID",
    "BUNDLE_ARTIFACT_MISSING",
    "BUNDLE_ARTIFACT_CORRUPT",
    "BUNDLE_DIGEST_MISMATCH",
    "SCHEMA_ROOT_UNAVAILABLE",
    "HOST_NOT_ALLOWED",
}
_UNSUPPORTED = {
    "WIKI_UNSUPPORTED",
    "NAMESPACE_UNSUPPORTED",
    "CONTENT_MODEL_UNSUPPORTED",
    "REDIRECT_NOT_FOLLOWED",
    "REDIRECT_LIMIT",
    "SOURCE_TOO_LARGE",
    "SOURCE_NOT_ENCODABLE",
    "PLATFORM_UNSUPPORTED",
}
_VERIFY = {"SOURCE_HASH_MISMATCH", "PAGE_ID_MISMATCH", "REVISION_ID_MISMATCH"}


def _emit(data: Any) -> None:
    sys.stdout.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def _err(message: str) -> None:
    sys.stderr.write(message.rstrip("\n") + "\n")


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:
        self.print_usage(sys.stderr)
        _err(f"{self.prog}: error: {message}")
        raise SystemExit(EXIT_USAGE)


def _positive(value: str) -> int:
    try:
        number = int(value, 10)
    except ValueError:
        raise argparse.ArgumentTypeError("a positive integer is required") from None
    if number < 1 or not value.isdigit():
        raise argparse.ArgumentTypeError("a positive integer is required")
    return number


def _parser() -> argparse.ArgumentParser:
    p = _Parser(prog="citerift-wiki", description="CITERIFT Stage 03 Wikipedia extraction engine (arwiki, enwiki)")
    sub = p.add_subparsers(dest="command", required=True, parser_class=_Parser)
    c = sub.add_parser("capture", help="capture one revision and its render (the only network operation)")
    c.add_argument("--wiki", required=True, choices=["ar", "en"])
    target = c.add_mutually_exclusive_group(required=True)
    target.add_argument("--title")
    target.add_argument("--page-id", type=_positive)
    target.add_argument("--revision", type=_positive)
    c.add_argument("--follow-redirect", action="store_true", help="follow one redirect hop (not with --revision)")
    c.add_argument("--no-render", action="store_true", help="capture the source revision only")
    c.add_argument("--out", type=Path, required=True, help="bundle directory to create (must not exist)")
    e = sub.add_parser("extract", help="extract a capture bundle offline")
    e.add_argument("--bundle", type=Path, required=True)
    e.add_argument("--out", type=Path, required=True, help="extraction document to create (must not exist)")
    e.add_argument("--config", type=Path, help="extraction configuration JSON (default: the built-in one)")
    v = sub.add_parser("verify", help="verify a bundle and optionally an extraction document of it")
    v.add_argument("--bundle", type=Path, required=True)
    v.add_argument("--extraction", type=Path)
    r = sub.add_parser("replay", help="re-extract a bundle offline and compare with a recorded extraction")
    r.add_argument("--bundle", type=Path, required=True)
    r.add_argument("--extraction", type=Path, help="the recorded extraction document to compare with")
    r.add_argument("--config", type=Path, help="pinned configuration JSON (default: the recorded one)")
    return p


def _exit_for(codes: list[str]) -> int:
    for group, code in ((_INVALID, EXIT_INVALID), (_UNSUPPORTED, EXIT_UNSUPPORTED), (_VERIFY, EXIT_VERIFY)):
        if any(c in group for c in codes):
            return code
    if "DEFERRED_RETRY_AFTER" in codes:
        return EXIT_DEFERRED
    return EXIT_UNAVAILABLE


def _config(path: Path | None) -> Any:
    if path is None:
        return None
    try:
        data = loads_strict(path.read_bytes())
        if not isinstance(data, dict):
            raise ValueError("the configuration is not an object")
        return ExtractConfig.from_json(data)
    except (OSError, StrictJSONError, ValueError, TypeError) as exc:
        raise _Invalid(f"configuration {path}: {exc}") from exc


class _Invalid(Exception):
    pass


def _capture(args: argparse.Namespace) -> int:

    request = CaptureRequest(
        args.wiki, args.title, args.page_id, args.revision, args.follow_redirect, not args.no_render
    )
    outcome = capture_revision(request, out=args.out)
    _emit(
        {"status": outcome.status, "bundle": str(outcome.bundle) if outcome.bundle else None, "capture": outcome.record}
    )
    errors = [i.code for i in outcome.issues if i.severity == "error"]
    if outcome.status == "complete" and outcome.bundle is not None:
        return EXIT_OK
    if outcome.status == "partial" and outcome.bundle is not None:
        _err(f"partial capture: {', '.join(errors)}")
        return EXIT_PARTIAL
    _err(f"capture {outcome.status}: {', '.join(errors)}")
    if outcome.status == "deferred":
        return EXIT_DEFERRED
    return _exit_for(errors)


def _summary(doc: dict[str, Any], out: Path) -> dict[str, Any]:
    return {
        "status": doc["status"],
        "out": str(out),
        "extraction_digest": doc["extraction_digest"],
        "capture": doc["capture"],
        "components": doc["components"],
        "accounting": doc["accounting"],
        "exceptions": dict(Counter(e["code"] for e in doc["exceptions"])),
        "issues": dict(Counter(i["code"] for i in doc["issues"])),
    }


def _extract(args: argparse.Namespace) -> int:

    config = _config(args.config)
    if os.path.lexists(args.out):
        raise _Invalid(f"BUNDLE_PATH_UNSAFE: {args.out} already exists; outputs are never replaced")
    doc = extract_bundle(args.bundle, config)
    try:
        publish_file(args.out, canonical_bytes(doc))
    except BundleError as exc:
        _err(f"{exc.issue.code}: {exc.issue.detail}")
        return EXIT_INVALID
    _emit(_summary(doc, args.out))
    if doc["status"] == "complete":
        return EXIT_OK
    if doc["status"] == "partial":
        return EXIT_PARTIAL
    errors = [i["code"] for i in doc["issues"] if i["severity"] == "error"]
    _err(f"extraction failed: {', '.join(errors)}")
    if any(c in _INVALID for c in errors):
        return EXIT_INVALID
    if any(c in _UNSUPPORTED for c in errors):
        return EXIT_UNSUPPORTED
    return EXIT_FAILED


def _verify(args: argparse.Namespace) -> int:

    report = verify_bundle(args.bundle, args.extraction)
    _emit(report)
    if report["verified"]:
        return EXIT_OK
    codes = [i["code"] for i in report["issues"] if i["severity"] == "error"]
    _err(f"verification failed: {', '.join(sorted(set(codes)))}")
    unreadable = {"BUNDLE_PATH_UNSAFE", "BUNDLE_MALFORMED", "SCHEMA_ROOT_UNAVAILABLE"}
    return EXIT_INVALID if report["capture_sha256"] is None or any(c in unreadable for c in codes) else EXIT_VERIFY


def _replay(args: argparse.Namespace) -> int:

    config = _config(args.config)
    report = replay_bundle(args.bundle, config, args.extraction)
    _emit(report)
    state = report["replay"]["state"]
    if report["verified"] and state in ("reproduced", "not_compared"):
        return EXIT_OK
    codes = [i["code"] for i in report["issues"] if i["severity"] == "error"]
    _err(f"replay {state}: {', '.join(sorted(set(codes)))}")
    if state == "failed" and not any(c in _INVALID for c in codes):
        return EXIT_FAILED
    if any(
        c in {"BUNDLE_PATH_UNSAFE", "BUNDLE_MALFORMED", "SCHEMA_ROOT_UNAVAILABLE", "BUNDLE_SCHEMA_INVALID"}
        for c in codes
    ):
        return EXIT_INVALID
    return EXIT_VERIFY


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else EXIT_USAGE
    handlers = {"capture": _capture, "extract": _extract, "verify": _verify, "replay": _replay}
    try:
        return handlers[args.command](args)
    except _Invalid as exc:
        _err(str(exc))
        return EXIT_INVALID
    except KeyboardInterrupt:
        _err("interrupted; nothing was published")
        return EXIT_INTERNAL
    except Exception as exc:  # a bug: report it without a traceback on stdout
        _err(f"internal error: {type(exc).__name__}: {exc}")
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
