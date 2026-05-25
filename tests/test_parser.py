"""LLM output parsing — these are real-world ugly outputs."""

from __future__ import annotations

import pytest

from codesentinel.llm.parser import ParseError, extract_json


def test_clean_json():
    raw = '{"summary": "ok", "findings": []}'
    obj = extract_json(raw)
    assert obj["summary"] == "ok"


def test_json_with_leading_prose():
    raw = "Here is the review:\n{\"summary\": \"ok\", \"findings\": []}"
    obj = extract_json(raw)
    assert obj == {"summary": "ok", "findings": []}


def test_json_with_trailing_prose():
    raw = '{"summary": "ok", "findings": []}\n\nHope this helps!'
    obj = extract_json(raw)
    assert obj["summary"] == "ok"


def test_json_with_markdown_fences():
    raw = '```json\n{"summary": "fenced", "findings": []}\n```'
    obj = extract_json(raw)
    assert obj["summary"] == "fenced"


def test_json_with_plain_fences():
    raw = '```\n{"summary": "plain", "findings": []}\n```'
    obj = extract_json(raw)
    assert obj["summary"] == "plain"


def test_json_with_trailing_comma():
    raw = '{"summary": "tc", "findings": [],}'
    obj = extract_json(raw)
    assert obj["summary"] == "tc"
    assert obj["findings"] == []


def test_json_with_nested_braces_in_string():
    raw = '{"summary": "x{y}z", "findings": [{"line_start": 1, "line_end": 1, "severity": "low", "category": "style", "title": "t", "description": "d"}]}'
    obj = extract_json(raw)
    assert obj["summary"] == "x{y}z"
    assert obj["findings"][0]["title"] == "t"


def test_json_with_escaped_quotes():
    raw = r'{"summary": "She said \"hi\"", "findings": []}'
    obj = extract_json(raw)
    assert obj["summary"] == 'She said "hi"'


def test_json_with_bom():
    raw = '﻿{"summary": "bom", "findings": []}'
    obj = extract_json(raw)
    assert obj["summary"] == "bom"


def test_json5_unquoted_keys():
    raw = "{summary: 'json5', findings: []}"
    obj = extract_json(raw)
    assert obj["summary"] == "json5"


def test_completely_garbled_raises():
    with pytest.raises(ParseError):
        extract_json("this is not JSON at all, just prose")


def test_empty_raises():
    with pytest.raises(ParseError):
        extract_json("")


def test_whitespace_only_raises():
    with pytest.raises(ParseError):
        extract_json("   \n\t  ")
