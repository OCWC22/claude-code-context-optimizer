"""Vercel Sandbox Client - Isolated Python code execution.

This module uses **Vercel's official Python SDK** for Sandbox execution.

Docs / reference (Python SDK beta):
- `from vercel.sandbox import Sandbox`
- `with Sandbox.create(runtime="python3.13") as sandbox: ...`

Authentication (preferred → fallback):
- **Preferred**: `VERCEL_OIDC_TOKEN` (typically set by `vercel env pull` into `.env.local`)
- **Fallback**: `VERCEL_TOKEN` + `VERCEL_TEAM_ID` + `VERCEL_PROJECT_ID`

Important:
- This repo standardizes on **uv** for dependency management.
"""

from __future__ import annotations

import asyncio
import inspect
import math
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any


class SandboxTimeoutError(Exception):
    """Execution exceeded timeout limit."""


class SandboxExecutionError(Exception):
    """Code execution failed."""


class SandboxConnectionError(Exception):
    """Failed to connect to / authenticate with Vercel Sandbox."""


class SandboxStatus(str, Enum):
    """Status of a sandbox execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class SandboxResult:
    """Result of sandbox code execution."""

    status: SandboxStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    execution_time_ms: int = 0
    memory_used_mb: int = 0
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "execution_time_ms": self.execution_time_ms,
            "memory_used_mb": self.memory_used_mb,
            "error_message": self.error_message,
        }


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution.

    Notes:
    - Vercel Sandbox allocates **2048 MB RAM per vCPU** (per docs).
    - We accept `memory_mb` and translate it to a `vcpus` request when supported
      by the installed SDK version.
    """

    timeout: int = 120  # seconds
    memory_mb: int = 512
    runtime: str = "python3.13"

    def validate(self) -> None:
        if self.timeout < 1:
            raise ValueError("Timeout must be at least 1 second")
        # Max runtime is plan-dependent; doc default is 5 minutes, max is 5 hours.
        if self.timeout > 18_000:
            raise ValueError("Timeout cannot exceed 18000 seconds (5 hours)")
        if self.memory_mb < 128:
            raise ValueError("memory_mb must be at least 128")
        if self.memory_mb > 16_384:
            raise ValueError("memory_mb cannot exceed 16384 MB (16GB)")

    def requested_vcpus(self) -> int:
        # 2048 MB per vCPU (docs)
        v = int(math.ceil(self.memory_mb / 2048.0))
        return max(1, min(8, v))


def _configured_for_vercel() -> bool:
    return bool(os.environ.get("VERCEL_OIDC_TOKEN") or os.environ.get("VERCEL_TOKEN") or os.environ.get("VERCEL_API_TOKEN"))


def _maybe_call(obj: Any, name: str, default: Any) -> Any:
    val = getattr(obj, name, None)
    if val is None:
        return default
    try:
        return val() if callable(val) else val
    except Exception:
        return default


