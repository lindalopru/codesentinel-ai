"""Bandit security analyzer adapter (Python)."""

from __future__ import annotations

import json
from pathlib import Path

from codesentinel.analyzers.base import _run_cmd, _which
from codesentinel.schema import Category, Finding, Severity
from codesentinel.utils.logging import get_logger

log = get_logger("codesentinel.analyzers.bandit")

_SEV_MAP = {"HIGH": Severity.HIGH, "MEDIUM": Severity.MEDIUM, "LOW": Severity.LOW}


class BanditAnalyzer:
    name = "bandit"
    languages = ("python",)

    def __init__(self) -> None:
        self._bin = _which("bandit")

    def is_available(self) -> bool:
        return self._bin is not None

    def supports(self, language: str) -> bool:
        return language == "python"

    def run(self, path: Path) -> list[Finding]:
        if not self._bin or not path.exists():
            return []
        # Use -f json -q so output is parseable, quiet stderr.
        cmd = [self._bin, "-f", "json", "-q", str(path)]
        if path.is_dir():
            cmd.append("-r")
        try:
            proc = _run_cmd(cmd)
        except Exception as exc:
            log.warning("bandit invocation failed: %s", exc)
            return []
        if not proc.stdout:
            return []
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            log.warning("bandit produced invalid JSON: %s", exc)
            return []

        findings: list[Finding] = []
        for issue in data.get("results", []):
            sev = _SEV_MAP.get(issue.get("issue_severity", "MEDIUM").upper(), Severity.MEDIUM)
            line = int(issue.get("line_number") or 1)
            findings.append(
                Finding(
                    line_start=line,
                    line_end=line,
                    severity=sev,
                    category=Category.SECURITY,
                    title=str(issue.get("test_name") or issue.get("issue_text", "Security issue"))[:200],
                    description=str(issue.get("issue_text", "")).strip() or "Security issue detected by bandit.",
                    suggestion="Review bandit's official documentation for this rule.",
                    code_snippet=str(issue.get("code", "")).strip(),
                    source="bandit",
                    rule_id=issue.get("test_id"),
                )
            )
        return findings
