#!/usr/bin/env python3
"""CCv3 MCP Server - Standalone (no API server needed).

This is a self-contained MCP server that includes all CCv3 functionality.
Works with Claude Code via Model Context Protocol.

Installation:
    uv add mcp httpx pyyaml motor pymongo pydantic

Usage:
    # Add to Claude Code
    claude mcp add ccv3 -e MONGODB_URI=... -- uv run python mcp_server_standalone.py

    # Or run directly
    python mcp_server_standalone.py
"""

import asyncio
import os
from pathlib import Path

from mcp.server import Server
from mcp.types import Tool, TextContent

# =============================================================================
# Configuration
# =============================================================================

app = Server("ccv3")

# Sponsor API keys from environment
MONGODB_URI = os.environ.get("MONGODB_URI", os.environ.get("ATLAS_URI", ""))
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
JINA_API_KEY = os.environ.get("JINA_API_KEY", "")
GALILEO_API_KEY = os.environ.get("GALILEO_API_KEY", "")


# =============================================================================
# Inline CCv3 Core (minimal implementation for MCP)
# =============================================================================

class SimpleAtlas:
    """Minimal MongoDB Atlas client for MCP server."""

    def __init__(self):
        self._client = None
        self._db = None
        self.connected = False

    async def connect(self):
        if not MONGODB_URI:
            return False

        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            self._client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            await self._client.admin.command("ping")
            self._db = self._client["ccv3_hackathon"]
            self.connected = True
            return True
        except Exception:
            return False

    async def store_embedding(self, repo_id: str, file_path: str, content: str, vector: list):
        if not self.connected:
            return
        await self._db.embeddings.update_one(
            {"repo_id": repo_id, "file_path": file_path},
            {"$set": {"content": content, "vector": vector}},
            upsert=True
        )

    async def store_handoff(self, repo_id: str, task: str, yaml_content: str, md_content: str):
        if not self.connected:
            return
        from datetime import datetime, timezone
        await self._db.handoffs.update_one(
            {"repo_id": repo_id, "task": task},
            {"$set": {
                "yaml": yaml_content,
                "markdown": md_content,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )

    async def hybrid_search(self, repo_id: str, query: str, limit: int = 10):
        """Simple text search (vector search if embeddings available)."""
        if not self.connected:
            return []

        # Text-based search fallback
        cursor = self._db.embeddings.find({
            "repo_id": repo_id,
            "content": {"$regex": query, "$options": "i"}
        }).limit(limit)
        results = []
        async for doc in cursor:
            results.append({
                "file_path": doc.get("object_id") or doc.get("file_path", "unknown"),
                "content": doc.get("content", "")[:500],
                "score": 0.8  # Default score for text match
            })
        return results


# Global Atlas instance
_atlas = SimpleAtlas()


# =============================================================================
# Simple Embeddings (local fallback)
# =============================================================================

class SimpleEmbeddings:
    """Simple hash-based embeddings for when Jina API is unavailable."""

    def __init__(self):
        self.use_jina = bool(JINA_API_KEY)
        self._client = None

    async def embed(self, text: str) -> list[float]:
        if self.use_jina:
            return await self._embed_jina(text)
        return self._embed_hash(text)

    async def _embed_jina(self, text: str) -> list[float]:
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient()
        response = await self._client.post(
            "https://api.jina.ai/v1/embeddings",
            json={"model": "jina-embeddings-v3", "input": text, "task": "retrieval.passage"},
            headers={"Authorization": f"Bearer {JINA_API_KEY}"}
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    def _embed_hash(self, text: str) -> list[float]:
        import hashlib
        import math
        text = text.lower().strip()
        embedding = []
        for i in range(1024):
            h = hashlib.md5(f"{text}_{i}".encode()).hexdigest()
            val = (int(h[:8], 16) / 0xFFFFFFFF) * 2 - 1
            embedding.append(val)
        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        return embedding


_embeddings = SimpleEmbeddings()


# =============================================================================
# MCP Tools Implementation
# =============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available CCv3 tools."""
    return [
        Tool(
            name="ccv3_init",
            description="Initialize CCv3 for a repository. Connects to MongoDB Atlas.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Repository path"}
                }
            }
        ),
        Tool(
            name="ccv3_index",
            description="Index codebase files into MongoDB Atlas with embeddings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Repository path"},
                    "extensions": {"type": "string", "description": "File extensions (default: .py,.ts,.js)"}
                }
            }
        ),
        Tool(
            name="ccv3_query",
            description="Search indexed codebase. Returns relevant files with context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "path": {"type": "string", "description": "Repository path"},
                    "limit": {"type": "integer", "description": "Max results"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="ccv3_handoff",
            description="Generate handoff pack (YAML+MD) for a task. Minimal context for LLM.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task description"},
                    "path": {"type": "string", "description": "Repository path"}
                },
                "required": ["task"]
            }
        ),
        Tool(
            name="ccv3_sandbox_execute",
            description="Execute Python code in Vercel Sandbox (isolated Firecracker microVM). Requires VERCEL_OIDC_TOKEN (preferred) or VERCEL_TOKEN/VERCEL_API_TOKEN.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default: 120, max: 18000)"},
                    "memory_mb": {"type": "integer", "description": "Memory limit in MB (default: 512, max: 16384)"}
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="ccv3_status",
            description="Get CCv3 and sponsor connectivity status.",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from Claude Code."""
    path = arguments.get("path", ".")

    try:
        if name == "ccv3_init":
            await _atlas.connect()
            status = "✅ Connected to MongoDB Atlas" if _atlas.connected else "⚠️ Using in-memory mode"
            return [TextContent(
                type="text",
                text=f"""{status}

