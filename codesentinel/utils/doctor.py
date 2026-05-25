"""Environment health check — run with `python -m codesentinel.utils.doctor`."""

from __future__ import annotations

import shutil
import sys

import httpx
from rich.console import Console
from rich.table import Table

from codesentinel import __version__
from codesentinel.config import get_settings

console = Console()


def _check(name: str, ok: bool, detail: str, optional: bool = False) -> dict:
    return {"name": name, "ok": ok, "detail": detail, "optional": optional}


def run_checks() -> list[dict]:
    results: list[dict] = []
    settings = get_settings()

    # Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    results.append(
        _check("Python ≥ 3.10", sys.version_info >= (3, 10), py_ver)
    )

    # Ollama binary
    ollama_bin = shutil.which("ollama")
    results.append(_check("Ollama binary", bool(ollama_bin), ollama_bin or "not found"))

    # Ollama daemon
    try:
        r = httpx.get(f"{settings.ollama_host}/api/version", timeout=3)
        if r.status_code == 200:
            results.append(_check("Ollama daemon", True, f"version {r.json().get('version', '?')}"))
        else:
            results.append(_check("Ollama daemon", False, f"HTTP {r.status_code}"))
    except Exception as exc:
        results.append(_check("Ollama daemon", False, f"unreachable ({exc.__class__.__name__})"))

    # Model pulled
    try:
        r = httpx.get(f"{settings.ollama_host}/api/tags", timeout=5)
        tags = [m["name"] for m in r.json().get("models", [])] if r.status_code == 200 else []
        present = settings.ollama_model in tags
        results.append(
            _check(
                f"Model: {settings.ollama_model}",
                present,
                "pulled" if present else f"missing — run: ollama pull {settings.ollama_model}",
            )
        )
        if tags:
            results.append(_check("Pulled models", True, ", ".join(tags[:5]) + (" ..." if len(tags) > 5 else "")))
    except Exception as exc:
        results.append(_check("Pulled models", False, str(exc)))

    # Static analyzers — look in the venv's bin dir as well
    from codesentinel.analyzers.base import _which as which_with_venv

    for tool in ["bandit", "ruff", "eslint"]:
        path = which_with_venv(tool)
        # All three are optional augmentation: the LLM still works without them.
        results.append(
            _check(f"{tool}", bool(path), path or "not installed (optional)", optional=True)
        )

    return results


def main() -> int:
    settings = get_settings()
    console.rule(f"[bold cyan]CodeSentinel AI doctor[/bold cyan]  v{__version__}")
    console.print(f"Ollama host: [yellow]{settings.ollama_host}[/yellow]")
    console.print(f"Model:       [yellow]{settings.ollama_model}[/yellow]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Check", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Detail")

    all_ok = True
    for r in run_checks():
        if not r["ok"] and not r.get("optional"):
            all_ok = False
        if r["ok"]:
            mark = "[green]OK[/green]"
        elif r.get("optional"):
            mark = "[yellow]SKIP[/yellow]"
        else:
            mark = "[red]FAIL[/red]"
        table.add_row(r["name"], mark, r["detail"])

    console.print(table)
    console.print()
    if all_ok:
        console.print("[green]Environment looks healthy.[/green]")
    else:
        console.print("[red]Some required checks failed — see details above.[/red]")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
