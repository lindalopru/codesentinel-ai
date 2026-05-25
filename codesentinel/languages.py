"""Source-code language detection and per-language metadata."""

from __future__ import annotations

from pathlib import Path

EXTENSION_MAP: dict[str, str] = {
    # Python
    ".py": "python",
    ".pyi": "python",
    # JavaScript / TypeScript
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    # JVM
    ".java": "java",
    ".kt": "kotlin",
    ".scala": "scala",
    # Native
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".rs": "rust",
    ".go": "go",
    # Misc
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".sh": "bash",
    ".bash": "bash",
}

SUPPORTED_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "java",
    "go",
    "rust",
    "c",
    "cpp",
    "ruby",
    "php",
    "csharp",
    "kotlin",
    "swift",
    "bash",
}

# Display names for prompts and UIs
DISPLAY_NAMES: dict[str, str] = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "go": "Go",
    "rust": "Rust",
    "c": "C",
    "cpp": "C++",
    "ruby": "Ruby",
    "php": "PHP",
    "csharp": "C#",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "bash": "Bash",
}


def detect_language(path: str | Path) -> str:
    """Detect a language from a file path. Returns 'unknown' on miss."""
    p = Path(path)
    return EXTENSION_MAP.get(p.suffix.lower(), "unknown")


def display_name(language: str) -> str:
    return DISPLAY_NAMES.get(language, language.title())
