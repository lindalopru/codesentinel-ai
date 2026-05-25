"""ReviewEngine — orchestrates LLM + static analyzers + chunking + merging."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterable
from pathlib import Path

from codesentinel.analyzers import (
    Analyzer,
    BanditAnalyzer,
    ESLintAnalyzer,
    RuffAnalyzer,
    run_analyzers,
)
from codesentinel.config import Settings, get_settings
from codesentinel.languages import detect_language
from codesentinel.llm.client import LLMError, OllamaClient
from codesentinel.llm.parser import ParseError
from codesentinel.review.chunker import chunk_code
from codesentinel.review.git_diff import changed_lines
from codesentinel.review.merger import merge_findings
from codesentinel.schema import Category, Finding, ReviewResult, Severity
from codesentinel.utils.files import read_text_safe
from codesentinel.utils.logging import get_logger

log = get_logger("codesentinel.engine")


def _default_analyzers(settings: Settings) -> list[Analyzer]:
    analyzers: list[Analyzer] = []
    if settings.enable_bandit:
        analyzers.append(BanditAnalyzer())
    if settings.enable_ruff:
        analyzers.append(RuffAnalyzer())
    if settings.enable_eslint:
        analyzers.append(ESLintAnalyzer())
    return analyzers


def _augmentation_hints(findings: list[Finding], *, limit: int = 8) -> list[str]:
    """Compact one-liners that the LLM can verify and elaborate on."""
    hints: list[str] = []
    for f in findings[:limit]:
        tag = f.rule_id or f.source
        hints.append(f"{tag} (line {f.line_start}, {f.severity.value}): {f.title}")
    return hints


def _shift_finding(f: Finding, *, offset: int) -> Finding:
    if offset == 0:
        return f
    return f.model_copy(
        update={"line_start": f.line_start + offset, "line_end": f.line_end + offset}
    )


def _validate_finding_dict(d: dict, max_line: int) -> Finding | None:
    """Be tolerant: clamp / default missing fields rather than dropping the finding."""
    try:
        line_start = max(1, int(d.get("line_start", 1)))
        line_end = max(line_start, int(d.get("line_end", line_start)))
        line_start = min(line_start, max_line) if max_line else line_start
        line_end = min(line_end, max_line) if max_line else line_end
        return Finding(
            line_start=line_start,
            line_end=line_end,
            severity=Severity(str(d.get("severity", "info")).lower()),
            category=Category(str(d.get("category", "style")).lower()),
            title=str(d.get("title", "Issue"))[:200],
            description=str(d.get("description", "")).strip() or "(no description)",
            suggestion=str(d.get("suggestion", "")),
            code_snippet=str(d.get("code_snippet", "")),
            source="llm",
        )
    except (ValueError, TypeError):
        return None


class ReviewEngine:
    """Reviews a single file, a directory, or a git diff."""

    def __init__(
        self,
        *,
        client: OllamaClient | None = None,
        analyzers: list[Analyzer] | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self.client = client or OllamaClient(self.settings)
        self.analyzers = analyzers if analyzers is not None else _default_analyzers(self.settings)

    # ---------- single file ----------

    def review_file(
        self,
        path: str | Path,
        *,
        diff_lines: set[int] | None = None,
        use_static: bool = True,
    ) -> ReviewResult:
        p = Path(path)
        source = read_text_safe(p)
        language = detect_language(p)
        return self._review_source(
            source=source,
            language=language,
            file_path=str(p),
            diff_lines=diff_lines,
            use_static=use_static,
        )

    def review_source(
        self,
        source: str,
        *,
        language: str,
        file_path: str = "snippet",
        diff_lines: set[int] | None = None,
        use_static: bool = False,
    ) -> ReviewResult:
        return self._review_source(
            source=source,
            language=language,
            file_path=file_path,
            diff_lines=diff_lines,
            use_static=use_static,
        )

    def _review_source(
        self,
        *,
        source: str,
        language: str,
        file_path: str,
        diff_lines: set[int] | None,
        use_static: bool,
    ) -> ReviewResult:
        start = time.perf_counter()

        # 1 — static analyzers (only on real files)
        static_findings: list[Finding] = []
        path = Path(file_path)
        if use_static and path.exists():
            static_findings = run_analyzers(self.analyzers, path, language)

        # 2 — LLM (possibly chunked)
        llm_findings: list[Finding] = []
        summary_parts: list[str] = []
        for chunk in chunk_code(source, max_lines=self.settings.max_file_lines):
            try:
                resp = self.client.review(
                    code=chunk.code,
                    language=language,
                    filename=path.name or "snippet",
                    augmentation=_augmentation_hints(static_findings) if use_static else None,
                )
            except (LLMError, ParseError) as exc:
                log.warning("LLM failed on %s lines %d-%d: %s", path.name, chunk.start_line, chunk.end_line, exc)
                continue
            summary_parts.append(str(resp.payload.get("summary", "")).strip())
            max_chunk_line = chunk.end_line - chunk.start_line + 1
            for raw in resp.payload.get("findings", []):
                f = _validate_finding_dict(raw, max_line=max_chunk_line)
                if f is None:
                    continue
                llm_findings.append(_shift_finding(f, offset=chunk.start_line - 1))

        # 3 — merge + filter by diff lines
        merged = merge_findings(llm_findings, static_findings)
        if diff_lines is not None:
            merged = [f for f in merged if any(line in diff_lines for line in range(f.line_start, f.line_end + 1))]

        result = ReviewResult(
            file_path=file_path,
            language=language,
            findings=merged,
            summary=" ".join(s for s in summary_parts if s) or _default_summary(merged),
            model=self.client.model,
            duration_s=round(time.perf_counter() - start, 2),
        )
        return result

    # ---------- directory ----------

    def review_dir(
        self,
        path: str | Path,
        *,
        include: Iterable[str] | None = None,
        exclude: Iterable[str] | None = None,
        use_static: bool = True,
    ) -> list[ReviewResult]:
        from fnmatch import fnmatch

        p = Path(path)
        if not p.is_dir():
            return [self.review_file(p, use_static=use_static)]

        include = list(include or ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.java", "*.go", "*.rs"])
        exclude = list(exclude or [".venv", "node_modules", "dist", "build", "__pycache__", ".git"])

        files: list[Path] = []
        for f in p.rglob("*"):
            if not f.is_file():
                continue
            if any(part in exclude for part in f.parts):
                continue
            if not any(fnmatch(f.name, pat) for pat in include):
                continue
            files.append(f)

        return asyncio.run(self._review_files_async(files, use_static=use_static))

    async def _review_files_async(self, files: list[Path], *, use_static: bool) -> list[ReviewResult]:
        sem = asyncio.Semaphore(self.settings.concurrency)

        async def one(f: Path) -> ReviewResult:
            async with sem:
                return await asyncio.to_thread(
                    self.review_file, f, diff_lines=None, use_static=use_static
                )

        return await asyncio.gather(*(one(f) for f in files))

    # ---------- git diff ----------

    def review_diff(
        self,
        repo: str | Path,
        *,
        ref: str = "HEAD",
        staged: bool = False,
        use_static: bool = True,
    ) -> list[ReviewResult]:
        repo_path = Path(repo)
        diff_map = changed_lines(repo_path, ref=ref, staged=staged)
        results: list[ReviewResult] = []
        for rel_path, lines in diff_map.items():
            abs_path = repo_path / rel_path
            if not abs_path.exists():
                continue
            if detect_language(abs_path) == "unknown":
                continue
            results.append(self.review_file(abs_path, diff_lines=lines, use_static=use_static))
        return results


def _default_summary(findings: list[Finding]) -> str:
    if not findings:
        return "No issues found."
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
    parts = [f"{n} {sev}" for sev, n in sorted(counts.items(), key=lambda x: -(["critical", "high", "medium", "low", "info"].index(x[0]) * -1))]
    return f"Found {len(findings)} issue(s): " + ", ".join(parts) + "."
