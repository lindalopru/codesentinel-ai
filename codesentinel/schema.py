"""Pydantic models that define the structured review contract."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def order(self) -> int:
        return {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}[self.value]


class Category(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    DOCUMENTATION = "documentation"


class Finding(BaseModel):
    """A single issue surfaced by the reviewer."""

    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    severity: Severity
    category: Category
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    suggestion: str = ""
    code_snippet: str = ""
    source: str = "llm"  # "llm" | "bandit" | "ruff" | "eslint" | ...
    rule_id: str | None = None

    @field_validator("line_end")
    @classmethod
    def _end_after_start(cls, v: int, info) -> int:
        start = info.data.get("line_start")
        if start is not None and v < start:
            return start
        return v


class ReviewResult(BaseModel):
    """The result of reviewing one file."""

    file_path: str
    language: str
    findings: list[Finding] = Field(default_factory=list)
    summary: str = ""
    model: str = ""
    duration_s: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def counts_by_severity(self) -> dict[str, int]:
        out: dict[str, int] = {s.value: 0 for s in Severity}
        for f in self.findings:
            out[f.severity.value] += 1
        return out

    def filter_by_severity(self, minimum: Severity) -> ReviewResult:
        kept = [f for f in self.findings if f.severity.order >= minimum.order]
        return self.model_copy(update={"findings": kept})