class VercelSandboxClient:
    """Thin wrapper around `vercel.sandbox.Sandbox`.

    The Vercel SDK is currently synchronous (per published examples). We provide
    async wrappers by running sync calls in a thread.
    """

    def __init__(
        self,
        api_token: str | None = None,
        team_id: str | None = None,
        project_id: str | None = None,
    ):
        # Keep backwards compatibility with earlier env var naming.
        self.token = api_token or os.environ.get("VERCEL_TOKEN") or os.environ.get("VERCEL_API_TOKEN") or ""
        self.team_id = team_id or os.environ.get("VERCEL_TEAM_ID") or ""
        self.project_id = project_id or os.environ.get("VERCEL_PROJECT_ID") or ""

        if not _configured_for_vercel():
            raise SandboxConnectionError(
                "Vercel Sandbox not configured. Set VERCEL_OIDC_TOKEN (preferred) or VERCEL_TOKEN (and team/project IDs if required)."
            )

    async def __aenter__(self) -> "VercelSandboxClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def close(self) -> None:
        return None

    def _build_create_kwargs(self, *, config: SandboxConfig) -> dict[str, Any]:
        """Build kwargs for `Sandbox.create()` in a version-tolerant way."""
        try:
            from vercel.sandbox import Sandbox  # type: ignore
        except Exception as e:
            raise SandboxConnectionError(
                "Vercel Sandbox SDK not installed. Install with: uv add vercel"
            ) from e

        sig = inspect.signature(Sandbox.create)
        kwargs: dict[str, Any] = {}

        # Runtime
        if "runtime" in sig.parameters:
            kwargs["runtime"] = config.runtime

        # Resources (optional)
        if "resources" in sig.parameters:
            kwargs["resources"] = {"vcpus": config.requested_vcpus()}

        # Access-token auth (optional). If OIDC token is present, the SDK should auto-auth.
        # We only pass these if the installed SDK exposes them.
        if self.team_id and "team_id" in sig.parameters:
            kwargs["team_id"] = self.team_id
        if self.project_id and "project_id" in sig.parameters:
            kwargs["project_id"] = self.project_id
        if self.token and "token" in sig.parameters:
            kwargs["token"] = self.token

        return kwargs

    def _execute_sync(self, code: str, config: SandboxConfig) -> SandboxResult:
        try:
            from vercel.sandbox import Sandbox  # type: ignore
        except Exception as e:
            raise SandboxConnectionError("Vercel Sandbox SDK not installed. Install with: uv add vercel") from e

        config.validate()
        create_kwargs = self._build_create_kwargs(config=config)

        try:
            with Sandbox.create(**create_kwargs) as sandbox:  # type: ignore[arg-type]
                cmd = sandbox.run_command("python", ["-c", code])
                stdout = str(_maybe_call(cmd, "stdout", ""))
                stderr = str(_maybe_call(cmd, "stderr", ""))

                exit_code = _maybe_call(cmd, "exit_code", None)
                if exit_code is None:
                    exit_code = _maybe_call(cmd, "exitCode", None)

                status = SandboxStatus.COMPLETED
                if isinstance(exit_code, int) and exit_code != 0:
                    status = SandboxStatus.FAILED

                return SandboxResult(
                    status=status,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code if isinstance(exit_code, int) else None,
                    error_message="" if status == SandboxStatus.COMPLETED else "nonzero_exit",
                )

        except Exception as e:
            return SandboxResult(status=SandboxStatus.FAILED, error_message=f"{type(e).__name__}: {e}")

    async def execute(self, code: str, config: SandboxConfig | None = None) -> SandboxResult:
        cfg = config or SandboxConfig()
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._execute_sync, code, cfg),
                timeout=cfg.timeout + 5,
            )
        except asyncio.TimeoutError:
            return SandboxResult(status=SandboxStatus.TIMEOUT, error_message="timeout")

    async def health_check(self) -> dict[str, Any]:
        """Best-effort health check.

        This does not call the REST API directly; it just verifies that:
        - env vars are present
        - the `vercel` python package is importable
        """
        try:
            from vercel.sandbox import Sandbox  # noqa: F401
        except Exception as e:
            return {"status": "unavailable", "error": f"{type(e).__name__}: {e}"}

        return {
            "status": "configured" if _configured_for_vercel() else "missing_env",
            "auth": "oidc" if os.environ.get("VERCEL_OIDC_TOKEN") else "token",
            "team_id": bool(os.environ.get("VERCEL_TEAM_ID")),
            "project_id": bool(os.environ.get("VERCEL_PROJECT_ID")),
        }


async def execute_code(code: str, *, timeout: int = 120, memory_mb: int = 512) -> SandboxResult:
    async with VercelSandboxClient() as client:
        return await client.execute(code, config=SandboxConfig(timeout=timeout, memory_mb=memory_mb))


def execute_code_sync(code: str, *, timeout: int = 120, memory_mb: int = 512) -> SandboxResult:
    return asyncio.run(execute_code(code, timeout=timeout, memory_mb=memory_mb))
