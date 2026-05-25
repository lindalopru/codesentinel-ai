"""HTML rendering helpers for the Gradio web UI — premium card style."""

from __future__ import annotations

import html

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from codesentinel.schema import Finding, ReviewResult, Severity

_FORMATTER = HtmlFormatter(nowrap=True, noclasses=True, style="dracula")

SEVERITY_ICON = {
    Severity.CRITICAL: "🚨",
    Severity.HIGH: "❗",
    Severity.MEDIUM: "⚠️",
    Severity.LOW: "ℹ️",
    Severity.INFO: "💡",
}


def _highlight(code: str, language: str) -> str:
    if not code.strip():
        return ""
    lookup = (language or "").lower()
    if lookup in ("js", "javascript"):
        lookup = "javascript"
    elif lookup in ("ts", "typescript", "tsx"):
        lookup = "typescript"
    try:
        lexer = get_lexer_by_name(lookup, stripall=False)
    except ClassNotFound:
        try:
            lexer = get_lexer_by_name("text")
        except ClassNotFound:
            return f"<pre>{html.escape(code)}</pre>"
    return f"<pre>{highlight(code, lexer, _FORMATTER)}</pre>"


def _finding_card(f: Finding, language: str) -> str:
    sev = f.severity.value
    icon = SEVERITY_ICON.get(f.severity, "•")
    lines = f"L{f.line_start}" if f.line_start == f.line_end else f"L{f.line_start}–{f.line_end}"
    source_html = ""
    if f.source != "llm":
        source_label = html.escape(f.source)
        rule = f" / {html.escape(f.rule_id)}" if f.rule_id else ""
        source_html = (
            f"<span class='dot'></span>"
            f"<span>via <b>{source_label}</b>{rule}</span>"
        )
    suggestion_html = ""
    if f.suggestion.strip():
        suggestion_html = (
            f"<div class='finding-suggestion'><b>Sugerencia:</b> {html.escape(f.suggestion)}</div>"
        )
    snippet_html = ""
    if f.code_snippet.strip():
        snippet_html = f"<div class='finding-snippet'>{_highlight(f.code_snippet, language)}</div>"
    return (
        f"<div class='finding-card sev-{sev}'>"
        f"<div class='finding-header'>"
        f"<span class='severity-badge {sev}'>{icon} {sev.upper()}</span>"
        f"<h4 class='finding-title'>{html.escape(f.title)}</h4>"
        f"</div>"
        f"<div class='finding-meta'>"
        f"<code>{html.escape(f.category.value)}</code>"
        f"<span class='dot'></span>"
        f"<span>{lines}</span>"
        f"{source_html}"
        f"</div>"
        f"<div class='finding-desc'>{html.escape(f.description)}</div>"
        f"{suggestion_html}"
        f"{snippet_html}"
        f"</div>"
    )


EMPTY_STATE = """
<div class='cs-empty'>
  <div class='ico'>
    <svg viewBox='0 0 24 24'>
      <circle cx='11' cy='11' r='8'/>
      <path d='m21 21-4.3-4.3'/>
    </svg>
  </div>
  <h3>Sin análisis aún</h3>
  <p>Pega código, sube un archivo o prueba un ejemplo para empezar.</p>
</div>
"""

NO_FINDINGS = """
<div class='cs-success'>
  <div class='ico'>
    <svg viewBox='0 0 24 24'>
      <polyline points='20 6 9 17 4 12'/>
    </svg>
  </div>
  <div>
    <h3>Sin hallazgos</h3>
    <p>El modelo no detectó problemas en el código revisado.</p>
  </div>
</div>
"""


def render_findings_html(results: ReviewResult | list[ReviewResult]) -> str:
    multi = isinstance(results, list)
    bucket = results if multi else [results]
    if not bucket or all(not r.findings for r in bucket):
        return NO_FINDINGS

    out: list[str] = []
    if multi:
        out.append(
            f"<div class='cs-status'>📦 <b>{len(bucket)}</b> archivos revisados</div>"
        )
    for r in bucket:
        if multi:
            out.append(
                f"<h3 style='margin:18px 0 4px; font-size:14px; font-weight:700;'>"
                f"📄 <code style='font-family:ui-monospace; font-size:12.5px;'>{html.escape(r.file_path)}</code>"
                f" <span style='color:#64748B; font-weight:500;'>· {html.escape(r.language)}</span></h3>"
            )
        if not r.findings:
            out.append(
                "<div class='cs-status'>✅ Sin hallazgos en este archivo.</div>"
            )
            continue
        for f in r.findings:
            out.append(_finding_card(f, r.language))
    return "\n".join(out)


def render_stats_html(results: ReviewResult | list[ReviewResult]) -> str:
    bucket = results if isinstance(results, list) else [results]
    totals: dict[str, int] = {s.value: 0 for s in Severity}
    for r in bucket:
        for k, v in r.counts_by_severity.items():
            totals[k] += v

    cards = []
    for sev in ("critical", "high", "medium", "low", "info"):
        n = totals[sev]
        zero_class = " zero" if n == 0 else ""
        cards.append(
            f"<div class='cs-stat-card {sev}{zero_class}'>"
            f"<div class='v'>{n}</div>"
            f"<div class='l'>{sev}</div>"
            f"</div>"
        )
    return "<div class='cs-stats-grid'>" + "".join(cards) + "</div>"
