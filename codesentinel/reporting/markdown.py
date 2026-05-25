"""Render ReviewResult as a Markdown report."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from codesentinel.schema import Finding, ReviewResult, Severity

SEVERITY_EMOJI = {
    Severity.CRITICAL: "🚨",
    Severity.HIGH: "❗",
    Severity.MEDIUM: "⚠️",
    Severity.LOW: "ℹ️",
    Severity.INFO: "💡",
}


def _finding_block(f: Finding) -> str:
    emoji = SEVERITY_EMOJI.get(f.severity, "•")
    source_tag = f" *(via {f.source}{f' / {f.rule_id}' if f.rule_id else ''})*"
    lines = f"L{f.line_start}" if f.line_start == f.line_end else f"L{f.line_start}-{f.line_end}"
    snippet = ""
    if f.code_snippet.strip():
        snippet = f"\n```\n{f.code_snippet.strip()}\n```"
    suggestion = ""
    if f.suggestion.strip():
        suggestion = f"\n\n**Suggestion:** {f.suggestion.strip()}"
    return (
        f"### {emoji} [{f.severity.value.upper()}] {f.title}  \n"
        f"`{f.category.value}` · {lines}{source_tag}\n\n"
        f"{f.description.strip()}{suggestion}{snippet}"
    )


def _summary_table(results: Iterable[ReviewResult]) -> str:
    rows = []
    for r in results:
        c = r.counts_by_severity
        rows.append(
            f"| `{r.file_path}` | {c['critical']} | {c['high']} | {c['medium']} | {c['low']} | {c['info']} | {len(r.findings)} |"
        )
    header = (
        "| File | Critical | High | Medium | Low | Info | Total |\n"
        "|---|---:|---:|---:|---:|---:|---:|"
    )
    return header + "\n" + "\n".join(rows)


def to_markdown(result: ReviewResult | list[ReviewResult]) -> str:
    results = result if isinstance(result, list) else [result]
    if not results:
        return "# CodeSentinel report\n\nNo files reviewed."

    out: list[str] = []
    out.append("# CodeSentinel AI — Review report")
    out.append(f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_  ")
    if results:
        out.append(f"_Model: `{results[0].model}`_\n")

    out.append("## Summary\n")
    out.append(_summary_table(results))
    out.append("")

    for r in results:
        out.append(f"\n---\n## `{r.file_path}` ({r.language})")
        out.append(f"_{r.summary}_\n")
        if not r.findings:
            out.append("_No findings._")
            continue
        for f in r.findings:
            out.append(_finding_block(f))
            out.append("")

    return "\n".join(out).rstrip() + "\n"
