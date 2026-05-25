# Prompt engineering

The prompt is the most important piece of intellectual property in CodeSentinel. The output contract is the contract between the LLM's free-form thinking and the rest of the system's typed, validated data. This document captures *why* the prompt looks the way it does.

## Design goals

1. **Strict JSON output** — every byte downstream parses with `json.loads`.
2. **Stable severity vocabulary** — five fixed labels.
3. **Stable category vocabulary** — five fixed buckets.
4. **Few-shot anchoring** — show the model exactly one positive example and one negative (zero-findings) example.
5. **Augmentation hints** — when classical analysers fire, surface their findings without letting the model defer to them.
6. **No false-positive bias** — explicitly instruct: "If unsure, omit."

## The system prompt

See [`codesentinel/llm/prompts.py:SYSTEM_PROMPT`](../codesentinel/llm/prompts.py). Key clauses:

- "Output JSON only. No prose before or after. No markdown fences." → guards against the most common failure mode.
- "Use double quotes. No trailing commas. No comments." → standard JSON gotchas.
- "Prefer no false positives over many low-quality findings. If unsure, omit." → explicit precision-over-recall instruction.
- "Keep description focused on WHY it matters, not just what it is." → drives useful explanations rather than restating the line.

## Few-shot examples

We use **two** examples by design — a third would burn 1 000+ tokens of context with diminishing returns:

1. **Positive** — `payments.py` with two real bugs (SQL injection + mutable default). The assistant turn shows the model exactly what good JSON output looks like, with proper line ranges, sensible severities, and embedded code fixes.
2. **Negative** — `utils.js` with a trivially correct `add` function. The assistant turn is the literal one-liner `{"summary": "No issues found.", "findings": []}` — teaches the model that zero findings is a valid answer.

## Augmentation block

When static analysers fire, we inject a block into the user message. The wording matters:

> "Lightweight static analysers offer the hints below as a starting point — these do NOT constrain you. Re-classify their severity using your OWN judgement … Independently look for ADDITIONAL bugs … Do not skip an issue just because an analyser already mentioned it — emit your own finding with your assessment."

This wording cost us one iteration:

| Version | Phrasing | Effect |
|---|---|---|
| v1 | "Static analysers already flagged the following. Verify each and add any additional findings." | Model deferred to analysers' severities. SQL injection came back as MEDIUM (bandit's default) instead of CRITICAL. |
| v2 (current) | "...starting point — these do NOT constrain you. Re-classify severity with your OWN judgement. Do not skip an issue just because an analyser already mentioned it." | Model produces its own CRITICAL/HIGH classifications; static findings still surface as separate entries via the merger. |

## Robust JSON extraction

Even with `format="json"` enabled, real outputs contain edge cases. The parser walks this fallback chain:

```mermaid
flowchart TD
    A[Raw LLM output] --> B[json.loads]
    B -->|ok| Z[Return dict]
    B -->|fail| C[Strip BOM + whitespace]
    C --> D[Strip ```json fences```]
    D --> E[Find first balanced {...} block]
    E --> F[Strip trailing commas]
    F --> G[json5.loads — allows trailing commas, single quotes]
    G -->|ok| Z
    G -->|fail| H[ParseError — raw preserved for retry]
```

The retry policy: the engine sees one `ParseError`, lowers temperature to 0.1, and retries once. A second failure logs and skips the file.

## Generation parameters

| Param | Value | Rationale |
|---|---|---|
| `temperature` | 0.2 | Low enough for deterministic JSON; high enough to vary phrasing on retry. |
| `top_p` | 0.9 | Standard nucleus sampling. |
| `num_ctx` | 16 384 | Critical override — Ollama's default 2 048 silently truncates files. |
| `format` | "json" | Constrained-decoding guard. |
| `stream` | false | We need the full JSON before validating. |

## Token budget

For a typical 100-line Python file:

| Section | Tokens |
|---|---|
| System prompt | ~ 450 |
| Few-shot pair 1 (user + assistant) | ~ 380 |
| Few-shot pair 2 (user + assistant) | ~ 40 |
| Augmentation hints (5 analyser findings) | ~ 90 |
| Actual code (100 lines × ~12 tok/line) | ~ 1 200 |
| Total input | ~ 2 160 |
| Reserved for output (set by num_ctx) | up to 14 200 |

Fits comfortably in 16 384, and we chunk above 1 500 source lines as an extra guard.
