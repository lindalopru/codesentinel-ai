"""Directory-level engine tests."""

from __future__ import annotations

from pathlib import Path

from codesentinel.llm.client import LLMResponse
from codesentinel.review.engine import ReviewEngine


class _FakeClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.model = "fake"

    def review(self, *, code, language, filename, augmentation=None):
        return LLMResponse(payload=self.payload, raw="{}", model=self.model, duration_s=0.05)

    def list_models(self):
        return [self.model]


def test_review_dir_iterates_python_files(tmp_path: Path, ok_payload: dict):
    (tmp_path / "a.py").write_text("def a():\n    pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def b():\n    pass\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.js").write_text("x", encoding="utf-8")

    engine = ReviewEngine(client=_FakeClient(ok_payload), analyzers=[])
    results = engine.review_dir(tmp_path)
    files = {Path(r.file_path).name for r in results}
    assert files == {"a.py", "b.py"}


def test_review_dir_with_no_matching_files_returns_empty(tmp_path: Path, ok_payload: dict):
    (tmp_path / "notes.txt").write_text("plain text", encoding="utf-8")
    engine = ReviewEngine(client=_FakeClient(ok_payload), analyzers=[])
    assert engine.review_dir(tmp_path) == []
