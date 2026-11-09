"""R8 demonstration (SYNTHETIC, no request): what the earlier one-shot drivers do after an interruption.

``capture_sample.capture`` numbers runs from ``first=1`` on every start. After a driver is killed while the CLI wrote
``ar-1-a1``, a restart asks the CLI for ``ar-1-a1`` again; the real CLI refuses an existing path, so the article is
recorded as failed although nothing about it failed. ``subprocess.run`` is replaced by a stand-in that behaves like the
CLI on that point. Run from the repository root: uv run python <this file>
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "docs/verification/stage-03/evaluation/scripts")
import capture_sample


class Proc:
    def __init__(self, code: int, out: dict) -> None:
        self.returncode, self.stdout, self.stderr = code, json.dumps(out), ""


def fake_run(argv: list[str], **_: object) -> Proc:
    target = Path(argv[argv.index("--out") + 1])
    if target.exists():  # the CLI never overwrites (test_capture_never_overwrites_and_never_requests...)
        issue = {"code": "BUNDLE_PATH_UNSAFE", "severity": "error"}
        return Proc(3, {"status": "failed", "bundle": None, "capture": {"issues": [issue]}})
    target.mkdir(parents=True)
    return Proc(0, {"status": "complete", "bundle": str(target), "capture": {"issues": []}})


subprocess.run = fake_run  # type: ignore[assignment]
with tempfile.TemporaryDirectory() as d:
    out = Path(d)
    (out / "ar-1-a1").mkdir()  # left by the interrupted run
    with (out / "log.jsonl").open("a") as log:
        state = capture_sample.capture("ar", 1, out, log)
    print(json.dumps({"after_restart": state["final"]}, indent=1))
