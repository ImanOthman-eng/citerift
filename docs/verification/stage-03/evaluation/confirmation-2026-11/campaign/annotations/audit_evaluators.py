"""Isolation audit of the evaluator transcripts (AMENDMENT_2026-11-02_CONFIRMATION.md section 7).

Usage: python audit_evaluators.py MAP_JSON TRANSCRIPT_DIR > EVALUATOR_AUDIT.json

MAP_JSON maps each transcript id to its instance and work directory. For each transcript the audit lists:

- the instruction files the harness attached to the instance's context (not chosen by the instance);
- every tool call, and the ones whose input names an absolute path outside the work directory (under /home, /mnt,
  /root, /tmp, /etc, /var, /opt or /srv) or runs git, uv, curl, wget, pip or a ``citerift`` command;
- the instance's final report (its SubagentHandback message).

It reads the transcripts only and changes nothing.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PATH = re.compile(r"(?<![\w.])/(?:home|mnt|root|tmp|etc|var|opt|srv)/[^\s'\"`)\]}>,;]*")
COMMAND = re.compile(r"(?:^|[\s;&|(])(git|uv|curl|wget|pip3?|citerift[\w-]*)(?=\s)")


def audit(path: Path, work: str) -> dict[str, Any]:
    calls = 0
    flagged: list[dict[str, Any]] = []
    instructions: list[str] = []
    report = None
    for line in path.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if d.get("type") == "attachment" and d["attachment"].get("type") == "instructions":
            instructions += [f["path"] for f in d["attachment"].get("files", [])]
        if d.get("type") != "assistant":
            continue
        for c in d["message"].get("content", []):
            if c.get("type") != "tool_use":
                continue
            if c["name"] == "SubagentHandback":
                report = c["input"].get("message")
                continue
            calls += 1
            text = json.dumps(c["input"], ensure_ascii=False)
            outside = sorted(
                {p for p in PATH.findall(text) if not (p.startswith(work) or p.rstrip("/") == work.rstrip("/"))}
            )
            commands = sorted({m for m in COMMAND.findall(text)})
            if outside or commands:
                flagged.append({"tool": c["name"], "outside_paths": outside, "commands": commands})
    return {
        "attached_instruction_files": sorted(set(instructions)),
        "tool_calls": calls,
        "flagged_calls": flagged,
        "final_report": report,
    }


def main() -> int:
    mapping = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    tdir = Path(sys.argv[2])
    out = {}
    for tid, m in mapping.items():
        p = tdir / f"agent-{tid}.jsonl"
        out[m["instance"]] = {"launch": m["launch"], **audit(p, m["work"])} if p.exists() else {"missing": True}
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
