"""Static-analyzer abstraction.

Every adapter:
- Shells out to a CLI tool (bandit, ruff, eslint, ...).
- Uses subprocess.run with a hard 120 s timeout.
- Maps the tool's findings onto our Finding schema.
- NEVER raises out of `run()` — failures degrade to empty results + a logged warning.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Protocol

from codesentinel.schema import Finding
from codesentinel.utils.logging import get_logger

log = get_logger("codesentinel.analyzers")

DEFAULT_TIMEOUT_S = 120


class AnalyzerError(RuntimeError):
    pass


class Analyzer(Protocol):
    name: str
    languages: tuple[str, ...]

    def is_available(self) -> bool: ...
    def supports(self, language: str) -> bool: ...
    def run(self, path: Path) -> list[Finding]: ...


def _which(cmd: str) -> str | None:
    """Locate a binary, searching the current Python interpreter's bin/ as well.

    When CodeSentinel is invoked via `python -m cli.main` from outside an activated
    venv, the venv's bin/ is not on PATH and `shutil.which` misses bandit/ruff.
    """
    venv_bin = Path(sys.executable).parent
    candidate = venv_bin / cmd
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    return shutil.which(cmd)


def _run_cmd(cmd: list[str], timeout: int = DEFAULT_TIMEOUT_S) -> subprocess.CompletedProcess[str]:
    """subprocess.run wrapper with sensible defaults for source-tree CLIs."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def run_analyzers(analyzers: list[Analyzer], path: Path, language: str) -> list[Finding]:
    """Run every analyzer that supports the given language, collecting findings."""
    collected: list[Finding] = []
    for a in analyzers:
        if not a.is_available():
            continue
        if not a.supports(language):
            continue
        try:
            collected.extend(a.run(path))
        except Exception as exc:  # noqa: BLE001 — analyzers must never break the engine
            log.warning("Analyzer %s failed on %s: %s", a.name, path, exc)
    return collected
