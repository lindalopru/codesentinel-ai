"""Merge findings from multiple sources, dedup similar ones."""

from __future__ import annotations

from rapidfuzz import fuzz

from codesentinel.schema import Finding

# Two findings are considered duplicates if their titles are very similar
# AND they refer to lines that overlap or sit within this many lines of each other.
_TITLE_SIMILARITY_THRESHOLD = 78  # 0–100
_LINE_PROXIMITY = 2


def _lines_close(a: Finding, b: Finding) -> bool:
    return (
        a.line_start <= b.line_end + _LINE_PROXIMITY
        and b.line_start <= a.line_end + _LINE_PROXIMITY
    )


def _similar_title(a: Finding, b: Finding) -> bool:
    if a.category != b.category:
        return False
    return fuzz.token_set_ratio(a.title, b.title) >= _TITLE_SIMILARITY_THRESHOLD


def merge_findings(*groups: list[Finding]) -> list[Finding]:
    """Concatenate, dedup, then sort by severity desc, line asc."""
    merged: list[Finding] = []
    for group in groups:
        for f in group:
            duplicate_of = next(
                (m for m in merged if _lines_close(m, f) and _similar_title(m, f)),
                None,
            )
            if duplicate_of is None:
                merged.append(f)
                continue
            # Prefer the more severe finding's metadata; concatenate sources.
            if f.severity.order > duplicate_of.severity.order:
                duplicate_of.severity = f.severity
                duplicate_of.description = f.description or duplicate_of.description
                duplicate_of.suggestion = f.suggestion or duplicate_of.suggestion
            if f.source not in duplicate_of.source.split("+"):
                duplicate_of.source = f"{duplicate_of.source}+{f.source}"

    merged.sort(key=lambda x: (-x.severity.order, x.line_start, x.title))
    return merged
