"""Safe file reading and small filesystem helpers."""

from __future__ import annotations

from pathlib import Path

MAX_BYTES_DEFAULT = 2 * 1024 * 1024  # 2 MiB safety cap


def read_text_safe(path: str | Path, max_bytes: int = MAX_BYTES_DEFAULT) -> str:
    """Read a text file, tolerating non-UTF8 sources."""
    p = Path(path)
    raw = p.read_bytes()
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    return raw.decode("utf-8", errors="replace")


def numbered_lines(code: str, start: int = 1) -> str:
    """Prefix each line with its 1-indexed line number, padded for readability."""
    lines = code.splitlines()
    width = len(str(start + len(lines) - 1))
    return "\n".join(f"{i:>{width}}  {line}" for i, line in enumerate(lines, start=start))
