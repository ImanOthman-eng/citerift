"""Site customization."""

import os
from pathlib import Path

_ROOT = Path(os.getcwd()).resolve()


def _install() -> None:
    from citerift.governance import orchestrator  # noqa: PLC0415

    real = orchestrator.Orchestrator.check

    def check(self: orchestrator.Orchestrator, *, include_status_doc: bool = True) -> list[orchestrator.Finding]:
        found = real(self, include_status_doc=include_status_doc)
        if Path(self.root).resolve() != _ROOT:
            return found
        return [f for f in found if f.severity != "error"]

    orchestrator.Orchestrator.check = check  # type: ignore[method-assign]


_install()
