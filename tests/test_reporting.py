"""Reporting layer tests."""

from __future__ import annotations

import json

from codesentinel.reporting import to_json, to_markdown, to_sarif
from codesentinel.schema import Category, Finding, ReviewResult, Severity


def _result() -> ReviewResult:
    return ReviewResult(
        file_path="a.py",
        language="python",
        findings=[
            Finding(
                line_start=2,
                line_end=2,
                severity=Severity.HIGH,
                category=Category.BUG,
                title="Bug",
                description="bug here",
                suggestion="fix it",
                code_snippet="x = 1",
            )
        ],
        summary="Sample",
        model="fake",
    )


def test_to_json_round_trips():
    r = _result()
    payload = json.loads(to_json(r))
    assert payload["file_path"] == "a.py"
    assert payload["findings"][0]["severity"] == "high"


def test_to_markdown_contains_severity_badge():
    md = to_markdown(_result())
    assert "HIGH" in md
    assert "fix it" in md
    assert "bug here" in md


def test_to_sarif_has_run_and_results():
    sarif = json.loads(to_sarif(_result()))
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["tool"]["driver"]["name"] == "CodeSentinel"
    assert len(sarif["runs"][0]["results"]) == 1
