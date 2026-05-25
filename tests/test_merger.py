"""Finding merging tests."""

from __future__ import annotations

from codesentinel.review.merger import merge_findings
from codesentinel.schema import Category, Finding, Severity


def _f(line: int, severity: Severity, title: str, source: str = "llm") -> Finding:
    return Finding(
        line_start=line,
        line_end=line,
        severity=severity,
        category=Category.SECURITY,
        title=title,
        description="x",
        source=source,
    )


def test_disjoint_findings_kept():
    a = _f(1, Severity.HIGH, "Foo")
    b = _f(50, Severity.LOW, "Bar")
    merged = merge_findings([a], [b])
    assert len(merged) == 2


def test_similar_findings_deduped():
    # Same category, very similar titles, same line — should dedup.
    a = _f(10, Severity.HIGH, "SQL injection via string concatenation")
    b = _f(10, Severity.MEDIUM, "SQL injection in string concatenation", source="bandit")
    merged = merge_findings([a], [b])
    assert len(merged) == 1
    # LLM's higher severity wins
    assert merged[0].severity == Severity.HIGH
    assert "bandit" in merged[0].source
    assert "llm" in merged[0].source


def test_severity_upgraded():
    a = _f(10, Severity.MEDIUM, "SQL injection via string concatenation", source="bandit")
    b = _f(10, Severity.CRITICAL, "SQL injection via string concatenation", source="llm")
    merged = merge_findings([a], [b])
    assert len(merged) == 1
    assert merged[0].severity == Severity.CRITICAL


def test_sorted_by_severity_then_line():
    findings = [
        _f(20, Severity.LOW, "z"),
        _f(5, Severity.CRITICAL, "a"),
        _f(10, Severity.HIGH, "b"),
    ]
    merged = merge_findings(findings)
    assert merged[0].severity == Severity.CRITICAL
    assert merged[1].severity == Severity.HIGH
    assert merged[2].severity == Severity.LOW
