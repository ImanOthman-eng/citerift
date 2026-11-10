"""Consistency check of the Stage 04 Step 3 documents (SPECIFICATION, MATHEMATICAL_MODEL, RISK_ANALYSIS).

Checks cross-references and table structure only. It does not evaluate the decision table or the state machines on
inputs: that is the reference model and the state-space enumeration of Step 4.

Usage: python check_step3_docs.py <repository root>
Prints one line per check and ends with RESULT: PASS or RESULT: FAIL (exit status 0 or 1).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

GATES = [f"04-{c}" for c in "ABCDEFGHIJ"]


def section(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[i:j]


def table_rows(block: str) -> list[list[str]]:
    rows = []
    for line in block.splitlines():
        if line.startswith("|") and not re.match(r"^\|[-| ]+\|$", line):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows[1:]  # drop the header row


def codes(cell: str) -> list[str]:
    return re.findall(r"`([A-Z][A-Z_]+)`", cell)


class Report:
    def __init__(self) -> None:
        self.failed = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f": {detail}" if detail and not ok else ""))


def main(root: Path) -> int:
    d = root / "docs/verification/stage-04"
    spec = (d / "SPECIFICATION.md").read_text(encoding="utf-8")
    mm = (d / "MATHEMATICAL_MODEL.md").read_text(encoding="utf-8")
    ra = (d / "RISK_ANALYSIS.md").read_text(encoding="utf-8")
    review = (d / "review/step3/STEP3_ADVERSARIAL_REVIEW.md").read_text(encoding="utf-8")
    registry = json.loads((root / "governance/stage_registry.json").read_text(encoding="utf-8"))
    r = Report()

    # Gates: registry, specification traceability, risks.
    stage = next(s for s in registry["stages"] if s["id"] == "04")
    reg_gates = [g["id"] for g in stage["acceptance_gates"]]
    r.check("registry gates are 04-A to 04-J", reg_gates == GATES, str(reg_gates))
    trace = {row[0]: row for row in table_rows(section(spec, "### 17.1 Gates", "### 17.2"))}
    r.check("SPEC 17.1 lists every gate once", sorted(trace) == GATES, str(sorted(trace)))
    for g in GATES:
        row = trace.get(g, ["", "", "", ""])
        r.check(f"{g} has specification, model and risk entries", all(row[1:4]) and "R4-" in row[3], str(row))

    # Risks: contiguous ids, every risk under a gate, summary gates equal SPEC 17.1.
    heads = re.findall(r"^### (R4-\d\d) ", ra, flags=re.M)
    ids = sorted(heads)
    r.check("RA risk ids unique", len(ids) == len(set(ids)), str(ids))
    r.check("RA risk ids contiguous from R4-01", ids == [f"R4-{i:02d}" for i in range(1, len(ids) + 1)], str(ids))
    summary = {row[0]: row for row in table_rows(section(ra, "## 5. Summary", "## 6."))}
    r.check("RA summary lists every risk", sorted(summary) == ids, str(sorted(set(ids) ^ set(summary))))
    risk_gates: dict[str, set[str]] = {i: set() for i in ids}
    for g in GATES:
        for rid in re.findall(r"R4-\d\d", trace.get(g, ["", "", "", ""])[3]):
            risk_gates.setdefault(rid, set()).add(g)
    for rid in ids:
        listed = set(re.findall(r"04-[A-J]", summary.get(rid, ["", "", ""])[2]))
        block = section(ra + "\n### R4-99 ", f"### {rid} ", "\n### ")
        in_block = set(re.findall(r"04-[A-J]", block.split("Gate and invariant:")[1].split("\n")[0]))
        r.check(
            f"{rid} gates agree (SPEC 17.1, RA block, RA summary)",
            bool(listed) and listed == risk_gates[rid] == in_block,
            f"spec {sorted(risk_gates[rid])} block {sorted(in_block)} summary {sorted(listed)}",
        )
        for field in (
            "Cause:",
            "Detection:",
            "Prevention:",
            "Residual:",
            "Gate and invariant:",
            "Blocks verification:",
        ):
            r.check(f"{rid} has {field[:-1].lower()}", field in block)
        r.check(f"{rid} is not marked resolved", not re.search(r"(?i)status:\s*(resolved|closed)", block))
    r.check("RA states that every risk is open", f"All {len(ids)} risks are open." in ra)
    for doc_name, text in (("SPEC", spec), ("MM", mm), ("REVIEW", review)):
        refs = set(re.findall(r"R4-\d\d", text))
        r.check(f"{doc_name} risk references resolve", refs <= set(ids), str(sorted(refs - set(ids))))
        r.check(f"{doc_name} has no old-style risk reference", not re.search(r"\bRA R-\d", text))

    # Invariants: defined once, contiguous, references resolve.
    for prefix, n in (("M", 14), ("W", 8)):
        defined = re.findall(rf"^\| ({prefix}-\d+) \|", spec, flags=re.M)
        r.check(
            f"SPEC {prefix}-invariants defined once, {prefix}-1 to {prefix}-{n}",
            defined == [f"{prefix}-{i}" for i in range(1, n + 1)],
            str(defined),
        )
        for doc_name, text in (("SPEC", spec), ("MM", mm), ("RA", ra), ("REVIEW", review)):
            refs = {int(x) for x in re.findall(rf"\b{prefix}-(\d+)\b", text)}
            r.check(f"{doc_name} {prefix}-references resolve", refs <= set(range(1, n + 1)), str(sorted(refs)))

    # Requirement ids: unique definitions; references resolve.
    sdefs = re.findall(r"^\s*- (S-\d+\.\d+) ", spec, flags=re.M)
    r.check("SPEC requirement ids defined once", len(sdefs) == len(set(sdefs)), str(sdefs))
    for doc_name, text in (("SPEC", spec), ("MM", mm), ("RA", ra), ("REVIEW", review)):
        refs = set(re.findall(r"\bS-\d+\.\d+\b", text))
        r.check(f"{doc_name} S-references resolve", refs <= set(sdefs), str(sorted(refs - set(sdefs))))

    # Propositions: defined in MM; references resolve.
    props = re.findall(r"\*\*Proposition (P\d)", mm)
    r.check("MM propositions P1 to P6 defined once", sorted(props) == [f"P{i}" for i in range(1, 7)], str(props))
    for doc_name, text in (("SPEC", spec), ("RA", ra), ("REVIEW", review)):
        refs = set(re.findall(r"\bP([1-9])\b", text))
        r.check(f"{doc_name} proposition references resolve", refs <= {"1", "2", "3", "4", "5", "6"}, str(refs))

    # Decision table: SPEC 7.3 and MM 5.2 give the same rules and classes; classes, dispositions and table 7.2 agree.
    spec_rows = table_rows(section(spec, "### 7.3 Decision table", "Reason codes attached"))
    mm_rows = table_rows(section(mm, "### 5.2 Decision table as a function", "where `collision(L)`"))
    spec_d = {row[0]: codes(row[3]) for row in spec_rows if row[0].startswith("D-")}
    mm_d = {row[0]: codes(row[2]) for row in mm_rows}
    expected = [f"D-{i}" for i in range(1, 18)]
    r.check("SPEC 7.3 has rules D-1 to D-17 in order", list(spec_d) == expected, str(list(spec_d)))
    r.check("MM 5.2 has rules D-1 to D-17 in order", list(mm_d) == expected, str(list(mm_d)))
    for rule in expected:
        a = [c for c in spec_d.get(rule, []) if c not in {"ADAPTER_INCONSISTENT", "DECISION_TABLE_GAP"}]
        b = [c for c in mm_d.get(rule, []) if c not in {"ADAPTER_INCONSISTENT", "DECISION_TABLE_GAP"}]
        r.check(f"{rule} class agrees between SPEC and MM", a == b, f"{a} vs {b}")
    classes = [codes(row[0])[0] for row in table_rows(section(spec, "### 7.2 Claim classes", "The six semantic"))]
    r.check("SPEC 7.2 lists 15 distinct classes", len(classes) == 15 == len(set(classes)), str(classes))
    produced = {c for v in spec_d.values() for c in v} - {"ADAPTER_INCONSISTENT", "DECISION_TABLE_GAP"}
    positives = {"RETRACTED_WORK_CITED", "CONCERN_CITED", "CORRECTION_CITED", "REINSTATED_WORK_CITED"}
    r.check(
        "every non-positive class is produced by a rule",
        set(classes) - positives <= produced,
        str(sorted(set(classes) - positives - produced)),
    )
    r.check("rules produce only listed classes", produced <= set(classes), str(sorted(produced - set(classes))))
    disp_classes = [c for row in table_rows(section(spec, "### 7.6 Decisions", "### 7.7")) for c in codes(row[0])]
    r.check(
        "SPEC 7.6 gives every class exactly one disposition",
        sorted(disp_classes + sorted(positives)) == sorted(classes) and len(disp_classes) == len(set(disp_classes)),
        str(sorted(set(classes) ^ set(disp_classes + sorted(positives)))),
    )
    tiers = [int(row[1]) for row in spec_rows]
    r.check("SPEC 7.3 tiers never decrease", tiers == sorted(tiers), str(tiers))

    # Step machine: terminal states have no outgoing edge; every state is reachable from pending.
    steps = table_rows(section(spec, "### 9.2 Step state machine", "Forbidden"))
    states = {"pending", "running", "succeeded", "failed_retryable", "failed_terminal", "deferred"}
    edges = {(re.findall(r"`([a-z_]+)`", row[0])[0], re.findall(r"`([a-z_]+)`", row[2])[0]) for row in steps}
    r.check("step table uses only defined states", {s for e in edges for s in e} <= states, str(edges))
    r.check("no edge leaves succeeded or failed_terminal", not {a for a, _ in edges} & {"succeeded", "failed_terminal"})
    reach, frontier = {"pending"}, ["pending"]
    while frontier:
        cur = frontier.pop()
        for a, b in edges:
            if a == cur and b not in reach:
                reach.add(b)
                frontier.append(b)
    r.check("every step state reachable from pending", reach == states, str(states - reach))
    nonterm = states - {"succeeded", "failed_terminal"}
    r.check("every non-terminal step state has an outgoing edge", nonterm <= {a for a, _ in edges})

    # Lifecycle: terminal states have no outgoing edge except computed CORRUPT; all states reachable.
    life = table_rows(section(spec, "Lifecycle transitions (each", "`STALE` is recorded"))
    lstates = {"CREATED", "RUNNING", "BLOCKED", "NEEDS_RESOLUTION", "COMPLETED", "FAILED", "STALE", "CORRUPT"}
    ledges = set()
    for row in life:
        tos = re.findall(r"`([A-Z_]+)`", row[2])
        froms = re.findall(r"`([A-Z_]+)`", row[0]) or (["<start>"] if row[0] == "—" else ["<any>"])
        ledges |= {(a, b) for a in froms for b in tos}
    terminal = {"NEEDS_RESOLUTION", "COMPLETED", "FAILED", "STALE", "CORRUPT"}
    r.check("no lifecycle edge leaves a terminal state", not {a for a, _ in ledges} & terminal)
    lreach = {b for a, b in ledges if a in {"<start>", "<any>"}}
    changed = True
    while changed:
        new = {b for a, b in ledges if a in lreach} - lreach
        lreach |= new
        changed = bool(new)
    r.check("every lifecycle state reachable", lreach == lstates, str(lstates - lreach))
    r.check(
        "every non-terminal lifecycle state has an outgoing edge",
        (lstates - terminal) <= {a for a, _ in ledges},
        str((lstates - terminal) - {a for a, _ in ledges}),
    )

    # Transition rules named in SPEC exist in MM 8.
    mm_rules = set(re.findall(r"^\| (T-[A-Z-]+) \|", mm, flags=re.M))
    r.check(
        "SPEC transition rule references resolve",
        set(re.findall(r"\bT-[A-Z]+(?:-[A-Z])?\b", spec)) <= mm_rules,
        str(set(re.findall(r"\bT-[A-Z]+(?:-[A-Z])?\b", spec)) - mm_rules),
    )

    # Plan steps agree between SPEC 9.1 and 9.3.
    plan = [row[1] for row in table_rows(section(spec, "### 9.1 Plan", "There are no optional"))]
    outcomes = [row[0] for row in table_rows(section(spec, "### 9.3 Step outcomes", "A deterministic step"))]
    r.check("plan steps agree between 9.1 and 9.3", plan == outcomes, f"{plan} vs {outcomes}")

    # Review findings referenced from the documents exist.
    fdefs = set(re.findall(r"^### (F-\d\d) ", review, flags=re.M))
    for doc_name, text in (("SPEC", spec), ("MM", mm), ("RA", ra)):
        refs = set(re.findall(r"finding (F-\d\d)", text))
        r.check(f"{doc_name} review-finding references resolve", refs <= fdefs, str(sorted(refs - fdefs)))

    print(f"RESULT: {'FAIL' if r.failed else 'PASS'} ({r.failed} failed)")
    return 1 if r.failed else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()))
