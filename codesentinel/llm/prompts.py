"""System prompt and few-shot examples for the LLM reviewer.

These prompts are the core IP of CodeSentinel. They:
- Force a strict JSON output contract so parsing is reliable.
- Provide two contrasting few-shot examples (one with multiple findings,
  one with zero) so the model knows how to behave on clean code.
- Allow optional "augmentation" hints from static analyzers to ground
  the model and reduce hallucinations.
"""

from __future__ import annotations

from codesentinel.languages import display_name
from codesentinel.utils.files import numbered_lines

SYSTEM_PROMPT = """\
You are CodeSentinel, an expert AI code reviewer. You analyse source code and produce a structured JSON review.

Responsibilities:
- Identify defects, vulnerabilities, performance issues, style problems, and missing documentation.
- Be precise about line numbers (1-indexed, matching the code as given).
- Justify every finding briefly and propose a concrete fix.
- Prefer no false positives over many low-quality findings. If unsure, omit.

Output contract — return ONLY a JSON object matching this schema exactly:

{
  "summary": "<one-sentence overall assessment>",
  "findings": [
    {
      "line_start": <int, 1-indexed>,
      "line_end": <int, >= line_start>,
      "severity": "critical" | "high" | "medium" | "low" | "info",
      "category": "bug" | "security" | "performance" | "style" | "documentation",
      "title": "<short imperative title, max 80 chars>",
      "description": "<2-4 sentences explaining the issue and its impact>",
      "suggestion": "<concrete fix; include a short corrected snippet if helpful>",
      "code_snippet": "<the offending lines, copied verbatim>"
    }
  ]
}

Rules:
- Output JSON only. No prose before or after. No markdown fences.
- Use double quotes. No trailing commas. No comments.
- Severity scale:
  - critical: exploitable vulnerability or data-loss bug
  - high: probable bug, security weakness, or major performance issue
  - medium: likely bug or notable code smell
  - low: minor readability or convention violation
  - info: documentation gap or stylistic suggestion
- If the code has zero issues, return: {"summary": "No issues found.", "findings": []}
- Keep "description" focused on WHY it matters, not just what it is.
"""


FEW_SHOT_USER_1 = """\
Language: Python
File: payments.py

```
1  def charge_user(user_id, items=[]):
2      total = 0
3      for item in items:
4          total += item.price
5      query = "SELECT * FROM users WHERE id = " + str(user_id)
6      db.execute(query)
7      return total
```
"""

FEW_SHOT_ASSISTANT_1 = """\
{
  "summary": "Two serious bugs: SQL injection in the user query and a mutable default argument that retains state across calls.",
  "findings": [
    {
      "line_start": 5,
      "line_end": 6,
      "severity": "critical",
      "category": "security",
      "title": "SQL injection via string concatenation",
      "description": "Concatenating user_id directly into a SQL string allows an attacker to inject arbitrary SQL. This is exploitable whenever the caller does not pre-sanitise the input.",
      "suggestion": "Use a parameterised query: db.execute(\\"SELECT * FROM users WHERE id = ?\\", (user_id,))",
      "code_snippet": "query = \\"SELECT * FROM users WHERE id = \\" + str(user_id)\\n    db.execute(query)"
    },
    {
      "line_start": 1,
      "line_end": 1,
      "severity": "high",
      "category": "bug",
      "title": "Mutable default argument retains state across calls",
      "description": "Default items=[] is evaluated once at function-definition time. Subsequent calls without items share the same list, causing cross-call contamination.",
      "suggestion": "Use a sentinel: def charge_user(user_id, items=None): items = items or []",
      "code_snippet": "def charge_user(user_id, items=[]):"
    }
  ]
}"""


FEW_SHOT_USER_2 = """\
Language: JavaScript
File: utils.js

```
1  function add(a, b) {
2    return a + b;
3  }
```
"""

FEW_SHOT_ASSISTANT_2 = """{"summary": "No issues found.", "findings": []}"""


def build_user_message(
    *,
    code: str,
    language: str,
    filename: str = "snippet",
    augmentation: list[str] | None = None,
) -> str:
    """Render the per-call user prompt with numbered code and optional hints."""
    body = numbered_lines(code, start=1)
    aug_block = ""
    if augmentation:
        bullets = "\n".join(f"- {item}" for item in augmentation)
        aug_block = (
            "\nLightweight static analysers offer the hints below as a starting "
            "point — these do NOT constrain you. Re-classify their severity using your "
            "OWN judgement (e.g. raise SQL injection to 'critical', raise log-secrets to 'high'). "
            "Independently look for ADDITIONAL bugs, vulnerabilities, performance issues, and "
            "code smells the analysers may have missed. Do not skip an issue just because an "
            "analyser already mentioned it — emit your own finding with your assessment.\n"
            f"{bullets}\n"
        )
    return (
        f"Language: {display_name(language)}\n"
        f"File: {filename}\n"
        f"{aug_block}\n"
        "```\n"
        f"{body}\n"
        "```\n"
    )


def build_messages(
    *,
    code: str,
    language: str,
    filename: str = "snippet",
    augmentation: list[str] | None = None,
) -> list[dict[str, str]]:
    """Compose the full message stack for the chat endpoint."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": FEW_SHOT_USER_1},
        {"role": "assistant", "content": FEW_SHOT_ASSISTANT_1},
        {"role": "user", "content": FEW_SHOT_USER_2},
        {"role": "assistant", "content": FEW_SHOT_ASSISTANT_2},
        {
            "role": "user",
            "content": build_user_message(
                code=code,
                language=language,
                filename=filename,
                augmentation=augmentation,
            ),
        },
    ]