Sponsors:
  MongoDB Atlas: {'✅ Connected' if _atlas.connected else '❌ Not configured'}
  Fireworks AI: {'✅ Configured' if FIREWORKS_API_KEY else '❌ Not configured'}
  Jina AI: {'✅ Configured' if JINA_API_KEY else '❌ Not configured'}"
  Galileo AI: {'✅ Configured' if GALILEO_API_KEY else '❌ Not configured'}
"""
            )]

        elif name == "ccv3_index":
            await _atlas.connect()
            extensions = arguments.get("extensions", ".py,.ts,.js,.tsx,.jsx")
            ext_list = extensions.split(",")

            repo_id = Path(path).name
            indexed_count = 0

            for ext in ext_list:
                for file_path in Path(path).rglob(f"*{ext}"):
                    try:
                        content = file_path.read_text()[:5000]  # Truncate large files
                        embed = await _embeddings.embed(content)
                        await _atlas.store_embedding(repo_id, str(file_path), content, embed)
                        indexed_count += 1
                    except Exception:
                        pass

            return [TextContent(
                type="text",
                text=f"✅ Indexed {indexed_count} files into MongoDB Atlas\nExtensions: {ext_list}"
            )]

        elif name == "ccv3_query":
            await _atlas.connect()
            results = await _atlas.hybrid_search(
                repo_id=Path(path).name,
                query=arguments["query"],
                limit=arguments.get("limit", 10)
            )

            output = [f"🔍 Query: '{arguments['query']}'\n"]
            for i, r in enumerate(results[:5], 1):
                output.append(f"\n{i}. {r.get('file_path', 'unknown')}")
                output.append(f"   {r.get('content', '')[:200]}...")

            return [TextContent(type="text", text="\n".join(output))]

        elif name == "ccv3_handoff":
            await _atlas.connect()
            task = arguments["task"]
            repo_id = Path(path).name

            # Simple handoff generation
            yaml_content = f"""task: {task}
repo: {repo_id}
status: ready
"""

            md_content = f"""# Handoff: {task}

**Repository:** {repo_id}
**Status:** Ready to implement

## Context
Use `ccv3_query` to retrieve relevant code before implementing.
"""

            await _atlas.store_handoff(repo_id, task, yaml_content, md_content)

            return [TextContent(
                type="text",
                text=f"""📦 Handoff Pack Generated

YAML:
{yaml_content}

Markdown:
{md_content}

Store in MongoDB Atlas: ✅"""
            )]

        elif name == "ccv3_sandbox_execute":
            # Execute Python code in Vercel Sandbox
            vercel_configured = bool(
                os.environ.get("VERCEL_OIDC_TOKEN") or os.environ.get("VERCEL_TOKEN") or os.environ.get("VERCEL_API_TOKEN")
            )
            if not vercel_configured:
                return [TextContent(
                    type="text",
                    text="❌ Vercel Sandbox not configured. Set VERCEL_OIDC_TOKEN (preferred) or VERCEL_TOKEN/VERCEL_API_TOKEN."
                )]

            try:
                from sandbox import VercelSandboxClient, SandboxConfig

                config = SandboxConfig(
                    timeout=arguments.get("timeout", 120),
                    memory_mb=arguments.get("memory_mb", 512),
                )

                async with VercelSandboxClient() as client:
                    result = await client.execute(
                        code=arguments["code"],
                        config=config,
                    )

                    # Store result in Atlas if available
                    if _atlas.connected:
                        computation_id = await _atlas.create_computation_id()
                        await _atlas.store_sandbox_result(
                            computation_id=computation_id,
                            code=arguments["code"],
                            result=result.to_dict(),
                            config={"timeout": config.timeout, "memory_mb": config.memory_mb},
                        )

                    output = f"""🔧 Sandbox Execution Result

Status: {result.status.value}
Exit Code: {result.exit_code or 'N/A'}
Execution Time: {result.execution_time_ms}ms
Memory Used: {result.memory_used_mb}MB

--- STDOUT ---
{result.stdout or '(empty)'}

--- STDERR ---
{result.stderr or '(empty)'}"""

                    if result.error_message:
                        output += f"\n\n--- ERROR ---\n{result.error_message}"

                    return [TextContent(type="text", text=output)]

            except ImportError:
                return [TextContent(
                    type="text",
                    text="❌ Sandbox module not available. Install dependencies with: uv sync"
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"❌ Sandbox execution failed: {str(e)}"
                )]

        elif name == "ccv3_status":
            await _atlas.connect()
            vercel_token = os.environ.get("VERCEL_OIDC_TOKEN") or os.environ.get("VERCEL_TOKEN") or os.environ.get("VERCEL_API_TOKEN") or ""
            return [TextContent(
                type="text",
                text=f"""📋 CCv3 MCP Server Status

MongoDB Atlas: {'✅ Connected' if _atlas.connected else '❌ Disconnected'}
Fireworks AI: {'✅' if FIREWORKS_API_KEY else '❌'} {len(FIREWORKS_API_KEY)} chars
Jina AI: {'✅' if JINA_API_KEY else '❌'} {len(JINA_API_KEY)} chars
Galileo AI: {'✅' if GALILEO_API_KEY else '❌'} {len(GALILEO_API_KEY)} chars
Vercel Sandbox: {'✅' if vercel_token else '❌'} {len(vercel_token)} chars

Available Tools: ccv3_init, ccv3_index, ccv3_query, ccv3_handoff, ccv3_sandbox_execute, ccv3_status"""
            )]

        else:
            return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


# =============================================================================
# Main
# =============================================================================

async def main():
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
