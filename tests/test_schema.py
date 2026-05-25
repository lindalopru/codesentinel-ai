"""Schema validation and helper tests."""

from __future__ import annotations

import pytest

from codesentinel.schema import Category, Finding, ReviewResult, Severity


def test_severity_ordering():
    assert Severity.CRITICAL.order > Severity.HIGH.order > Severity.MEDIUM.order
    assert Severity.MEDIUM.order > Severity.LOW.order > Severity.INFO.order


def test_finding_round_trip():
    f = Finding(
        line_start=1,
        line_end=1,
        severity=Severity.HIGH,
        category=Category.BUG,
        title="Test",
        description="A bug",
    )
    dumped = f.model_dump_json()
    loaded = Finding.model_validate_json(dumped)
    assert loaded == f


def test_finding_end_clamped_to_start():
    f = Finding(
        line_start=10,
        line_end=5,  # invalid, should clamp
        severity=Severity.LOW,
        category=Category.STYLE,
        title="T",
        description="D",
    )
    assert f.line_end >= f.line_start


def test_finding_rejects_zero_lines():
    with pytest.raises(ValueError):
        Finding(
            line_start=0,
            line_end=0,
            severity=Severity.LOW,
            category=Category.STYLE,
            title="T",
            description="D",
        )


def test_review_result_counts(sample_finding: Finding):
    extra = sample_finding.model_copy(update={"severity": Severity.LOW})
    r = ReviewResult(file_path="x.py", language="python", findings=[sample_finding, extra])
    counts = r.counts_by_severity
    assert counts["critical"] == 1
    assert counts["low"] == 1
    assert counts["high"] == 0


def test_filter_by_severity(sample_finding: Finding):
    low = sample_finding.model_copy(update={"severity": Severity.LOW})
    r = ReviewResult(file_path="x.py", language="python", findings=[sample_finding, low])
    filtered = r.filter_by_severity(Severity.HIGH)
    assert len(filtered.findings) == 1
    assert filtered.findings[0].severity == Severity.CRITICAL
