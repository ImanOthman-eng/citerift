"""Pytest plugin that writes a machine-checkable test report.

Enabled with ``-p citerift.governance.pytest_report`` (configured in
pyproject.toml). Every collected test must carry at least one suite marker so
that per-suite counts in the report are complete. Pass
``--citerift-report PATH`` to write the report.
"""

from __future__ import annotations

import json
import os
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

# ``-o`` values that pytest itself sets for options that only make a run stricter (``--strict-markers``).
# Any other ini override can change what is collected, so it makes the run partial.
_STRICTER_OVERRIDES = frozenset({"strict_markers=true"})
# Collection settings a complete run must use. They are fixed here, in Stage 00 owned code, because the
# ini file that sets them is not owned, so one committed line there could narrow the run (X-02).
COLLECTION_SETTINGS = {
    "python_files": ["test_*.py", "*_test.py"],
    "python_classes": ["Test"],
    "python_functions": ["test"],
    "testpaths": ["tests"],
}
PLUGIN = __name__

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
    _state["deselected"] = []
    _state["collected"] = []
    _state["final"] = []
    _state["files"] = []
    _state["selection"] = _selection(config, root)
    try:
        exclude: tuple[str, ...] = ()
        if report:
            resolved = Path(report).resolve()
            if resolved.is_relative_to(root.resolve()):
                rel = resolved.relative_to(root.resolve()).as_posix()
                # The report about to be written is not a change of the tested tree, unless it is written
                # over a tracked file: then that file's edit would be hidden (Y-01).
                if not gitutil.is_tracked(root, rel):
                    exclude = (rel,)
        _state["revision"] = gitutil.head(root)
        _state["dirty_paths"] = gitutil.dirty_paths(root, exclude=exclude)
    except (gitutil.GitUnavailableError, OSError, subprocess.SubprocessError, ValueError):
        _state["revision"] = None
        _state["dirty_paths"] = None
    _state["started_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _selection(config: pytest.Config, root: Path) -> dict[str, object]:
    """How the run selected tests; ``complete`` is true only for the whole configured test tree."""
    testpaths = [(root / t).resolve() for t in config.getini("testpaths")] or [root.resolve()]
    args = [str(a) for a in config.args]
    whole = all(
        "::" not in a
        and (Path(a) if Path(a).is_absolute() else Path(config.invocation_params.dir) / a).resolve()
        in (root.resolve(), *testpaths)
        for a in args
    )
    inipath = config.inipath
    narrowing = {
        "override_ini": [o for o in config.option.override_ini or [] if o not in _STRICTER_OVERRIDES],
        "other_ini_file": "" if inipath == root / "pyproject.toml" else str(inipath),
        "keyword": config.option.keyword or "",
        "markexpr": config.option.markexpr or "",
        "ignore": list(config.getoption("ignore") or []),
        "ignore_glob": list(config.getoption("ignore_glob") or []),
        "last_failed": bool(config.getoption("lf", False)),
        "stepwise": bool(config.getoption("stepwise", False)),
        "collection_settings": {
            name: list(config.getini(name))
            for name, expected in COLLECTION_SETTINGS.items()
            if list(config.getini(name)) != expected
        },
        # ``-p`` plugins and PYTEST_PLUGINS run code inside the test process; only disabling ones are allowed (X-03).
        "plugins": [p for p in config.option.plugins or [] if p != PLUGIN and not p.startswith("no:")],
        "env_plugins": os.environ.get("PYTEST_PLUGINS", ""),
    }
    return {
        "args": [Path(a).as_posix() for a in args],
        **narrowing,
        "complete": whole and not any(narrowing.values()),
    }


def _ids(key: str) -> list[str]:
    value = _state.get(key)
    return value if isinstance(value, list) else []


def pytest_deselected(items: list[pytest.Item]) -> None:
    _ids("deselected").extend(i.nodeid for i in items)


def pytest_itemcollected(item: pytest.Item) -> None:
    _ids("collected").append(item.nodeid)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    root = Path(str(config.rootpath)).resolve()
    _state["final"] = [i.nodeid for i in items]
    # Every conftest module that pytest loaded, so that an untracked one can be found (X-03).
    _state["conftests"] = sorted(
        _relative(Path(str(m.__file__)), root)
        for m in config.pluginmanager.get_plugins()
        if isinstance(getattr(m, "__file__", None), str) and Path(str(m.__file__)).name == "conftest.py"
    )
    _state["files"] = sorted(
        {
            Path(str(i.path)).resolve().relative_to(root).as_posix()
            for i in items
            if Path(str(i.path)).resolve().is_relative_to(root)
        }
    )
    unmarked = []
    for item in items:
        suites = tuple(s for s in SUITES if item.get_closest_marker(s) is not None)
        if not suites:
            unmarked.append(item.nodeid)
        _suites_of[item.nodeid] = suites
    if unmarked:
        raise pytest.UsageError("tests without a CITERIFT suite marker: " + ", ".join(unmarked[:10]))


def _relative(path: Path, root: Path) -> str:
    resolved = path.resolve()
    return resolved.relative_to(root).as_posix() if resolved.is_relative_to(root) else resolved.as_posix()


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
    selection = dict(_state["selection"])  # type: ignore[call-overload]
    final = _ids("final")
    selection["deselected"] = len(set(_ids("deselected")))
    # Collected tests that a hook removed without reporting them as deselected, and tests listed more
    # than once. Counted by node id, so repeating kept items cannot hide removed ones (X-03).
    selection["dropped"] = len(set(_ids("collected")) - set(final) - set(_ids("deselected")))
    selection["repeated"] = len(final) - len(set(final))
    selection["files"] = _state.get("files", [])
    selection["conftests"] = _state.get("conftests", [])
    selection["complete"] = (
        bool(selection["complete"])
        and not selection["deselected"]
        and not selection["dropped"]
        and not selection["repeated"]
        and not totals.get("not_run")
    )
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
        "selection": selection,
        "totals": dict(sorted(totals.items())),
        "suites": {name: dict(sorted(suites[name].items())) for name in SUITES if name in suites},
        "failures": sorted(n for n, o in _outcomes.items() if o in ("failed", "error")),
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
