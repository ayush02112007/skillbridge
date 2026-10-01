"""LLM provider abstraction.

The platform is fully functional with **no** LLM configured: every AI feature has
a deterministic implementation that runs locally. When ``AI_PROVIDER`` and
``AI_API_KEY`` are set, the provider is used to make explanations more fluent -
never to make a decision, and never as the sole source of a number.
"""
from __future__ import annotations

import abc
import json
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("ai.provider")


class AIProvider(abc.ABC):
    """Minimal text-completion contract."""

    name: str = "base"
    #: When False, callers skip the provider and use their deterministic path.
    available: bool = False

    @abc.abstractmethod
    async def complete(
        self, prompt: str, *, system: str = "", max_tokens: int = 600,
        temperature: float = 0.2,
    ) -> str | None:
        """Return generated text, or ``None`` if generation was not possible."""

    async def complete_json(
        self, prompt: str, *, system: str = "", max_tokens: int = 900
    ) -> dict[str, Any] | None:
        raw = await self.complete(
            prompt
            + "\n\nRespond with a single valid JSON object and nothing else.",
            system=system, max_tokens=max_tokens, temperature=0.0,
        )
        if not raw:
            return None
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            text = text[4:] if text.startswith("json") else text
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            log.warning("ai.json_parse_failed", provider=self.name)
            return None


class DeterministicProvider(AIProvider):
    """Default. Generates nothing; every caller falls back to rule-based text.

    This is not a stub - it is the guarantee that SkillBridge works with zero
    external dependencies and zero per-request cost.
    """

    name = "deterministic"
    available = False

    async def complete(self, prompt: str, **_: Any) -> str | None:
        return None


class MockProvider(AIProvider):
    """Deterministic echo provider used by tests that exercise the LLM path."""

    name = "mock"
    available = True

    def __init__(self, canned: dict[str, str] | None = None) -> None:
        self.canned = canned or {}
        self.calls: list[str] = []

    async def complete(self, prompt: str, **_: Any) -> str | None:
        self.calls.append(prompt)
        for key, value in self.canned.items():
            if key in prompt:
                return value
        return "MOCK_RESPONSE"


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self) -> None:
        self.available = bool(settings.AI_API_KEY)
        self.model = settings.AI_MODEL or "gpt-4o-mini"
        self.base_url = settings.AI_BASE_URL or "https://api.openai.com/v1"

    async def complete(
        self, prompt: str, *, system: str = "", max_tokens: int = 600,
        temperature: float = 0.2,
    ) -> str | None:
        if not self.available:
            return None
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        try:
            async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
                    json={
                        "model": self.model, "messages": messages,
                        "max_tokens": max_tokens, "temperature": temperature,
                    },
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # pragma: no cover - network dependent
            log.warning("ai.completion_failed", provider=self.name, error=str(exc)[:200])
            return None


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self) -> None:
        self.available = bool(settings.AI_API_KEY)
        self.model = settings.AI_MODEL or "claude-sonnet-5"
        self.base_url = settings.AI_BASE_URL or "https://api.anthropic.com/v1"

    async def complete(
        self, prompt: str, *, system: str = "", max_tokens: int = 600,
        temperature: float = 0.2,
    ) -> str | None:
        if not self.available:
            return None
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        try:
            async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": settings.AI_API_KEY,
                        "anthropic-version": "2023-06-01",
                    },
                    json=payload,
                )
                response.raise_for_status()
                blocks = response.json().get("content", [])
                return "".join(b.get("text", "") for b in blocks) or None
        except Exception as exc:  # pragma: no cover - network dependent
            log.warning("ai.completion_failed", provider=self.name, error=str(exc)[:200])
            return None


class LocalModelProvider(AIProvider):
    """Any OpenAI-compatible local server (Ollama, vLLM, LM Studio, ...)."""

    name = "local"

    def __init__(self) -> None:
        self.base_url = settings.AI_BASE_URL or "http://localhost:11434/v1"
        self.model = settings.AI_MODEL or "llama3.1"
        self.available = bool(settings.AI_BASE_URL or settings.AI_MODEL)

    async def complete(
        self, prompt: str, *, system: str = "", max_tokens: int = 600,
        temperature: float = 0.2,
    ) -> str | None:
        if not self.available:
            return None
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        try:
            async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model, "messages": messages,
                        "max_tokens": max_tokens, "temperature": temperature,
                    },
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # pragma: no cover - network dependent
            log.warning("ai.completion_failed", provider=self.name, error=str(exc)[:200])
            return None


_REGISTRY: dict[str, type[AIProvider]] = {
    "deterministic": DeterministicProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "local": LocalModelProvider,
    "mock": MockProvider,
}

_instance: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    global _instance
    if _instance is None:
        provider_cls = _REGISTRY.get(settings.AI_PROVIDER, DeterministicProvider)
        _instance = provider_cls()
        log.info(
            "ai.provider_selected",
            provider=_instance.name, available=_instance.available,
        )
    return _instance


def set_ai_provider(provider: AIProvider | None) -> None:
    """Test hook for injecting a provider."""
    global _instance
    _instance = provider
