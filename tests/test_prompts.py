"""Prompt rendering smoke tests."""

from __future__ import annotations

from codesentinel.llm.prompts import (
    FEW_SHOT_ASSISTANT_1,
    SYSTEM_PROMPT,
    build_messages,
    build_user_message,
)


def test_system_prompt_contains_contract():
    assert "JSON object" in SYSTEM_PROMPT
    assert "critical" in SYSTEM_PROMPT
    assert "line_start" in SYSTEM_PROMPT


def test_few_shot_assistant_is_valid_json():
    import json

    parsed = json.loads(FEW_SHOT_ASSISTANT_1)
    assert "summary" in parsed
    assert "findings" in parsed
    assert len(parsed["findings"]) >= 1


def test_build_user_message_numbers_lines():
    msg = build_user_message(code="print('a')\nprint('b')", language="python")
    assert "1  print('a')" in msg
    assert "2  print('b')" in msg
    assert "Python" in msg


def test_build_user_message_with_augmentation():
    msg = build_user_message(
        code="x = 1",
        language="python",
        augmentation=["bandit B608 line 1: hardcoded SQL"],
    )
    assert "bandit B608" in msg
    assert "starting point" in msg.lower() or "starting hints" in msg.lower()


def test_build_messages_has_few_shots():
    messages = build_messages(code="x = 1", language="python")
    roles = [m["role"] for m in messages]
    assert roles[0] == "system"
    # 2 few-shots = 2 user+assistant pairs, then the real user message
    assert roles.count("user") == 3
    assert roles.count("assistant") == 2
