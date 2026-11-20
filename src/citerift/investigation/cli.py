"""``citerift-investigate``: run, resume, replay, verify and show Stage 04 investigations (SPEC 13; Step 10).

Commands (every command takes ``--format text`` (default) or ``--format json``):

=============  ======================================================================================================
run            ``--request FILE`` | ``--bundle DIR`` | ``--wiki {ar,en} --revision N``, with ``--index FILE`` and
               ``--memory-root DIR`` (not with ``--request``), optional ``--lookup-budget BYTES``. Creates the
               investigation the request keys or reopens it, and runs it until it is terminal or must wait.
resume         ``--memory-root DIR --key KEY``: runs an existing investigation from its journal.
replay         ``--memory-root DIR --key KEY``: read-only, offline; reproduced, differs or stale (SPEC 10.4).
verify         ``--memory-root DIR --key KEY [--checkpoint FILE]``: read-only named checks; passed, failed,
               not_verified, corrupt, busy or stale; with a D-052 checkpoint, also compares it with the journal.
show           ``--memory-root DIR --key KEY [--claims]``: read-only diagnostics and the next legal transition.
export         ``--memory-root DIR --key KEY --out DIR``: the export directory of a verified investigation.

``resume``, ``replay``, ``verify``, ``show`` and ``export`` also take ``--index FILE`` and ``--bundle DIR``: where this
process reads the Stage 02 index (with its build manifest beside it) and the retained bundle when they moved
(Step 12, C-04, A11-6). They are operational locators only: the journal keeps the recorded paths, and the inputs are
still identified by content (D-062), so another content at the new place is STALE as it would be at the old one.
checkpoint     ``--memory-root DIR --key KEY [--out FILE [--overwrite]]``: a D-052 checkpoint, on stdout or to FILE
               outside the memory root.
=============  ======================================================================================================

Exit codes (one table for every command; ``operations.EXIT``):

====  ================  ==============================================================================================
code  status            meaning
====  ================  ==============================================================================================
0     completed         COMPLETED with outcome completed, and the command did what it was asked
1     internal          an unexpected error (a defect); nothing is exported
2     usage             the command line is wrong
3     invalid           the request, a configuration, a checkpoint or an output path is invalid or unsafe
4     not_found         no investigation with that key under the memory root
5     verify_failed     a verification check failed, a replay differs, or a checkpoint does not match
6     partial           COMPLETED with outcome partial
8     blocked           no step may start before ``not_before``: BLOCKED, or CREATED/RUNNING whose next action is to
                        wait (A11-5); nothing waits or sleeps
9     failed            FAILED: a step failed terminally
10    needs_resolution  NEEDS_RESOLUTION: verified, with an open question
11    stale             STALE, or (``verify``, ``replay``, ``export``, and ``show`` of a non-terminal investigation) an
                        input identity differs from the recorded one; also ``ENGINE_IDENTITY_DIFFERS`` (any command):
                        another engine created the investigation (E-07), nothing is written
12    corrupt           CORRUPT: the journal, a blob or the report graph is invalid
13    busy              another process holds the investigation lock
14    incomplete        CREATED or RUNNING and a step may start now (for example after a crash, before ``resume``)
====  ================  ==============================================================================================

When a command succeeds, its exit code is the investigation's status. An exit code never carries a claim class.
``run`` and ``resume`` of a terminal investigation report it and do not re-check its input identities (I-5); ``verify``
and ``replay`` do. An input that cannot be established now (a missing or unverifiable index) is refused with its code
(exit 3) and nothing is written; it is never reported as a change (MM 10.2).

JSON output (stable shape): ``{"command", "status", "exit_code", "result"}`` on success and ``{"command", "status",
"exit_code", "error": {"code", "detail"}}`` otherwise (usage and internal errors included when ``--format json`` was
given), on stdout; diagnostics go to stderr. Two exceptions: ``checkpoint`` without ``--out`` writes the checkpoint
itself, and ``verify`` of a busy or corrupt investigation is a ``result`` with ``result`` busy or corrupt. Text output
is for people and is never a scientific identity. Files are written only by ``export`` and ``checkpoint``, to the path
given.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any

from citerift.investigation import checkpoint as d052
from citerift.investigation import operations as ops
from citerift.investigation.adapters.plan import Integration
from citerift.investigation.fsutil import is_hex64
from citerift.investigation.outputs import OperationError

PROG = "citerift-investigate"


def _err(message: str) -> None:
    sys.stderr.write(message.rstrip("\n") + "\n")


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:
        self.print_usage(sys.stderr)
        _err(f"{self.prog}: error: {message}")
        raise SystemExit(ops.EXIT["usage"])


def _positive(value: str) -> int:
    if not value.isdigit() or int(value) < 1:
        raise argparse.ArgumentTypeError("a positive integer is required")
    return int(value)


def _key(value: str) -> str:
    if not is_hex64(value):
        raise argparse.ArgumentTypeError("an investigation key is 64 lowercase hex digits")
    return value


def _common(p: argparse.ArgumentParser, *, key: bool = True) -> None:
    p.add_argument("--format", choices=["text", "json"], default="text")
    if key:
        p.add_argument("--memory-root", type=Path, required=True)
        p.add_argument("--key", type=_key, required=True)


def _exit_table() -> str:
    doc = __doc__ or ""
    start = doc.index("Exit codes")
    return doc[start : doc.index("JSON output")].rstrip()


def _locators(p: argparse.ArgumentParser) -> None:
    p.add_argument("--index", type=Path, help="read the Stage 02 index from here (its manifest beside it)")
    p.add_argument("--bundle", type=Path, help="read the retained Stage 03 bundle from here")


def parser() -> argparse.ArgumentParser:
    p = _Parser(
        prog=PROG,
        description="CITERIFT Stage 04 investigations of one pinned Wikipedia article revision",
        epilog=_exit_table(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True, parser_class=_Parser)
    r = sub.add_parser("run", help="create or reopen the investigation of a request and run it")
    _common(r, key=False)
    src = r.add_mutually_exclusive_group(required=True)
    src.add_argument("--request", type=Path, help="a request JSON file (request schema 2.0.0)")
    src.add_argument("--bundle", type=Path, help="a retained Stage 03 capture bundle")
    src.add_argument("--wiki", choices=["ar", "en"], help="a live capture of --revision on this wiki")
    r.add_argument("--revision", type=_positive)
    r.add_argument("--index", type=Path, help="the Stage 02 index file")
    r.add_argument("--memory-root", type=Path)
    r.add_argument("--lookup-budget", type=_positive, help="lookup evidence budget in bytes (D-048)")
    for name, text in (
        ("resume", "run an existing investigation from its journal"),
        ("replay", "re-derive and compare, read-only and offline (SPEC 10.4)"),
        ("show", "diagnostics and the next legal transition, read-only"),
    ):
        c = sub.add_parser(name, help=text)
        _common(c)
        _locators(c)
        if name == "show":
            c.add_argument("--claims", action="store_true", help="also print each claim's explanation")
    v = sub.add_parser("verify", help="named verification checks, read-only")
    _common(v)
    _locators(v)
    v.add_argument("--checkpoint", type=Path, help="a D-052 checkpoint to compare with the journal")
    e = sub.add_parser("export", help="write the export directory of a verified investigation")
    _common(e)
    _locators(e)
    e.add_argument("--out", type=Path, required=True, help="a new directory outside the memory root")
    k = sub.add_parser("checkpoint", help="write a D-052 external journal checkpoint")
    _common(k)
    k.add_argument("--out", type=Path, help="a file outside the memory root (default: standard output)")
    k.add_argument("--overwrite", action="store_true", help="replace an existing checkpoint file")
    return p


def _request(args: argparse.Namespace) -> dict[str, Any]:
    if args.request is not None:
        if args.index or args.memory_root or args.revision or args.lookup_budget:
            raise OperationError("usage", "USAGE", "--request carries the index, memory root and configuration")
        return ops.read_request(args.request)
    if args.index is None or args.memory_root is None:
        raise OperationError("usage", "USAGE", "--index and --memory-root are required")
    root = args.memory_root.absolute()
    if args.bundle is not None:
        if args.revision is not None:
            raise OperationError("usage", "USAGE", "--revision belongs to --wiki")
        return ops.retained_request(args.bundle.absolute(), args.index.absolute(), root, budget=args.lookup_budget)
    if args.revision is None:
        raise OperationError("usage", "USAGE", "--wiki needs --revision")
    return ops.live_request(args.wiki, args.revision, args.index.absolute(), root, budget=args.lookup_budget)


def dispatch(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    if args.command == "run":
        return ops.run(_request(args))
    root = args.memory_root.absolute()
    locators = {
        name: str(value.absolute())
        for name, value in (
            ("index_path", getattr(args, "index", None)),
            ("bundle_path", getattr(args, "bundle", None)),
        )
        if value is not None
    }
    if args.command == "resume":
        return ops.resume(root, args.key, locators=locators)
    integration = Integration(locators=locators)
    if args.command == "replay":
        return ops.replay(root, args.key, integration=integration)
    if args.command == "verify":
        return ops.verify(root, args.key, checkpoint=args.checkpoint, integration=integration)
    if args.command == "show":
        return ops.show(root, args.key, explain_claims=args.claims, integration=integration)
    if args.command == "export":
        return ops.export(root, args.key, args.out.absolute(), integration=integration)
    return ops.checkpoint(root, args.key, args.out.absolute() if args.out else None, overwrite=args.overwrite)


STATUS_OF_CODE = {code: status for status, code in ops.EXIT.items()}


def _text(command: str, status: str, code: int, result: dict[str, Any]) -> str:
    lines = [f"{command}: {status} (exit {code})"]
    for k in (
        "investigation_key",
        "investigation_id",
        "lifecycle",
        "result",
        "changed",
        "code",
        "detail",
        "first_difference",
        "exported",
    ):
        if result.get(k) is not None:
            v = result[k]
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}")
    if isinstance(result.get("stale"), dict):
        lines.append(f"changed: {json.dumps(result['stale']['changed'])}")
    if result.get("claims_by_class"):
        lines.append("claims: " + ", ".join(f"{k} {v}" for k, v in result["claims_by_class"].items()))
    if "steps" in result:
        for s in result["steps"]:
            nb = f", not_before {s['not_before']}" if s["not_before"] else ""
            lines.append(f"  {s['step']:<9} {s['state']:<16} attempts {s['attempts']}{nb}")
    nxt = result.get("next")
    if nxt:
        what = " ".join(str(x) for x in (nxt["action"], nxt.get("step")) if x)
        why = nxt.get("reason") or f"{nxt.get('code')}: {nxt.get('detail')}"
        lines.append(f"next: {what} (rule {nxt['rule']}): {why}")
        if nxt.get("changed"):
            lines.append(f"changed: {json.dumps(nxt['changed'])}")
    if result.get("terminated_by"):
        lines.append(f"terminated by: {json.dumps(result['terminated_by'], ensure_ascii=False)}")
    rep = result.get("report")
    if isinstance(rep, dict):
        lines.append(f"report {rep['report']} outcome {rep['outcome']}; projections {rep['projection_count']}")
        lines.append(rep["summary"])
        lines += [f"  limitation {lim['code']}: {lim['text']}" for lim in rep["limitations"]]
        for c in rep.get("claims", []):
            lines.append(f"  [{c['kind']}] {c['text']} {c['chain']}")
    for c in result.get("checks", []):
        detail = f": {c['detail']}" if c.get("detail") and not c["passed"] else ""
        lines.append(f"  {'PASS' if c['passed'] else 'FAIL'} {c['check']}{detail}")
    if "checkpoint" in result:
        cp = result["checkpoint"]
        lines.append(json.dumps(cp, sort_keys=True) if "format" in cp else f"checkpoint: {cp.get('result')}")
    if result.get("statement"):
        lines.append(result["statement"])
    return "\n".join(_printable(line) for line in lines) + "\n"


def _printable(line: str) -> str:
    """Text output only (SD-09): control and bidirectional formatting characters are shown escaped."""
    return "".join(c if c == "\t" or unicodedata.category(c) not in ("Cc", "Cf") else f"\\u{ord(c):04x}" for c in line)


MEMORY_ROOT_PLACEHOLDER = "<memory-root>"


def _effective_root(args: argparse.Namespace) -> Path | None:
    """The memory root a command works in: ``--memory-root``, or for ``run --request`` the request's ``memory_root``
    (reviewer finding E-03 of the final cycle). A request that cannot be read gives none here; its own error is
    raised by ``dispatch`` and names only the request file."""
    root = getattr(args, "memory_root", None)
    if root is not None:
        return Path(root)
    if getattr(args, "request", None) is None:
        return None
    try:
        value = ops.read_request(args.request).get("memory_root")
    except OperationError:
        return None
    return Path(value) if isinstance(value, str) and value else None


def _redactor(args: argparse.Namespace) -> Callable[[Any], Any]:
    """Reviewer finding E-05 (owner decision D-083): what the command line prints never carries the absolute memory
    root (an account or session locator). Every absolute spelling of the effective root (absolute, resolved) is
    replaced by ``<memory-root>`` in any output string, error details included, where it stands as a whole path: not
    preceded by a path character and not followed by a word character, ``~`` or ``-`` (reviewer finding E-04: a
    relative spelling, or a bare substring match, could rewrite digests and identifiers).
    The journal and Memory itself are not changed."""
    root = _effective_root(args)
    if root is None:
        return lambda value: value
    spellings: set[str] = set()
    for spell in (Path.absolute, Path.resolve):
        try:
            spellings.add(str(spell(root)))
        except (OSError, RuntimeError):
            continue
    ordered = sorted((s for s in spellings if s.startswith("/") and len(s) > 1), key=len, reverse=True)
    if not ordered:
        return lambda value: value
    pattern = re.compile(r"(?<![\w.~/-])(?:" + "|".join(re.escape(s) for s in ordered) + r")(?![\w~-])")

    def redact(value: Any) -> Any:
        if isinstance(value, str):
            return pattern.sub(MEMORY_ROOT_PLACEHOLDER, value)
        if isinstance(value, dict):
            return {k: redact(v) for k, v in value.items()}
        if isinstance(value, list | tuple):
            return [redact(v) for v in value]
        return value

    return redact


def _json_error(command: str | None, status: str, code: str, detail: str) -> None:
    out = {
        "command": command,
        "status": status,
        "exit_code": ops.EXIT[status],
        "error": {"code": code, "detail": detail},
    }
    sys.stdout.write(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parser().parse_args(argv)
    except SystemExit as exc:
        code = int(exc.code) if isinstance(exc.code, int) else ops.EXIT["usage"]
        if code == ops.EXIT["usage"] and _wants_json(raw):  # UF-05: the JSON envelope for a usage error too
            _json_error(raw[0] if raw and not raw[0].startswith("-") else None, "usage", "USAGE", "see standard error")
        return code
    fmt = getattr(args, "format", "text")
    redact = _redactor(args)
    try:
        result, code = dispatch(args)
    except OperationError as exc:
        code = ops.EXIT[exc.status]
        detail = redact(exc.detail)
        if fmt == "json":
            out = {"command": args.command, "status": exc.status, "exit_code": code}
            out["error"] = {"code": exc.code, "detail": detail}
            sys.stdout.write(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        _err(f"{PROG} {args.command}: {exc.status}: {exc.code}: {detail}")
        return code
    except Exception as exc:  # a defect: report it, export nothing
        _err(redact(f"{PROG} {args.command}: internal error: {type(exc).__name__}: {exc}"))
        if fmt == "json":
            _json_error(args.command, "internal", "INTERNAL", redact(f"{type(exc).__name__}: {exc}")[:500])
        return ops.EXIT["internal"]
    status = STATUS_OF_CODE[code]
    if args.command == "checkpoint" and args.out is None:  # the checkpoint bytes are written as made, never redacted
        sys.stdout.write(d052.encode(result["checkpoint"]).decode("utf-8"))
        _err(redact(result["statement"]))
        return code
    result = redact(result)
    if fmt == "json":
        out = {"command": args.command, "status": status, "exit_code": code, "result": result}
        sys.stdout.write(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(_text(args.command, status, code, result))
    return code


def _wants_json(raw: list[str]) -> bool:
    return any(a == "--format=json" or (a == "--format" and raw[i + 1 : i + 2] == ["json"]) for i, a in enumerate(raw))


if __name__ == "__main__":
    sys.exit(main())
