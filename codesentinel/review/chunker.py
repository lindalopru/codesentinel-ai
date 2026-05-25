"""Split large source files into reviewable windows with line-number context preserved."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CodeChunk:
    code: str
    start_line: int  # 1-indexed line number in the original file
    end_line: int


def chunk_code(source: str, *, max_lines: int = 1500, overlap: int = 50) -> list[CodeChunk]:
    """Split source into overlapping windows.

    Each chunk carries the absolute line numbers of its first/last line so
    the engine can shift LLM-reported line numbers back into the original file.
    """
    lines = source.splitlines()
    if len(lines) <= max_lines:
        return [CodeChunk(code=source, start_line=1, end_line=max(1, len(lines)))]

    if overlap >= max_lines:
        overlap = max_lines // 4

    step = max_lines - overlap
    chunks: list[CodeChunk] = []
    i = 0
    while i < len(lines):
        end = min(i + max_lines, len(lines))
        chunk_text = "\n".join(lines[i:end])
        chunks.append(CodeChunk(code=chunk_text, start_line=i + 1, end_line=end))
        if end >= len(lines):
            break
        i += step
    return chunks
