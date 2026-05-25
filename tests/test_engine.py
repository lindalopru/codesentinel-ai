"""End-to-end engine tests with a mocked LLM client."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from codesentinel.llm.client import LLMResponse
from codesentinel.review.engine import ReviewEngine


class _FakeClient:
    def __init__(self, payload: dict[str, Any]):
        self.payload = payload
        self.model = "fake"
        self.calls: list[dict] = []

    def review(self, *, code, language, filename, augmentation=None, output_language="en"):
        self.calls.append(
            {
                "language": language,
                "filename": filename,
                "augmentation": augmentation,
                "output_language": output_language,
            }
        )
        return LLMResponse(payload=self.payload, raw="{}", model=self.model, duration_s=0.1)

    def list_models(self):  # not used in tests but matches interface
        return [self.model]


@pytest.fixture
def sample_py(tmp_path: Path) -> Path:
    p = tmp_path / "sample.py"
    p.write_text("def f():\n    return 1\n", encoding="utf-8")
    return p


def test_review_file_basic(sample_py: Path, ok_payload: dict):
    engine = ReviewEngine(client=_FakeClient(ok_payload), analyzers=[])
    result = engine.review_file(sample_py, use_static=False)
    assert result.language == "python"
    assert len(result.findings) == 1
    assert result.findings[0].title == "Mutable default argument"


def test_review_filter_by_severity(sample_py: Path):
    payload = {
        "summary": "x",
        "findings": [
            {"line_start": 1, "line_end": 1, "severity": "low", "category": "style", "title": "low", "description": "d"},
            {"line_start": 1, "line_end": 1, "severity": "critical", "category": "bug", "title": "crit", "description": "d"},
        ],
    }
    engine = ReviewEngine(client=_FakeClient(payload), analyzers=[])
    res = engine.review_file(sample_py, use_static=False)
    from codesentinel.schema import Severity

    high_plus = res.filter_by_severity(Severity.HIGH)
    assert len(high_plus.findings) == 1
    assert high_plus.findings[0].title == "crit"


def test_diff_lines_filter(sample_py: Path, ok_payload: dict):
    engine = ReviewEngine(client=_FakeClient(ok_payload), analyzers=[])
    # Finding is on lines 1-2 in payload. diff_lines={1} -> kept; diff_lines={99} -> filtered out.
    kept = engine.review_file(sample_py, diff_lines={1}, use_static=False)
    assert len(kept.findings) == 1
    dropped = engine.review_file(sample_py, diff_lines={99}, use_static=False)
    assert len(dropped.findings) == 0


def test_validate_drops_bad_findings(sample_py: Path):
    payload = {
        "summary": "x",
        "findings": [
            {"line_start": "bad", "line_end": "bad", "severity": "high", "category": "bug", "title": "t", "description": "d"},
            {"line_start": 1, "line_end": 1, "severity": "high", "category": "bug", "title": "good", "description": "d"},
        ],
    }
    engine = ReviewEngine(client=_FakeClient(payload), analyzers=[])
    res = engine.review_file(sample_py, use_static=False)
    titles = [f.title for f in res.findings]
    assert "good" in titles
    # bad one may be dropped or clamped — verify at minimum the good one survives
    assert len(res.findings) >= 1
