"""Robust JSON extraction from LLM output.

Real-world LLM outputs (even with format="json") can contain:
- Leading / trailing prose ("Here is the review: ...")
- Markdown code fences (```json ... ```)
- Trailing commas before } and ]
- Single quotes instead of double quotes
- A leading BOM or stray whitespace

This module's `extract_json` walks a fallback chain so the engine never crashes
on a single bad model output.
"""

from __future__ import annotations

import json
import re
from typing import Any

import json5


class ParseError(ValueError):
    """Raised when no recovery strategy could parse the LLM output."""

    def __init__(self, raw: str, attempts: list[str]):
        super().__init__(f"Could not parse LLM output. Tried: {attempts}")
        self.raw = raw
        self.attempts = attempts


_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def _strip_fences(text: str) -> str:
    match = _FENCE_RE.search(text)
    return match.group(1).strip() if match else text


def _find_balanced_object(text: str) -> str | None:
    """Return the first balanced {...} JSON object, respecting string literals."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_json(raw: str) -> dict[str, Any]:
    """Walk a fallback chain to extract a dict from a noisy LLM string.

    Order:
      1. Direct json.loads
      2. Strip whitespace + BOM, retry
      3. Strip markdown fences, retry
      4. Slice first balanced {...} block, retry
      5. Strip trailing commas, retry
      6. json5.loads (allows trailing commas, single quotes, unquoted keys)
    """
    if not raw or not raw.strip():
        raise ParseError(raw, ["empty"])

    attempts: list[str] = []
    candidates: list[str] = [raw]

    # 1 — raw
    attempts.append("raw")
    cleaned = raw.strip().lstrip("﻿")
    if cleaned != raw:
        candidates.append(cleaned)
        attempts.append("trimmed")

    # 2 — fences
    no_fence = _strip_fences(cleaned)
    if no_fence != cleaned:
        candidates.append(no_fence)
        attempts.append("defenced")

    # 3 — balanced object slice
    sliced = _find_balanced_object(no_fence)
    if sliced is not None:
        candidates.append(sliced)
        attempts.append("balanced")

    # 4 — trailing-comma cleanup applied to the best candidate so far
    for base in list(candidates):
        without_trailing = _TRAILING_COMMA_RE.sub(r"\1", base)
        if without_trailing != base:
            candidates.append(without_trailing)
            attempts.append("no-trailing-commas")

    # Try strict JSON on each candidate, then permissive json5.
    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue

    for cand in candidates:
        try:
            obj = json5.loads(cand)
            if isinstance(obj, dict):
                attempts.append("json5")
                return obj
        except Exception:  # noqa: BLE001 — json5 raises many things
            continue

    raise ParseError(raw, attempts)
