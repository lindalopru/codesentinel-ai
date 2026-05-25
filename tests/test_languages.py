"""Language detection."""

from __future__ import annotations

from codesentinel.languages import detect_language, display_name


def test_python_detection():
    assert detect_language("foo.py") == "python"
    assert detect_language("foo.pyi") == "python"


def test_typescript_detection():
    assert detect_language("foo.ts") == "typescript"
    assert detect_language("Foo.TSX") == "typescript"  # case-insensitive


def test_unknown_extension():
    assert detect_language("file.xyz") == "unknown"


def test_display_names():
    assert display_name("python") == "Python"
    assert display_name("javascript") == "JavaScript"
    assert display_name("unknown") == "Unknown"
