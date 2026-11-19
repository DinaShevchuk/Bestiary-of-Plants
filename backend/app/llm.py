"""OpenAI-compatible chat client used for Ollama and hosted APIs."""
from __future__ import annotations

from typing import Any
import requests

from .config import Settings


class LLMError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if not self.settings.llm_configured:
            raise LLMError("LLM provider is not configured")
        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1200,
        }
        if tools:
            # Auto tool selection is the API default when tools are supplied.
            # We omit tool_choice because some OpenAI-compatible local servers
            # (including Ollama's compatibility layer) do not implement it.
            payload["tools"] = tools
        headers = {"Content-Type": "application/json"}
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"
        endpoint = f"{self.settings.llm_base_url}/chat/completions"
        try:
            response = requests.post(endpoint, json=payload, headers=headers,
                                     timeout=self.settings.llm_timeout_seconds)
        except requests.RequestException as exc:
            raise LLMError("Could not connect to the configured LLM provider") from exc
        if response.status_code >= 400:
            # Do not leak provider response bodies or credentials to the browser.
            raise LLMError(f"LLM provider returned HTTP {response.status_code}")
        try:
            data = response.json()
            message = data["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM provider returned an unexpected response") from exc
        if not isinstance(message, dict):
            raise LLMError("LLM provider returned an invalid message")
        return message
