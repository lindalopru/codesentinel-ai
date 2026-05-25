"""Chunker tests."""

from __future__ import annotations

from codesentinel.review.chunker import chunk_code


def test_small_file_single_chunk():
    code = "\n".join(f"line{i}" for i in range(50))
    chunks = chunk_code(code, max_lines=1000)
    assert len(chunks) == 1
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 50


def test_large_file_split_with_overlap():
    code = "\n".join(f"line{i}" for i in range(3000))
    chunks = chunk_code(code, max_lines=1000, overlap=50)
    assert len(chunks) >= 3
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 1000
    # Second chunk should overlap the first by overlap lines
    assert chunks[1].start_line == 1000 - 50 + 1


def test_chunk_preserves_total_coverage():
    code = "\n".join(f"line{i}" for i in range(2500))
    chunks = chunk_code(code, max_lines=1000, overlap=20)
    assert chunks[-1].end_line == 2500
