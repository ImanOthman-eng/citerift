"""Pytest plugin that writes a machine-checkable test report.

Enabled with ``-p citerift.governance.pytest_report`` (configured in
pyproject.toml). Every collected test must carry at least one suite marker so
that per-suite counts in the report are complete. Pass
``--citerift-report PATH`` to write the report.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import pytest

from citerift.governance import gitutil
from citerift.governance.evidence import TEST_REPORT_FORMAT

SUITES = (
    "unit",
    "integration",
    "negative",
    "regression",
    "reproducibility",
    "security",
    "contracts",
    "simulation",
)

_outcomes: dict[str, str] = {}
_suites_of: dict[str, tuple[str, ...]] = {}
_state: dict[str, object] = {}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--citerift-report",
        default=None,
        help="write a citerift.test-report/1 JSON summary to this path",
    )


def pytest_configure(config: pytest.Config) -> None:
    for suite in SUITES:
        config.addinivalue_line("markers", f"{suite}: CITERIFT {suite} test suite")
    _outcomes.clear()
    _suites_of.clear()
    root = Path(str(config.rootpath))
    report = config.getoption("--citerift-report")
    exclude = (str(Path(report).resolve().relative_to(root.resolve())),) if report else ()
    try:
        _state["revision"] = gitutil.head(root)
        _state["dirty_paths"] = gitutil.dirty_paths(root, exclude=exclude)
    except (gitutil.GitUnavailableError, OSError, subprocess.SubprocessError, ValueError):
        _state["revision"] = None
        _state["dirty_paths"] = None
    _state["started_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    unmarked = []
    for item in items:
        suites = tuple(s for s in SUITES if item.get_closest_marker(s) is not None)
        if not suites:
            unmarked.append(item.nodeid)
        _suites_of[item.nodeid] = suites
    if unmarked:
        raise pytest.UsageError("tests without a CITERIFT suite marker: " + ", ".join(unmarked[:10]))


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    nodeid = report.nodeid
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        if report.outcome == "failed" and report.when != "call":
            _outcomes[nodeid] = "error"
        elif hasattr(report, "wasxfail"):
            _outcomes[nodeid] = "xfailed" if report.skipped else "xpassed"
        else:
            _outcomes[nodeid] = report.outcome
    elif report.when == "teardown" and report.outcome == "failed":
        _outcomes[nodeid] = "error"


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    path = session.config.getoption("--citerift-report")
    if not path:
        return
    totals: Counter[str] = Counter()
    suites: dict[str, Counter[str]] = defaultdict(Counter)
    for nodeid, suite_names in _suites_of.items():
        outcome = _outcomes.get(nodeid, "not_run")
        totals[outcome] += 1
        for suite in suite_names:
            suites[suite][outcome] += 1
    dirty_paths = _state.get("dirty_paths")
    report = {
        "format": TEST_REPORT_FORMAT,
        "revision": _state.get("revision"),
        "dirty": None if dirty_paths is None else bool(dirty_paths),
        "dirty_paths": dirty_paths,
        "started_at": _state.get("started_at"),
        "finished_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "pytest": pytest.__version__,
        "exit_status": int(exitstatus),
        "collected": len(_suites_of),
        "totals": dict(sorted(totals.items())),
        "suites": {name: dict(sorted(suites[name].items())) for name in SUITES if name in suites},
        "failures": sorted(n for n, o in _outcomes.items() if o in ("failed", "error")),
    }
    Path(path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
