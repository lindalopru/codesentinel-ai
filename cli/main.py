"""CodeSentinel CLI — Typer + Rich front-end for the review engine."""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from cli.rich_render import render, render_many
from codesentinel import __version__
from codesentinel.config import get_settings
from codesentinel.llm.client import OllamaClient
from codesentinel.reporting import to_json, to_markdown, to_sarif
from codesentinel.review import ReviewEngine
from codesentinel.schema import ReviewResult, Severity

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
    help="[bold cyan]CodeSentinel AI[/bold cyan] — Local AI Code Reviewer",
)
console = Console()


class OutputFormat(str, Enum):
    pretty = "pretty"
    json = "json"
    markdown = "markdown"
    sarif = "sarif"


class FailOn(str, Enum):
    none = "none"
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


def _serialise(results: ReviewResult | list[ReviewResult], fmt: OutputFormat) -> str:
    if fmt == OutputFormat.json:
        return to_json(results)
    if fmt == OutputFormat.markdown:
        return to_markdown(results)
    if fmt == OutputFormat.sarif:
        return to_sarif(results)
    return ""  # pretty is handled separately


def _exit_code(results: list[ReviewResult], fail_on: FailOn) -> int:
    if fail_on == FailOn.none:
        return 0
    threshold = Severity(fail_on.value)
    for r in results:
        for f in r.findings:
            if f.severity.order >= threshold.order:
                return 1
    return 0


def _maybe_write(content: str, output: Path | None) -> None:
    if output is None:
        if content:
            console.print(content)
        return
    output.write_text(content, encoding="utf-8")
    console.print(f"[green]Report written to {output}[/green]")


@app.command()
def review(
    path: Path = typer.Argument(..., exists=True, readable=True, help="File or directory to review"),
    language: str | None = typer.Option(None, "--language", "-l", help="Override language detection"),
    model: str | None = typer.Option(None, "--model", "-m", help="Override Ollama model"),
    severity: Severity = typer.Option(Severity.INFO, "--severity", "-s", help="Minimum severity to display"),
    fmt: OutputFormat = typer.Option(OutputFormat.pretty, "--format", "-f", help="Output format"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write report to file"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Recurse into directories (auto-true if path is a dir)"),
    no_static: bool = typer.Option(False, "--no-static", help="Disable static-analyzer augmentation"),
    summary_only: bool = typer.Option(False, "--summary", help="Show severity totals only"),
    fail_on: FailOn = typer.Option(FailOn.none, "--fail-on", help="Exit non-zero if any finding ≥ this severity"),
) -> None:
    """Review a file or directory."""
    settings = get_settings()
    client = OllamaClient(settings, model=model) if model else OllamaClient(settings)
    engine = ReviewEngine(client=client, settings=settings)

    use_static = not no_static
    if path.is_dir() or recursive:
        results = engine.review_dir(path, use_static=use_static)
    else:
        results = [engine.review_file(path, use_static=use_static)]

    filtered = [r.filter_by_severity(severity) for r in results]

    if fmt == OutputFormat.pretty:
        if summary_only:
            _print_summary_table(filtered)
        else:
            if len(filtered) == 1:
                render(filtered[0], console=console)
            else:
                render_many(filtered, console=console)
                _print_summary_table(filtered)
    else:
        single = filtered[0] if len(filtered) == 1 else filtered
        _maybe_write(_serialise(single, fmt), output)

    raise typer.Exit(code=_exit_code(filtered, fail_on))


@app.command()
def diff(
    repo: Path = typer.Option(Path("."), "--repo", help="Path to git repository", exists=True),
    since: str = typer.Option("HEAD", "--since", help="Git ref to compare against (e.g. HEAD~3)"),
    staged: bool = typer.Option(False, "--staged", help="Review staged changes only"),
    fmt: OutputFormat = typer.Option(OutputFormat.pretty, "--format", "-f"),
    severity: Severity = typer.Option(Severity.INFO, "--severity", "-s"),
    output: Path | None = typer.Option(None, "--output", "-o"),
    fail_on: FailOn = typer.Option(FailOn.none, "--fail-on"),
) -> None:
    """Review only the lines changed in a git diff."""
    settings = get_settings()
    engine = ReviewEngine(settings=settings)
    results = engine.review_diff(repo, ref=since, staged=staged)
    if not results:
        console.print("[yellow]No reviewable changes detected.[/yellow]")
        raise typer.Exit(0)
    filtered = [r.filter_by_severity(severity) for r in results]
    if fmt == OutputFormat.pretty:
        render_many(filtered, console=console)
        _print_summary_table(filtered)
    else:
        _maybe_write(_serialise(filtered, fmt), output)
    raise typer.Exit(code=_exit_code(filtered, fail_on))


@app.command()
def models() -> None:
    """List models pulled in the local Ollama daemon."""
    client = OllamaClient()
    tags = client.list_models()
    if not tags:
        console.print("[red]No models pulled or Ollama not reachable.[/red]")
        console.print("Try: [bold]ollama pull qwen2.5-coder:7b-instruct-q4_K_M[/bold]")
        raise typer.Exit(1)
    table = Table(title="Pulled models", show_header=True)
    table.add_column("Tag", style="cyan")
    current = get_settings().ollama_model
    for t in tags:
        marker = " [bold green](in use)[/bold green]" if t == current else ""
        table.add_row(t + marker)
    console.print(table)


@app.command()
def doctor() -> None:
    """Verify environment health (python, Ollama, model, analyzers)."""
    from codesentinel.utils.doctor import main as run_doctor

    raise typer.Exit(code=run_doctor())


@app.command()
def version() -> None:
    """Show version."""
    console.print(f"CodeSentinel AI v{__version__}")


def _print_summary_table(results: list[ReviewResult]) -> None:
    table = Table(title="CodeSentinel — summary", show_header=True, header_style="bold magenta")
    table.add_column("File", style="cyan")
    table.add_column("Critical", justify="right")
    table.add_column("High", justify="right")
    table.add_column("Medium", justify="right")
    table.add_column("Low", justify="right")
    table.add_column("Info", justify="right")
    table.add_column("Total", justify="right", style="bold")
    grand: dict[str, int] = {s.value: 0 for s in Severity}
    for r in results:
        c = r.counts_by_severity
        for k, v in c.items():
            grand[k] += v
        table.add_row(
            r.file_path,
            str(c["critical"]),
            str(c["high"]),
            str(c["medium"]),
            str(c["low"]),
            str(c["info"]),
            str(len(r.findings)),
        )
    table.add_section()
    table.add_row(
        "[bold]Total[/bold]",
        str(grand["critical"]),
        str(grand["high"]),
        str(grand["medium"]),
        str(grand["low"]),
        str(grand["info"]),
        str(sum(grand.values())),
    )
    console.print(table)


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
