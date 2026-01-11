from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from .utils import now_ns


@dataclass(frozen=True)
class GalileoLogResult:
    ok: bool
    status_code: int | None = None
    response_json: dict[str, Any] | None = None
    error: str | None = None


class GalileoObserveClient:
    """Lightweight Galileo Observe logger.

    We keep this intentionally minimal and resilient:
    - If GALILEO_API_KEY is missing, it becomes a no-op.
    - If the endpoint is misconfigured, we capture the error and continue.

    Env vars:
      - GALILEO_API_KEY
      - GALILEO_API_URL (default: https://api.galileo.ai/v1)
      - GALILEO_PROJECT_NAME (default: continuous-claude-v3-evals)
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        project_name: str | None = None,
        timeout_s: float = 30.0,
    ):
        self.api_key = api_key or os.environ.get("GALILEO_API_KEY")
        self.api_url = (api_url or os.environ.get("GALILEO_API_URL") or "https://api.galileo.ai/v1").rstrip(
            "/"
        )
        self.project_name = project_name or os.environ.get("GALILEO_PROJECT_NAME") or "continuous-claude-v3-evals"
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

    async def log_workflow(
        self,
        *,
        name: str,
        input_text: str,
        output_text: str,
        metadata: dict[str, Any] | None = None,
        steps: list[dict[str, Any]] | None = None,
        duration_ns: int | None = None,
        status_code: int = 200,
    ) -> GalileoLogResult:
        if not self.api_key:
            return GalileoLogResult(ok=False, error="GALILEO_API_KEY not set (skipped)")

        client = await self._get_client()
        created_at_ns = now_ns()
        duration_ns = duration_ns or 0

        body = {
            "project_name": self.project_name,
            "workflows": [
                {
                    "type": "workflow",
                    "name": name,
                    "input": input_text,
                    "output": output_text,
                    "created_at_ns": created_at_ns,
                    "duration_ns": duration_ns,
                    "metadata": metadata or {},
                    "status_code": status_code,
                    "steps": steps or [],
                }
            ],
        }

        try:
            resp = await client.post(
                f"{self.api_url}/observe/workflows",
                headers={
                    "Content-Type": "application/json",
                    "Galileo-API-Key": self.api_key,
                },
                json=body,
            )
            return GalileoLogResult(ok=resp.status_code < 300, status_code=resp.status_code, response_json=resp.json())
        except Exception as e:
            return GalileoLogResult(ok=False, error=f"{type(e).__name__}: {e}")

