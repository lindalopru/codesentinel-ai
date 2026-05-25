"""Thin Ollama HTTP wrapper tuned for structured-JSON code review.

Why a hand-rolled wrapper instead of the `ollama` Python lib:
- We need to force `format="json"` AND `num_ctx=16384` on every request
  (the lib's default num_ctx is 2048 which silently truncates large files).
- We need a deterministic single-retry loop on bad JSON.
- We want clean async support so the engine can run a small pool concurrently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from codesentinel.config import Settings, get_settings
from codesentinel.llm.parser import ParseError, extract_json
from codesentinel.llm.prompts import build_messages
from codesentinel.utils.logging import get_logger

log = get_logger("codesentinel.llm")


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResponse:
    payload: dict[str, Any]
    raw: str
    model: str
    duration_s: float


class OllamaClient:
    """Synchronous + async wrapper around the Ollama /api/chat endpoint."""

    def __init__(self, settings: Settings | None = None, *, model: str | None = None):
        self.settings = settings or get_settings()
        self.model = model or self.settings.ollama_model
        self._timeout = httpx.Timeout(self.settings.ollama_timeout, connect=10.0)

    # ---------- sync ----------

    def review(
        self,
        *,
        code: str,
        language: str,
        filename: str = "snippet",
        augmentation: list[str] | None = None,
    ) -> LLMResponse:
        messages = build_messages(
            code=code, language=language, filename=filename, augmentation=augmentation
        )
        return self._chat_with_retry(messages)

    def _chat_with_retry(self, messages: list[dict[str, str]]) -> LLMResponse:
        try:
            return self._chat(messages, temperature=self.settings.ollama_temperature)
        except (ParseError, LLMError) as first:
            log.warning("First LLM call failed (%s) — retrying at lower temperature", first.__class__.__name__)
            try:
                return self._chat(messages, temperature=0.1)
            except (ParseError, LLMError) as second:
                raise LLMError(f"LLM call failed twice: {first} / {second}") from second

    def _chat(self, messages: list[dict[str, str]], *, temperature: float) -> LLMResponse:
        url = f"{self.settings.ollama_host}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "num_ctx": self.settings.ollama_num_ctx,
                "temperature": temperature,
                "top_p": self.settings.ollama_top_p,
            },
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise LLMError(f"HTTP error talking to Ollama: {exc}") from exc

        if r.status_code != 200:
            raise LLMError(f"Ollama returned {r.status_code}: {r.text[:300]}")

        data = r.json()
        raw_content = (data.get("message") or {}).get("content", "")
        if not raw_content:
            raise LLMError("Ollama returned an empty message")

        return LLMResponse(
            payload=extract_json(raw_content),
            raw=raw_content,
            model=self.model,
            duration_s=(data.get("total_duration", 0) / 1e9) or 0.0,
        )

    # ---------- async ----------

    async def areview(
        self,
        *,
        code: str,
        language: str,
        filename: str = "snippet",
        augmentation: list[str] | None = None,
    ) -> LLMResponse:
        messages = build_messages(
            code=code, language=language, filename=filename, augmentation=augmentation
        )
        try:
            return await self._achat(messages, temperature=self.settings.ollama_temperature)
        except (ParseError, LLMError) as first:
            log.warning("First async LLM call failed (%s) — retrying at lower temperature", first.__class__.__name__)
            try:
                return await self._achat(messages, temperature=0.1)
            except (ParseError, LLMError) as second:
                raise LLMError(f"LLM call failed twice: {first} / {second}") from second

    async def _achat(self, messages: list[dict[str, str]], *, temperature: float) -> LLMResponse:
        url = f"{self.settings.ollama_host}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "num_ctx": self.settings.ollama_num_ctx,
                "temperature": temperature,
                "top_p": self.settings.ollama_top_p,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise LLMError(f"HTTP error talking to Ollama: {exc}") from exc

        if r.status_code != 200:
            raise LLMError(f"Ollama returned {r.status_code}: {r.text[:300]}")

        data = r.json()
        raw_content = (data.get("message") or {}).get("content", "")
        if not raw_content:
            raise LLMError("Ollama returned an empty message")

        return LLMResponse(
            payload=extract_json(raw_content),
            raw=raw_content,
            model=self.model,
            duration_s=(data.get("total_duration", 0) / 1e9) or 0.0,
        )

    # ---------- introspection ----------

    def list_models(self) -> list[str]:
        url = f"{self.settings.ollama_host}/api/tags"
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url)
            if r.status_code != 200:
                return []
            return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
        except httpx.HTTPError:
            return []
