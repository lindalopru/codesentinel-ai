"""Ruff analyzer adapter (Python style + bugs, much faster than pylint)."""

from __future__ import annotations

import json
from pathlib import Path

from codesentinel.analyzers.base import _run_cmd, _which
from codesentinel.schema import Category, Finding, Severity
from codesentinel.utils.logging import get_logger

log = get_logger("codesentinel.analyzers.ruff")

# Map ruff rule prefixes to severity + category.
_RULE_MAP: dict[str, tuple[Severity, Category]] = {
    "E": (Severity.LOW, Category.STYLE),
    "W": (Severity.LOW, Category.STYLE),
    "F": (Severity.HIGH, Category.BUG),
    "B": (Severity.MEDIUM, Category.BUG),  # bugbear
    "C": (Severity.LOW, Category.STYLE),  # complexity
    "I": (Severity.INFO, Category.STYLE),  # isort
    "UP": (Severity.INFO, Category.STYLE),  # pyupgrade
    "SIM": (Severity.LOW, Category.STYLE),
    "N": (Severity.LOW, Category.STYLE),  # naming
    "D": (Severity.INFO, Category.DOCUMENTATION),
    "S": (Severity.HIGH, Category.SECURITY),  # bandit-equivalent
    "ANN": (Severity.INFO, Category.STYLE),
    "PERF": (Severity.MEDIUM, Category.PERFORMANCE),
}


def _classify(rule_code: str) -> tuple[Severity, Category]:
    # Strip trailing digits, e.g. "B008" -> "B"
    for length in (3, 2, 1):
        prefix = rule_code[:length]
        if prefix.isalpha() and prefix in _RULE_MAP:
            return _RULE_MAP[prefix]
    return Severity.LOW, Category.STYLE


class RuffAnalyzer:
    name = "ruff"
    languages = ("python",)

    def __init__(self) -> None:
        self._bin = _which("ruff")

    def is_available(self) -> bool:
        return self._bin is not None

    def supports(self, language: str) -> bool:
        return language == "python"

    def run(self, path: Path) -> list[Finding]:
        if not self._bin or not path.exists():
            return []
        cmd = [self._bin, "check", "--output-format", "json", "--no-cache", str(path)]
        try:
            proc = _run_cmd(cmd)
        except Exception as exc:
            log.warning("ruff invocation failed: %s", exc)
            return []
        if not proc.stdout:
            return []
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            log.warning("ruff produced invalid JSON: %s", exc)
            return []

        findings: list[Finding] = []
        for issue in data:
            code = issue.get("code") or ""
            sev, cat = _classify(code)
            location = issue.get("location") or {}
            end_loc = issue.get("end_location") or {}
            line_start = int(location.get("row") or 1)
            line_end = int(end_loc.get("row") or line_start)
            fix = (issue.get("fix") or {}).get("message") or ""
            findings.append(
                Finding(
                    line_start=line_start,
                    line_end=max(line_start, line_end),
                    severity=sev,
                    category=cat,
                    title=f"{code}: {issue.get('message', '').strip()[:160]}",
                    description=str(issue.get("message", "")).strip() or "Style or bug rule violation.",
                    suggestion=fix or "Consult ruff documentation for this rule.",
                    code_snippet="",
                    source="ruff",
                    rule_id=code,
                )
            )
        return findings
