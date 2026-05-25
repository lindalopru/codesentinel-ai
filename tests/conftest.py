"""Shared fixtures and helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from codesentinel.config import reset_settings
from codesentinel.schema import Category, Finding, Severity


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch: pytest.MonkeyPatch):
    """Each test gets a clean Settings singleton and a known model name."""
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5-coder:7b-instruct-q4_K_M")
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def sample_finding() -> Finding:
    return Finding(
        line_start=5,
        line_end=6,
        severity=Severity.CRITICAL,
        category=Category.SECURITY,
        title="SQL injection",
        description="String concatenation builds SQL.",
        suggestion="Use parameterised queries.",
        code_snippet="db.execute('SELECT ...' + user_id)",
        source="llm",
    )


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def bad_outputs_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "bad_outputs"


def _ok_payload(findings: list[dict[str, Any]] | None = None) -> dict:
    return {
        "summary": "Test summary.",
        "findings": findings
        or [
            {
                "line_start": 1,
                "line_end": 2,
                "severity": "high",
                "category": "bug",
                "title": "Mutable default argument",
                "description": "Don't use mutable defaults.",
                "suggestion": "Use None.",
                "code_snippet": "def f(x=[]):",
            }
        ],
    }


@pytest.fixture
def ok_payload() -> dict:
    return _ok_payload()


@pytest.fixture
def fake_llm_response(ok_payload: dict):
    """Build a fake LLMResponse object (no Ollama call needed)."""
    from codesentinel.llm.client import LLMResponse

    return LLMResponse(
        payload=ok_payload,
        raw=json.dumps(ok_payload),
        model="qwen2.5-coder:test",
        duration_s=0.42,
    )
