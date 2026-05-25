"""Stable JSON serialisation of ReviewResult."""

from __future__ import annotations

import json

from codesentinel.schema import ReviewResult


def to_json(result: ReviewResult | list[ReviewResult], *, indent: int = 2) -> str:
    if isinstance(result, list):
        return json.dumps([r.model_dump(mode="json") for r in result], indent=indent, default=str)
    return result.model_dump_json(indent=indent)
