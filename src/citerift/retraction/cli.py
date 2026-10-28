"""``citerift-rde``: the Retraction Data Engine command line (SPECIFICATION.md 10.2).

JSON goes to stdout and diagnostics to stderr. Exit codes: 0 result produced (including no_record),
2 usage, 3 invalid_query, 4 unavailable, 5 verification failed, 6 import failed, 7 enrichment stopped,
1 internal error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from citerift.retraction import ambiguity, local_model, tension
from citerift.retraction.ambiguity import suggest
from citerift.retraction.corroboration import enrich
from citerift.retraction.export import diff, export, verify
from citerift.retraction.query import Index, event_detail, lookup, normalize_query
from citerift.retraction.source import ImportFailure, load_receipt
from citerift.retraction.store import IndexUnavailable, build, manifest_path_for

EXIT_OK, EXIT_INTERNAL, EXIT_USAGE, EXIT_INVALID, EXIT_UNAVAILABLE, EXIT_VERIFY, EXIT_IMPORT, EXIT_ENRICH = (
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
)


DEFAULT_MODEL_MANIFEST = Path(__file__).parent / "model_manifests" / "mxbai-rerank-base-v2.json"


def _emit(data: Any) -> None:
    sys.stdout.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def _err(message: str) -> None:
    sys.stderr.write(message.rstrip("\n") + "\n")


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:  # argparse exits 2 on usage errors already; keep the message on stderr
        self.print_usage(sys.stderr)
        _err(f"{self.prog}: error: {message}")
        raise SystemExit(EXIT_USAGE)


def _parser() -> argparse.ArgumentParser:
    p = _Parser(prog="citerift-rde", description="CITERIFT Retraction Data Engine")
    sub = p.add_subparsers(dest="command", required=True, parser_class=_Parser)
    b = sub.add_parser("build", help="build an index from the pinned CSV (no network)")
    b.add_argument("--source", type=Path, required=True)
    b.add_argument("--receipt", type=Path, help="receipt JSON (default: the packaged pinned receipt)")
    b.add_argument("--out-dir", type=Path, required=True)
    b.add_argument("--corroboration", type=Path, help="Crossref replay manifest.json")
    for name in ("lookup", "tension"):
        q = sub.add_parser(name)
        q.add_argument("--index", type=Path, required=True)
        q.add_argument("--doi")
        q.add_argument("--pmid")
        if name == "lookup":
            q.add_argument("--page-size", type=int, default=20)
            q.add_argument("--cursor")
        else:
            q.add_argument(
                "--intervention",
                action="append",
                choices=list(tension.INTERVENTIONS),
            )
            q.add_argument("--origin", action="append", default=[])
    e = sub.add_parser("event")
    e.add_argument("--index", type=Path, required=True)
    e.add_argument("event_id")
    v = sub.add_parser("verify")
    v.add_argument("--index", type=Path, required=True)
    v.add_argument("--source", type=Path)
    x = sub.add_parser("export")
    x.add_argument("--index", type=Path, required=True)
    x.add_argument("--out", type=Path, required=True)
    d = sub.add_parser("diff")
    d.add_argument("--old", type=Path, required=True)
    d.add_argument("--new", type=Path, required=True)
    n = sub.add_parser("enrich", help="bounded Crossref retrieval into a replay bundle (network)")
    n.add_argument("--index", type=Path, required=True)
    n.add_argument("--dois-file", type=Path, required=True)
    n.add_argument("--out-dir", type=Path, required=True)
    a = sub.add_parser("ambiguity")
    a.add_argument("--index", type=Path, required=True)
    a.add_argument("--event", required=True)
    a.add_argument("--tau-s", type=float, default=ambiguity.FROZEN_TAU_S)
    a.add_argument("--tau-m", type=float, default=ambiguity.FROZEN_TAU_M)
    a.add_argument("--model-dir", type=Path, help="local weights directory: also rank with the pinned open model")
    a.add_argument("--model-manifest", type=Path, default=DEFAULT_MODEL_MANIFEST)
    return p


def _open(path: Path) -> Any:
    return Index(path)


def _model_assessment(ix: Index, args: argparse.Namespace) -> dict[str, Any]:
    """Advisory ranking by the local open model (AI Protocol v2). It never changes the baseline output."""
    probe = ambiguity.probe_for_event(ix, args.event)
    bundle = ambiguity.model_bundle(ix, args.event, ambiguity.Baseline(ix).candidates(probe))
    try:
        manifest = local_model.load_manifest(args.model_manifest)
    except (OSError, ValueError) as exc:
        return {"decision": "abstain", "reason_codes": ["MANIFEST_INVALID"], "problems": [str(exc)], "advisory": True}
    except local_model.ModelUnavailable as exc:
        return {"decision": "abstain", "reason_codes": [exc.code], "problems": [exc.detail], "advisory": True}
    return local_model.LocalAmbiguityModel(args.model_dir).rank(bundle, manifest).to_json()


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            result = build(args.source, load_receipt(args.receipt), args.out_dir, corroboration=args.corroboration)
            _emit({"index": str(result.index_path), "manifest": str(result.manifest_path), **result.manifest})
            return EXIT_OK
        if args.command == "lookup":
            if args.doi is None and args.pmid is None:
                _err("lookup needs --doi, --pmid or both")
                return EXIT_USAGE
            out = lookup(args.index, args.doi, args.pmid, page_size=args.page_size, cursor=args.cursor)
            _emit(out)
            return {"invalid_query": EXIT_INVALID, "unavailable": EXIT_UNAVAILABLE}.get(out["lookup_state"], EXIT_OK)
        if args.command == "tension":
            if args.doi is None and args.pmid is None:
                _err("tension needs --doi, --pmid or both")
                return EXIT_USAGE
            if not normalize_query(args.doi, args.pmid)[2]:
                _emit({"lookup_state": "invalid_query", "query": normalize_query(args.doi, args.pmid)[0]})
                return EXIT_INVALID
            with _open(args.index) as ix:
                ev = ix.gather(args.doi, args.pmid)
                plan = None
                if args.intervention:
                    plan = []
                    for name in args.intervention:
                        if name == "exclude_origin":
                            if not 1 <= len(args.origin) <= tension.MAX_ORIGINS_PER_CALL:
                                _err("exclude_origin needs one or two --origin values")
                                return EXIT_USAGE
                            plan.append((name, tuple(args.origin)))
                        else:
                            plan.append((name, ()))
                _emit(tension.report(ev, ix.snapshot_id, plan))
            return EXIT_OK
        if args.command == "event":
            with _open(args.index) as ix:
                detail = event_detail(ix, args.event_id)
            if detail is None:
                _err(f"no event {args.event_id}")
                return EXIT_INVALID
            _emit(detail)
            return EXIT_OK
        if args.command == "verify":
            with _open(args.index) as ix:
                report = verify(ix.conn, args.source, manifest_path_for(args.index))
            _emit(report)
            return EXIT_OK if report["ok"] else EXIT_VERIFY
        if args.command == "export":
            with _open(args.index) as ix:
                _emit(export(ix.conn, args.out))
            return EXIT_OK
        if args.command == "diff":
            with _open(args.old) as old, _open(args.new) as new:
                _emit(diff(old.conn, new.conn))
            return EXIT_OK
        if args.command == "enrich":
            with _open(args.index):
                pass  # the index must be readable; works are chosen by the caller
            dois = [line.strip() for line in args.dois_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            manifest = enrich(dois, args.out_dir)
            _emit({k: v for k, v in manifest.items() if k != "works"} | {"works": len(manifest["works"])})
            return EXIT_ENRICH if manifest["stopped"] else EXIT_OK
        if args.command == "ambiguity":
            with _open(args.index) as ix:
                try:
                    out = suggest(ix, args.event, args.tau_s, args.tau_m)
                    if args.model_dir is not None and out["decision"] != "exact":
                        out["model_assessment"] = _model_assessment(ix, args)
                except KeyError:
                    _err(f"no event {args.event}")
                    return EXIT_INVALID
            _emit(out)
            return EXIT_OK
    except IndexUnavailable as exc:
        _emit({"lookup_state": "unavailable", "code": exc.code, "detail": str(exc)})
        return EXIT_UNAVAILABLE
    except ImportFailure as exc:
        _emit({"import_failed": exc.to_json()})
        return EXIT_IMPORT
    except ValueError as exc:  # QueryError and TensionError are ValueErrors: usage problems
        _err(str(exc))
        return EXIT_USAGE
    return EXIT_USAGE


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else EXIT_USAGE
    except Exception as exc:
        _err(f"internal error: {type(exc).__name__}: {exc}")
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
