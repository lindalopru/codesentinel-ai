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

SYSTEM_PROMPT_TEMPLATE = """\
You are CodeSentinel, a senior security-focused code reviewer. You analyse source code in any language and produce a structured JSON review.

Responsibilities:
- Be THOROUGH. Real production code almost always has at least one issue —
  inspect every function for the common pitfalls of its language.
- Always look hard for:
    * SECURITY:    SQL/command/template injection, XSS, hardcoded secrets,
                   missing input validation, unsafe deserialisation (pickle,
                   yaml.load, JSON.parse on untrusted), exposed API keys,
                   weak auth, logging of sensitive data, eval/exec on input.
    * BUGS:        null/undefined dereferences, off-by-one, mutable default
                   arguments, == vs ===, missing await on Promises, race
                   conditions on shared mutable state, ignored errors,
                   resource leaks (files / DB connections / goroutines).
    * PERFORMANCE: N+1 queries, blocking I/O on hot paths, unbounded loops,
                   inefficient data structures.
    * STYLE / DOCS: unused imports, dead code, magic numbers, missing
                   docstrings on public APIs.
- Be precise about line numbers (1-indexed, matching the code as given).
- Cite the exact offending fragment in `code_snippet`. Never paraphrase.
- A 30-line file dealing with HTTP, DB, secrets or user input typically has
  several issues — do not return an empty review out of laziness.
- It IS acceptable to return an empty review for genuinely trivial code
  (e.g. a 3-line pure function), but justify it via the summary.

Output contract — return ONLY a JSON object matching this schema exactly:

{{
  "summary": "<one-sentence overall assessment>",
  "findings": [
    {{
      "line_start": <int, 1-indexed>,
      "line_end": <int, >= line_start>,
      "severity": "critical" | "high" | "medium" | "low" | "info",
      "category": "bug" | "security" | "performance" | "style" | "documentation",
      "title": "<short imperative title, max 80 chars>",
      "description": "<2-4 sentences explaining the issue and its impact>",
      "suggestion": "<concrete fix; include a short corrected snippet if helpful>",
      "code_snippet": "<the offending lines, copied verbatim>"
    }}
  ]
}}

Rules:
- Output JSON only. No prose before or after. No markdown fences.
- Use double quotes. No trailing commas. No comments.
- The keys (summary, findings, line_start, severity, category, ...) MUST stay in English.
- The values for `severity` MUST stay as one of: critical, high, medium, low, info.
- The values for `category` MUST stay as one of: bug, security, performance, style, documentation.
- {language_directive}
- Severity scale:
  - critical: exploitable vulnerability or data-loss bug
  - high: probable bug, security weakness, or major performance issue
  - medium: likely bug or notable code smell
  - low: minor readability or convention violation
  - info: documentation gap or stylistic suggestion
- If the code has zero issues, return: {{"summary": "{no_issues}", "findings": []}}
- Keep "description" focused on WHY it matters, not just what it is.
"""


_LANG_DIRECTIVES = {
    "en": ("Write the natural-language fields (`summary`, `title`, `description`, `suggestion`) in ENGLISH.",
           "No issues found."),
    "es": ("Escribe los campos de texto natural (`summary`, `title`, `description`, `suggestion`) en ESPAÑOL.",
           "Sin hallazgos."),
}


def system_prompt_for(language: str = "en") -> str:
    directive, no_issues = _LANG_DIRECTIVES.get(language, _LANG_DIRECTIVES["en"])
    return SYSTEM_PROMPT_TEMPLATE.format(language_directive=directive, no_issues=no_issues)


# Back-compat: default English system prompt for callers that don't pass a language.
SYSTEM_PROMPT = system_prompt_for("en")


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

FEW_SHOT_ASSISTANT_1_EN = """\
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

FEW_SHOT_ASSISTANT_1_ES = """\
{
  "summary": "Dos errores graves: inyección SQL en la consulta de usuario y un argumento por defecto mutable que retiene estado entre llamadas.",
  "findings": [
    {
      "line_start": 5,
      "line_end": 6,
      "severity": "critical",
      "category": "security",
      "title": "Inyección SQL por concatenación de strings",
      "description": "Concatenar user_id directamente dentro de una cadena SQL permite a un atacante inyectar SQL arbitrario. Es explotable siempre que quien llama no sanitice previamente la entrada.",
      "suggestion": "Usa una consulta parametrizada: db.execute(\\"SELECT * FROM users WHERE id = ?\\", (user_id,))",
      "code_snippet": "query = \\"SELECT * FROM users WHERE id = \\" + str(user_id)\\n    db.execute(query)"
    },
    {
      "line_start": 1,
      "line_end": 1,
      "severity": "high",
      "category": "bug",
      "title": "Argumento por defecto mutable retiene estado entre llamadas",
      "description": "El valor por defecto items=[] se evalúa una sola vez al definir la función. Las llamadas posteriores sin items comparten la misma lista, lo que causa contaminación entre invocaciones.",
      "suggestion": "Usa un centinela: def charge_user(user_id, items=None): items = items or []",
      "code_snippet": "def charge_user(user_id, items=[]):"
    }
  ]
}"""

# Back-compat alias
FEW_SHOT_ASSISTANT_1 = FEW_SHOT_ASSISTANT_1_EN


FEW_SHOT_USER_2 = """\
Language: JavaScript
File: utils.js

```
1  function add(a, b) {
2    return a + b;
3  }
```
"""

FEW_SHOT_ASSISTANT_2_EN = """{"summary": "No issues found.", "findings": []}"""
FEW_SHOT_ASSISTANT_2_ES = """{"summary": "Sin hallazgos.", "findings": []}"""
FEW_SHOT_ASSISTANT_2    = FEW_SHOT_ASSISTANT_2_EN


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
    output_language: str = "en",
) -> list[dict[str, str]]:
    """Compose the full message stack for the chat endpoint.

    `output_language` controls the language of the natural-language fields
    (summary / title / description / suggestion) — "en" or "es".
    """
    assistant_1 = FEW_SHOT_ASSISTANT_1_ES if output_language == "es" else FEW_SHOT_ASSISTANT_1_EN
    assistant_2 = FEW_SHOT_ASSISTANT_2_ES if output_language == "es" else FEW_SHOT_ASSISTANT_2_EN
    return [
        {"role": "system", "content": system_prompt_for(output_language)},
        {"role": "user", "content": FEW_SHOT_USER_1},
        {"role": "assistant", "content": assistant_1},
        {"role": "user", "content": FEW_SHOT_USER_2},
        {"role": "assistant", "content": assistant_2},
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
