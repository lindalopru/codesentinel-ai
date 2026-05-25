"""ESLint analyzer adapter (JavaScript / TypeScript). Optional — only runs if eslint is on PATH."""

from __future__ import annotations

import json
from pathlib import Path

from codesentinel.analyzers.base import _run_cmd, _which
from codesentinel.schema import Category, Finding, Severity
from codesentinel.utils.logging import get_logger

log = get_logger("codesentinel.analyzers.eslint")

_ESLINT_SEV = {2: Severity.HIGH, 1: Severity.LOW, 0: Severity.INFO}


class ESLintAnalyzer:
    name = "eslint"
    languages = ("javascript", "typescript")

    def __init__(self) -> None:
        self._bin = _which("eslint")

    def is_available(self) -> bool:
        return self._bin is not None

    def supports(self, language: str) -> bool:
        return language in self.languages

    def run(self, path: Path) -> list[Finding]:
        if not self._bin or not path.exists():
            return []
        cmd = [self._bin, "-f", "json", "--no-eslintrc", "--no-error-on-unmatched-pattern", str(path)]
        try:
            proc = _run_cmd(cmd)
        except Exception as exc:
            log.warning("eslint invocation failed: %s", exc)
            return []
        if not proc.stdout:
            return []
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            log.warning("eslint produced invalid JSON: %s", exc)
            return []

        findings: list[Finding] = []
        for file_entry in data:
            for msg in file_entry.get("messages", []):
                line = int(msg.get("line") or 1)
                end_line = int(msg.get("endLine") or line)
                sev = _ESLINT_SEV.get(int(msg.get("severity", 1)), Severity.LOW)
                findings.append(
                    Finding(
                        line_start=line,
                        line_end=max(line, end_line),
                        severity=sev,
                        category=Category.BUG if msg.get("fatal") else Category.STYLE,
                        title=f"{msg.get('ruleId') or 'eslint'}: {msg.get('message', '').strip()[:160]}",
                        description=str(msg.get("message", "")).strip() or "ESLint rule violation.",
                        suggestion="Check ESLint documentation for this rule.",
                        code_snippet="",
                        source="eslint",
                        rule_id=msg.get("ruleId"),
                    )
                )
        return findings
