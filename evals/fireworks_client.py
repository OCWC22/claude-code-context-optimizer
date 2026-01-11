from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class FireworksUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class FireworksChatResult:
    content: str
    model: str
    usage: FireworksUsage
    latency_ms: float
    raw: dict[str, Any]


class FireworksChatClient:
    """Minimal OpenAI-compatible chat client for Fireworks.

    Sponsor requirement: use MiniMax M2 via Fireworks.
    Default model is configured for cost: accounts/fireworks/models/minimax-m2p1
    """

    API_URL = "https://api.fireworks.ai/inference/v1/chat/completions"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: float = 120.0,
    ):
        self.api_key = api_key or os.environ.get("FIREWORKS_API_KEY")
        self.model = model or os.environ.get("FIREWORKS_MODEL") or "accounts/fireworks/models/minimax-m2p1"
        self.timeout_s = timeout_s
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_s)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 800,
        model: str | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> FireworksChatResult:
        if not self.api_key:
            raise ValueError("FIREWORKS_API_KEY is required")

        selected_model = model or self.model
        client = await self._get_client()

        payload: dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if extra_body:
            payload.update(extra_body)

        start = time.perf_counter()
        resp = await client.post(
            self.API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        latency_ms = (time.perf_counter() - start) * 1000
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        content = (choice.get("message") or {}).get("content") or ""

        usage_obj = data.get("usage") or {}
        usage = FireworksUsage(
            prompt_tokens=int(usage_obj.get("prompt_tokens") or 0),
            completion_tokens=int(usage_obj.get("completion_tokens") or 0),
            total_tokens=int(usage_obj.get("total_tokens") or 0),
        )

        return FireworksChatResult(
            content=content,
            model=selected_model,
            usage=usage,
            latency_ms=latency_ms,
            raw=data,
        )

