"""Parse git diff to identify changed lines per file."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_FILE_RE = re.compile(r"^\+\+\+ b/(.+)$")


def parse_unified_diff(diff: str) -> dict[str, set[int]]:
    """Return {file_path: set_of_changed_line_numbers_in_new_file}.

    Recognises only the post-image (+) lines — that's what we want to review.
    """
    result: dict[str, set[int]] = {}
    current_file: str | None = None
    current_line = 0
    in_hunk = False
    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            m = _FILE_RE.match(raw)
            if m:
                current_file = m.group(1)
                result.setdefault(current_file, set())
            in_hunk = False
            continue
        if raw.startswith("@@"):
            m = _HUNK_RE.match(raw)
            if m and current_file is not None:
                current_line = int(m.group(1))
                in_hunk = True
            continue
        if not in_hunk or current_file is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            result[current_file].add(current_line)
            current_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            # Lines removed don't advance the new-file counter.
            continue
        else:
            current_line += 1
    return result


def changed_lines(repo: Path, *, ref: str = "HEAD", staged: bool = False) -> dict[str, set[int]]:
    """Run `git diff` and return changed-line ranges per file."""
    cmd = ["git", "-C", str(repo), "diff", "-U0"]
    if staged:
        cmd.append("--staged")
    else:
        cmd.append(ref)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}
    if proc.returncode != 0 or not proc.stdout:
        return {}
    return parse_unified_diff(proc.stdout)
