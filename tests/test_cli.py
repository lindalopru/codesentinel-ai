"""Typer CLI smoke tests via CliRunner."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_version_runs():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "CodeSentinel" in result.stdout


def test_help_lists_subcommands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ["review", "diff", "models", "doctor", "version"]:
        assert cmd in result.stdout


def test_review_help_mentions_severity():
    result = runner.invoke(app, ["review", "--help"])
    assert result.exit_code == 0
    assert "severity" in result.stdout.lower()


def test_review_rejects_missing_file(tmp_path: Path):
    missing = tmp_path / "does_not_exist.py"
    result = runner.invoke(app, ["review", str(missing)])
    assert result.exit_code != 0
