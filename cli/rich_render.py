"""Render ReviewResult objects in a colourful terminal."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from codesentinel.languages import display_name
from codesentinel.schema import Finding, ReviewResult, Severity

_SEV_STYLE = {
    Severity.CRITICAL: "bold white on red",
    Severity.HIGH: "bold red",
    Severity.MEDIUM: "bold yellow",
    Severity.LOW: "bold cyan",
    Severity.INFO: "dim",
}

_SEV_ICON = {
    Severity.CRITICAL: "[CRIT]",
    Severity.HIGH: "[HIGH]",
    Severity.MEDIUM: "[MED ]",
    Severity.LOW: "[LOW ]",
    Severity.INFO: "[INFO]",
}


def _severity_badge(sev: Severity) -> Text:
    return Text(_SEV_ICON[sev], style=_SEV_STYLE[sev])


def _finding_panel(f: Finding, language: str) -> Panel:
    title = Text.assemble(
        _severity_badge(f.severity),
        ("  ", ""),
        (f.title, "bold white"),
        ("  ", ""),
        (f"({f.category.value} · line {f.line_start}", "dim"),
        ("-" if f.line_end != f.line_start else "", "dim"),
        (f"{f.line_end}" if f.line_end != f.line_start else "", "dim"),
        (")", "dim"),
    )
    sub = Text("")
    if f.source != "llm":
        sub.append(f"via {f.source}", style="italic dim")
        if f.rule_id:
            sub.append(f" / {f.rule_id}", style="italic dim")
        sub.append("\n\n")
    sub.append(f.description.strip(), style="white")
    if f.suggestion.strip():
        sub.append("\n\n")
        sub.append("Suggestion: ", style="bold green")
        sub.append(f.suggestion.strip(), style="green")
    panel_body: list = [sub]
    if f.code_snippet.strip():
        try:
            syn = Syntax(f.code_snippet.rstrip(), language, line_numbers=False, theme="monokai", word_wrap=True)
            panel_body.append(syn)
        except Exception:
            pass
    return Panel(
        Text.assemble(*[(p if isinstance(p, str) else p.plain, "") for p in [panel_body[0]]]) if False else panel_body[0],
        title=title,
        border_style=_SEV_STYLE[f.severity].split()[-1] if " " in _SEV_STYLE[f.severity] else _SEV_STYLE[f.severity],
        title_align="left",
        padding=(0, 1),
        subtitle=None,
    )


def render(result: ReviewResult, *, console: Console | None = None) -> None:
    console = console or Console()
    counts = result.counts_by_severity
    header = (
        f"[bold cyan]{result.file_path}[/bold cyan]  "
        f"[dim]({display_name(result.language)} · {result.model} · {result.duration_s}s)[/dim]"
    )
    console.print(header)
    console.print(f"[italic]{result.summary}[/italic]\n")

    if not result.findings:
        console.print("[green]✓ No findings.[/green]")
        return

    for f in result.findings:
        console.print(_finding_panel(f, result.language))

    table = Table(show_header=True, header_style="bold magenta", title="Severity totals")
    table.add_column("Severity", style="cyan")
    table.add_column("Count", justify="right")
    for sev in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
        table.add_row(
            Text(sev.value.upper(), style=_SEV_STYLE[sev]),
            str(counts[sev.value]),
        )
    console.print()
    console.print(table)


def render_many(results: list[ReviewResult], *, console: Console | None = None) -> None:
    console = console or Console()
    for r in results:
        console.rule(f"[bold]{r.file_path}")
        render(r, console=console)
        console.print()
