"""``citerift-gov``: command-line interface to the Project Orchestrator.

Inspection commands are read-only. Commands that change the registry are
dry-runs unless ``--apply`` is given, and every change is validated first.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from citerift.contracts.formats import loads_strict
from citerift.governance import evidence, gitutil
from citerift.governance.model import EDGES, Actor, Status
from citerift.governance.orchestrator import (
    STATUS_DOC_PATH,
    Finding,
    GovernanceError,
    Orchestrator,
    errors,
    find_root,
)


def _print_findings(findings: list[Finding]) -> None:
    for f in findings:
        print(f"  {f}")


def _emit(args: argparse.Namespace, data: Any, text: str) -> None:
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(text)


def cmd_status(orc: Orchestrator, args: argparse.Namespace) -> int:
    rows = [{"id": s["id"], "name": s["name"], "status": s["status"]} for s in orc.stages]
    text = "\n".join(f"{r['id']}  {r['status']:<36} {r['name']}" for r in rows)
    text += "\n\nNext actions:\n" + "\n".join(f"- {a}" for a in orc.next_actions())
    _emit(args, {"stages": rows, "next_actions": orc.next_actions()}, text)
    return 0


def cmd_deps(orc: Orchestrator, args: argparse.Namespace) -> int:
    info = orc.dependencies(args.stage)
    text = (
        f"Stage {info['stage']} depends on: {', '.join(info['depends_on']) or 'nothing'}\n"
        f"Dependents: {', '.join(info['dependents']) or 'none'}\n"
        f"Unsatisfied (not ACCEPTED_CLOSED): {', '.join(info['unsatisfied']) or 'none'}"
    )
    _emit(args, info, text)
    return 0


def cmd_transitions(orc: Orchestrator, args: argparse.Namespace) -> int:
    rows = [
        {"from": e.source.value, "to": e.target.value, "owner_only": e.owner_only, "meaning": e.meaning} for e in EDGES
    ]
    text = "\n".join(
        f"{r['from']:<36} -> {r['to']:<36} {'OWNER ' if r['owner_only'] else '      '}{r['meaning']}" for r in rows
    )
    _emit(args, rows, text)
    return 0


def cmd_check(orc: Orchestrator, args: argparse.Namespace) -> int:
    findings = orc.check()
    errs = errors(findings)
    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        print(f"Consistency check: {len(errs)} errors, {len(findings) - len(errs)} warnings")
        _print_findings(findings)
    return 1 if errs else 0


def cmd_readiness(orc: Orchestrator, args: argparse.Namespace) -> int:
    findings = orc.readiness(args.stage)
    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        print(f"Stage {args.stage} verification readiness: {'READY' if not errors(findings) else 'NOT READY'}")
        _print_findings(findings)
    return 1 if errors(findings) else 0


def _parse_gates(values: list[str]) -> dict[str, Any]:
    gates: dict[str, Any] = {}
    for value in values:
        gid, _, rest = value.partition("=")
        result, _, refs = rest.partition(":")
        if not gid or not result or not refs:
            raise SystemExit(f"--gate must look like ID=RESULT:EVIDENCE[,EVIDENCE], got {value!r}")
        gates[gid] = {"result": result, "evidence": [r for r in refs.split(",") if r]}
    return gates


def cmd_transition(orc: Orchestrator, args: argparse.Namespace) -> int:
    gates: dict[str, Any] = {}
    ci = None
    if args.record:
        try:
            record = loads_strict(Path(args.record).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"error: cannot read --record {args.record}: {exc}", file=sys.stderr)
            return 2
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("gates", {}), dict)
            or not isinstance(record.get("ci"), dict | None)
        ):
            print(f"error: --record {args.record} must be an object with 'gates' and 'ci' objects", file=sys.stderr)
            return 2
        gates = record.get("gates", {})
        ci = record.get("ci")
    gates.update(_parse_gates(args.gate or []))
    result = orc.propose(
        args.stage,
        Status(args.to),
        actor=Actor(args.actor),
        reason=args.reason,
        owner_ref=args.owner_ref,
        recorded_by=Actor(args.recorded_by),
        revision=args.revision,
        gates=gates,
        ci=ci,
        amendment=args.amendment,
        at=args.at,
    )
    verdict = "ALLOWED" if result.allowed else "REJECTED"
    print(f"Transition stage {args.stage} -> {args.to}: {verdict}")
    _print_findings(result.findings)
    if not result.allowed:
        return 1
    if args.apply:
        orc.apply(result)
        print(f"Applied. Updated governance/stage_registry.json and {STATUS_DOC_PATH}.")
    else:
        print("Dry run: nothing written. Re-run with --apply to record it.")
    return 0


def cmd_blocker(orc: Orchestrator, args: argparse.Namespace) -> int:
    try:
        if args.action == "add":
            bid = orc.add_blocker(args.stage, args.text, at=args.at)
            print(f"Recorded blocker {bid}")
        else:
            unblocked = orc.resolve_blocker(
                args.stage,
                args.id,
                args.text,
                at=args.at,
                actor=Actor(args.actor),
                recorded_by=Actor(args.recorded_by),
            )
            print(f"Resolved blocker {args.id}" + ("; stage returned to IN_PROGRESS" if unblocked else ""))
    except GovernanceError as exc:
        print("REJECTED")
        _print_findings(exc.findings)
        return 1
    return 0


def cmd_amend(orc: Orchestrator, args: argparse.Namespace) -> int:
    try:
        aid = orc.add_amendment(
            args.stage,
            kind=args.kind,
            reason=args.reason,
            evidence_refs=args.evidence,
            owner_ref=args.owner_ref,
            revision=args.revision,
            test_report=args.test_report,
            at=args.at,
        )
    except GovernanceError as exc:
        print("REJECTED")
        _print_findings(exc.findings)
        return 1
    print(f"Recorded amendment {aid}")
    return 0


def cmd_handoff(orc: Orchestrator, args: argparse.Namespace) -> int:
    print(orc.handoff_summary(args.stage), end="")
    return 0


def cmd_render_status(orc: Orchestrator, args: argparse.Namespace) -> int:
    text = orc.render_status()
    path = orc.root / STATUS_DOC_PATH
    if args.write:
        path.write_text(text, encoding="utf-8")
        print(f"Wrote {STATUS_DOC_PATH}")
        return 0
    if args.check:
        try:
            current = path.read_text(encoding="utf-8") if path.is_file() else ""
        except UnicodeDecodeError:
            current = None  # not UTF-8 text, so it is out of date (X-05)
        if current != text:
            print(f"{STATUS_DOC_PATH} is out of date")
            return 1
        print(f"{STATUS_DOC_PATH} is up to date")
        return 0
    print(text, end="")
    return 0


def cmd_recover(orc: Orchestrator, args: argparse.Namespace) -> int:
    data = orc.recover()
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    out = [
        f"CITERIFT recovery report for {data['repository']}",
        f"HEAD: {data['head']} on {data['branch']}",
        f"Uncommitted changes: {len(data['uncommitted_changes'] or [])}",
        "",
        "Authoritative revisions:",
        *[
            f"  stage {k}: verified {v['verified']}, accepted {v['accepted']}"
            for k, v in data["authoritative_revisions"].items()
        ],
        f"Completed and accepted: {', '.join(data['completed_and_accepted']) or 'none'}",
        f"Verified, awaiting owner acceptance: {', '.join(data['verified_awaiting_owner_acceptance']) or 'none'}",
        "Open:",
        *[f"  {k}: {', '.join(v)}" for k, v in data["open"].items()],
        f"Not started: {', '.join(data['not_started']) or 'none'}",
        "Open blockers:",
        *([f"  {b['stage']} {b['id']}: {b['description']}" for b in data["open_blockers"]] or ["  none"]),
        "Open risks, defects and limitations:",
        *(
            [
                f"  {r['id']} [{r['severity']} {r['kind']}, stage {r['stage']}]: {r['title']}"
                for r in data["open_risks_and_limitations"]
            ]
            or ["  none"]
        ),
        "Pending decisions:",
        *([f"  {d['id']}: {d['title']}" for d in data["pending_decisions"]] or ["  none"]),
        "Recent changes:",
        *[f"  {h['at']} stage {h['stage']} {h['from']} -> {h['to']} ({h['actor']})" for h in data["recent_changes"]],
        "Next actions:",
        *[f"  - {a}" for a in data["next_actions"]],
        f"Consistency: {len(data['consistency']['errors'])} errors, {len(data['consistency']['warnings'])} warnings",
        *[f"  ERROR {e['code']}: {e['message']}" for e in data["consistency"]["errors"]],
    ]
    print("\n".join(out))
    return 0


def cmd_check_report(orc: Orchestrator, args: argparse.Namespace) -> int:
    """Check a test report as verification would, against HEAD: CI runs this on its own report (O-6)."""
    try:
        stage = orc.stage(args.stage)
    except KeyError as exc:
        print(f"ERROR STAGE_UNKNOWN: {exc}")
        return 2
    revision = gitutil.head(orc.root)
    if revision is None:
        print("ERROR REVISION_NOT_FOUND: HEAD cannot be read")
        return 1
    problems = evidence.check_test_report(orc.root, args.report, None, revision, stage["required_test_suites"])
    for p in problems:
        print(f"ERROR {p.code}: {p.message}")
    print(f"Test report {args.report} at {revision[:12]}: {len(problems)} problems")
    return 1 if problems else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="citerift-gov", description="CITERIFT Project Orchestrator")
    p.add_argument("--root", type=Path, help="repository root (default: search upwards from cwd)")
    p.add_argument("--json", action="store_true", help="machine-readable output where supported")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="show stage states and next actions").set_defaults(func=cmd_status)
    d = sub.add_parser("deps", help="show a stage's dependencies")
    d.add_argument("stage")
    d.set_defaults(func=cmd_deps)
    sub.add_parser("transitions", help="list the permitted transitions").set_defaults(func=cmd_transitions)
    sub.add_parser("check", help="validate registry, history, evidence and memory (exit 1 on error)").set_defaults(
        func=cmd_check
    )
    r = sub.add_parser("readiness", help="report what blocks verification of a stage")
    r.add_argument("stage")
    r.set_defaults(func=cmd_readiness)

    t = sub.add_parser("transition", help="validate (and with --apply, record) a stage transition")
    t.add_argument("stage")
    t.add_argument("to", choices=[s.value for s in Status])
    t.add_argument("--actor", required=True, choices=[a.value for a in Actor])
    t.add_argument("--recorded-by", default=Actor.ENGINEERING_AGENT.value, choices=[a.value for a in Actor])
    t.add_argument("--reason", required=True)
    t.add_argument("--owner-ref", help="reference to the owner's own statement (owner decisions)")
    t.add_argument("--revision", help="implementation, verified or accepted revision (full SHA)")
    t.add_argument("--gate", action="append", help="ID=RESULT:EVIDENCE[,EVIDENCE]")
    t.add_argument("--record", help="JSON file with 'gates' and 'ci' for a verification")
    t.add_argument("--amendment", help="correction amendment id when reopening an accepted stage")
    t.add_argument("--at", help="timestamp override (YYYY-MM-DDTHH:MM:SSZ)")
    t.add_argument("--apply", action="store_true", help="write the change if it is allowed")
    t.set_defaults(func=cmd_transition)

    b = sub.add_parser("blocker", help="record or resolve a blocker")
    b.add_argument("action", choices=["add", "resolve"])
    b.add_argument("stage")
    b.add_argument("text", help="description (add) or resolution (resolve)")
    b.add_argument("--id", help="blocker id to resolve")
    b.add_argument(
        "--actor",
        default=Actor.ENGINEERING_AGENT.value,
        choices=[a.value for a in Actor],
        help="who resolved the blocker (also the actor of BLOCKED -> IN_PROGRESS)",
    )
    b.add_argument("--recorded-by", default=Actor.ENGINEERING_AGENT.value, choices=[a.value for a in Actor])
    b.add_argument("--at")
    b.set_defaults(func=cmd_blocker)

    a = sub.add_parser("amend", help="record an amendment to an accepted stage")
    a.add_argument("stage")
    a.add_argument("--kind", required=True, choices=["correction", "enhancement"])
    a.add_argument("--reason", required=True)
    a.add_argument("--evidence", action="append", required=True)
    a.add_argument("--owner-ref", required=True)
    a.add_argument("--revision")
    a.add_argument("--test-report")
    a.add_argument("--at")
    a.set_defaults(func=cmd_amend)

    h = sub.add_parser("handoff", help="print an auditable handoff summary")
    h.add_argument("stage")
    h.set_defaults(func=cmd_handoff)

    rs = sub.add_parser("render-status", help="render PROJECT_STATUS.md from the registry")
    g = rs.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    rs.set_defaults(func=cmd_render_status)

    sub.add_parser("recover", help="reconstruct project state from the repository alone").set_defaults(func=cmd_recover)

    cr = sub.add_parser("check-report", help="check a test report against HEAD as verification would")
    cr.add_argument("report", help="repository-relative path of the report")
    cr.add_argument("--stage", default="00", help="stage whose required suites apply")
    cr.set_defaults(func=cmd_check_report)
    return p


def _git_hint(root: Path, command: str) -> int:
    if command == "recover" and gitutil.is_repository(root):
        print(f"HEAD: {gitutil.head(root)} on {gitutil.branch(root)}")
        try:
            print(f"Uncommitted changes: {', '.join(gitutil.dirty_paths(root)) or 'none'}")
        except gitutil.GitUnavailableError as exc:
            print(f"Uncommitted changes: unknown ({exc})")
        print("Restore the registry from git (git log -- governance/stage_registry.json) before any other step.")
    return 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = args.root or find_root(Path.cwd())
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        orc = Orchestrator(root)
    except (OSError, ValueError) as exc:
        # A damaged registry is reported, never a traceback (F-13); recover still prints what git knows.
        print(f"ERROR REGISTRY_UNREADABLE: governance/stage_registry.json cannot be read: {exc}")
        return _git_hint(root, args.command)
    try:
        schema_errors = orc.schema_findings()
    except (OSError, ValueError) as exc:
        print(f"ERROR REGISTRY_SCHEMA_UNREADABLE: schemas/governance/stage_registry.schema.json cannot be read: {exc}")
        return _git_hint(root, args.command)
    if schema_errors and args.command != "check":
        # Every other command relies on the registry's structure; refuse instead of failing half-way (V-10).
        for f in schema_errors:
            print(f)
        print("The registry does not match its schema; run `citerift-gov check` and restore it from git.")
        return _git_hint(root, args.command)
    stage_id = getattr(args, "stage", None)
    if stage_id is not None and stage_id not in {s["id"] for s in orc.stages}:
        print(f"ERROR STAGE_UNKNOWN: [stage {stage_id}] no such stage in the registry")
        return 2
    if args.command == "blocker" and args.action == "resolve" and not args.id:
        print("error: blocker resolve needs --id", file=sys.stderr)
        return 2
    try:
        result: int = args.func(orc, args)
    except gitutil.GitUnavailableError as exc:
        # Last resort for a damaged repository (for example a broken index) that a check did not catch (Y-11).
        print(f"ERROR REVISION_UNVERIFIABLE: git cannot read the repository: {exc}")
        return 1
    return result


if __name__ == "__main__":
    raise SystemExit(main())
