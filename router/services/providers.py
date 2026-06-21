"""Provider clients. Both speak the OpenAI chat-completions shape.

httpx is imported lazily so the routing engine and tests import with no third-party
deps and burn no credit.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ..core.models import ModelSpec


@dataclass
class Completion:
    text: str
    tokens_in: int
    tokens_out: int


class InferenceProvider:
    """The shared multi-model endpoint (OpenAI-compatible)."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or os.getenv("INFERENCE_API_KEY", "")
        self.base_url = (base_url or os.getenv(
            "INFERENCE_BASE_URL", "https://model.service-inference.ai/v1"
        )).rstrip("/")

    def complete(self, model_id: str, messages: list[dict], max_tokens: int = 1024) -> Completion:
        import httpx

        if not self.api_key:
            raise RuntimeError("INFERENCE_API_KEY is not set")
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": model_id, "messages": messages, "max_tokens": max_tokens},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return Completion(text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


class OpenRouterProvider:
    """OpenRouter — activates only when OPENROUTER_API_KEY is set."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def complete(self, model_id: str, messages: list[dict], max_tokens: int = 1024) -> Completion:
        import httpx

        if not self.enabled:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": model_id, "messages": messages, "max_tokens": max_tokens},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return Completion(text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


def get_provider(spec: ModelSpec):
    if spec.provider == "openrouter":
        return OpenRouterProvider()
    return InferenceProvider()
