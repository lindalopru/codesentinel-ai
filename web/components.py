"""HTML rendering helpers for the Gradio web UI."""

from __future__ import annotations

import html

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from codesentinel.schema import Finding, ReviewResult, Severity

_FORMATTER = HtmlFormatter(nowrap=True, noclasses=True, style="monokai")


def _highlight(code: str, language: str) -> str:
    if not code.strip():
        return ""
    try:
        lexer = get_lexer_by_name(language, stripall=False)
    except ClassNotFound:
        try:
            lexer = get_lexer_by_name("text")
        except ClassNotFound:
            return f"<pre>{html.escape(code)}</pre>"
    return f"<pre>{highlight(code, lexer, _FORMATTER)}</pre>"


def _finding_card(f: Finding, language: str) -> str:
    sev = f.severity.value
    lines = f"L{f.line_start}" if f.line_start == f.line_end else f"L{f.line_start}-{f.line_end}"
    source_tag = ""
    if f.source != "llm":
        source_tag = f"<span class=\"meta\"> via {html.escape(f.source)}"
        if f.rule_id:
            source_tag += f" / {html.escape(f.rule_id)}"
        source_tag += "</span>"
    suggestion_html = ""
    if f.suggestion.strip():
        suggestion_html = f"<div class=\"suggestion\"><b>Suggestion:</b> {html.escape(f.suggestion)}</div>"
    snippet_html = _highlight(f.code_snippet, language) if f.code_snippet else ""
    return (
        f"<div class=\"finding-card sev-{sev}\">"
        f"<h4><span class=\"severity-badge {sev}\">{sev.upper()}</span> {html.escape(f.title)}</h4>"
        f"<div class=\"meta\">{html.escape(f.category.value)} · {lines}{source_tag}</div>"
        f"<div>{html.escape(f.description)}</div>"
        f"{suggestion_html}"
        f"{snippet_html}"
        f"</div>"
    )


def render_findings_html(results: ReviewResult | list[ReviewResult]) -> str:
    multi = isinstance(results, list)
    bucket = results if multi else [results]
    if not bucket or all(not r.findings for r in bucket):
        return "<div class='summary-banner'><b>✓ No findings.</b> The code looks clean.</div>"

    out: list[str] = []
    if multi:
        out.append(
            f"<div class='summary-banner'>Reviewed <b>{len(bucket)}</b> files. Findings below.</div>"
        )
    for r in bucket:
        if multi:
            out.append(f"<h3>📄 <code>{html.escape(r.file_path)}</code> <small>({html.escape(r.language)})</small></h3>")
        if not r.findings:
            out.append("<div class='summary-banner'>✓ No findings in this file.</div>")
            continue
        for f in r.findings:
            out.append(_finding_card(f, r.language))
    return "\n".join(out)


def severity_counts(results: ReviewResult | list[ReviewResult]) -> list[list]:
    bucket = results if isinstance(results, list) else [results]
    totals: dict[str, int] = {s.value: 0 for s in Severity}
    for r in bucket:
        for k, v in r.counts_by_severity.items():
            totals[k] += v
    return [
        ["CRITICAL", totals["critical"]],
        ["HIGH", totals["high"]],
        ["MEDIUM", totals["medium"]],
        ["LOW", totals["low"]],
        ["INFO", totals["info"]],
    ]
