"""Vercel Sandbox integration for isolated code execution.

This package provides a client for Vercel's Firecracker microVM-based
code execution, used in CCv3 for running AI-generated code safely.

Example:
    from sandbox import VercelSandboxClient, SandboxConfig

    async with VercelSandboxClient() as client:
        result = await client.execute(
            code="print('Hello from sandbox!')",
            config=SandboxConfig(timeout=30)
        )
        print(result.stdout)
"""

from sandbox.vercel_sandbox import (
    SandboxConfig,
    SandboxConnectionError,
    SandboxExecutionError,
    SandboxResult,
    SandboxStatus,
    SandboxTimeoutError,
    VercelSandboxClient,
    execute_code,
    execute_code_sync,
)

__all__ = [
    "VercelSandboxClient",
    "SandboxConfig",
    "SandboxResult",
    "SandboxStatus",
    "SandboxTimeoutError",
    "SandboxExecutionError",
    "SandboxConnectionError",
    "execute_code",
    "execute_code_sync",
]
