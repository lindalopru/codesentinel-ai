"""OllamaClient tests with respx HTTP mocking."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from codesentinel.llm.client import LLMError, OllamaClient


@pytest.fixture
def client() -> OllamaClient:
    return OllamaClient()


@respx.mock
def test_review_success(client: OllamaClient, ok_payload: dict):
    respx.post("http://127.0.0.1:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"content": json.dumps(ok_payload)}, "total_duration": 1_000_000_000},
        )
    )
    resp = client.review(code="x = 1", language="python")
    assert resp.payload == ok_payload
    assert resp.duration_s > 0


@respx.mock
def test_review_retries_on_bad_json(client: OllamaClient, ok_payload: dict):
    # First response = garbled, second = valid JSON
    respx.post("http://127.0.0.1:11434/api/chat").mock(
        side_effect=[
            httpx.Response(200, json={"message": {"content": "garbled prose with no JSON"}}),
            httpx.Response(200, json={"message": {"content": json.dumps(ok_payload)}}),
        ]
    )
    resp = client.review(code="x = 1", language="python")
    assert resp.payload == ok_payload


@respx.mock
def test_review_raises_after_two_failures(client: OllamaClient):
    respx.post("http://127.0.0.1:11434/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"content": "still garbled"}})
    )
    with pytest.raises(LLMError):
        client.review(code="x = 1", language="python")


@respx.mock
def test_review_handles_http_error(client: OllamaClient):
    respx.post("http://127.0.0.1:11434/api/chat").mock(return_value=httpx.Response(500, text="boom"))
    with pytest.raises(LLMError):
        client.review(code="x = 1", language="python")


@respx.mock
def test_list_models(client: OllamaClient):
    respx.get("http://127.0.0.1:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "qwen2.5-coder:7b"}, {"name": "llama3.2"}]})
    )
    tags = client.list_models()
    assert "qwen2.5-coder:7b" in tags
    assert "llama3.2" in tags
