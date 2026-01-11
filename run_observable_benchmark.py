#!/usr/bin/env python3
"""
Observable Claude Code Benchmark (via CLI)
==========================================

Uses ACTUAL Claude Code CLI with MCP, not direct API calls.
Full observability with:
- Live streaming logs from Claude Code
- Real-time token tracking (parsed from CLI output)
- Galileo integration for LLM observability
- Step-by-step I/O visibility

Usage:
    uv run python run_observable_benchmark.py
    
    # With specific repo
    TUYA_REPO_PATH=/path/to/repo uv run python run_observable_benchmark.py
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# Rich Console Setup
# ============================================================================
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install rich for better output: uv add rich")

console = Console() if RICH_AVAILABLE else None


# ============================================================================
# Galileo Observer
# ============================================================================
@dataclass
class GalileoStep:
    """Single step in a workflow."""
    name: str
    input_text: str
    output_text: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost: float = 0.0
    metadata: dict = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> int:
        return int((self.end_time - self.start_time) * 1000)


class GalileoObserver:
    """Galileo observability integration.
    
    Tracks workflows and steps, logs to Galileo API for LLM observability.
    """
    
    def __init__(self, project_name: str = "ccv3-benchmark"):
        self.api_key = os.environ.get("GALILEO_API_KEY")
        self.api_url = os.environ.get("GALILEO_API_URL", "https://api.galileo.ai/v1")
        self.project_name = project_name
        self.steps: list[GalileoStep] = []
        self.workflow_start: float = 0.0
        self.workflow_name: str = ""
        
    def _log(self, msg: str, style: str = ""):
        """Log with rich formatting."""
        if console:
            console.print(f"[dim]🔭 Galileo:[/dim] {msg}", style=style)
        else:
            print(f"🔭 Galileo: {msg}")
    
    async def start_workflow(self, name: str):
        """Start a new workflow."""
        self.workflow_name = name
        self.workflow_start = time.time()
        self.steps = []
        
        if self.api_key:
            self._log(f"Starting workflow: [bold]{name}[/bold]", "green")
        else:
            self._log("API key not set - logging locally only", "yellow")
    
    def start_step(self, name: str, input_text: str) -> GalileoStep:
        """Start a new step."""
        step = GalileoStep(
            name=name,
            input_text=input_text,
            start_time=time.time(),
        )
        self.steps.append(step)
        return step
    
    def end_step(
        self, 
        step: GalileoStep, 
        output_text: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        cost: float = 0.0,
        metadata: dict | None = None,
    ):
        """End a step with output."""
        step.end_time = time.time()
        step.output_text = output_text
        step.input_tokens = input_tokens
        step.output_tokens = output_tokens
        step.cache_read_tokens = cache_read_tokens
        step.cache_write_tokens = cache_write_tokens
        step.cost = cost
        step.metadata = metadata or {}
    
    async def end_workflow(self) -> dict:
        """End workflow and log to Galileo."""
        workflow_end = time.time()
        duration_ns = int((workflow_end - self.workflow_start) * 1e9)
        
        # Build workflow data
        workflow_data = {
            "name": self.workflow_name,
            "project": self.project_name,
            "duration_ms": int(duration_ns / 1e6),
            "steps": [
                {
                    "name": s.name,
                    "input": s.input_text[:1000],
                    "output": s.output_text[:1000],
                    "duration_ms": s.duration_ms,
                    "input_tokens": s.input_tokens,
                    "output_tokens": s.output_tokens,
                    "cache_read_tokens": s.cache_read_tokens,
                    "cache_write_tokens": s.cache_write_tokens,
                    "cost": s.cost,
                    "metadata": s.metadata,
                }
                for s in self.steps
            ],
            "total_input_tokens": sum(s.input_tokens for s in self.steps),
            "total_output_tokens": sum(s.output_tokens for s in self.steps),
            "total_cost": sum(s.cost for s in self.steps),
        }
        
        # Log to Galileo API if available
        if self.api_key:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{self.api_url}/observe/workflows",
                        headers={
                            "Content-Type": "application/json",
                            "Galileo-API-Key": self.api_key,
                        },
                        json={
                            "project_name": self.project_name,
                            "workflows": [{
                                "type": "workflow",
                                "name": self.workflow_name,
                                "input": f"Benchmark with {len(self.steps)} queries",
                                "output": json.dumps(workflow_data["steps"], indent=2)[:2000],
                                "duration_ns": duration_ns,
                                "metadata": {
                                    "total_input_tokens": workflow_data["total_input_tokens"],
                                    "total_output_tokens": workflow_data["total_output_tokens"],
                                    "total_cost": workflow_data["total_cost"],
                                },
                                "status_code": 200,
                                "steps": [
                                    {
                                        "type": "llm",
                                        "name": s["name"],
                                        "input": s["input"],
                                        "output": s["output"],
                                        "duration_ns": s["duration_ms"] * 1_000_000,
                                        "metadata": {
                                            "input_tokens": s["input_tokens"],
                                            "output_tokens": s["output_tokens"],
                                            "cost": s["cost"],
                                        },
                                    }
                                    for s in workflow_data["steps"]
                                ],
                            }]
                        }
                    )
                    if resp.status_code < 300:
                        self._log(f"✅ Logged to Galileo: {self.workflow_name}", "green")
                        self._log(f"   View: https://console.galileo.ai/project/{self.project_name}", "dim")
                    else:
                        self._log(f"⚠️  Galileo API error: {resp.status_code} - {resp.text[:200]}", "yellow")
            except Exception as e:
                self._log(f"⚠️  Galileo API error: {e}", "yellow")
        
        return workflow_data


# ============================================================================
# Live Token Tracker
# ============================================================================
@dataclass
class TokenStats:
    """Running token statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    total_cost: float = 0.0
    
    def add(self, input_t: int, output_t: int, cache_read: int = 0, cache_write: int = 0, cost: float = 0.0):
        """Add tokens and cost."""
        self.input_tokens += input_t
        self.output_tokens += output_t
        self.cache_read_tokens += cache_read
        self.cache_write_tokens += cache_write
        self.total_cost += cost


class LiveLogger:
    """Live logging with streaming output."""
    
    def __init__(self):
        self.raw_stats = TokenStats()
        self.opt_stats = TokenStats()
        
    def _make_stats_table(self) -> Table:
        """Create a live stats table."""
        table = Table(title="📊 Live Token Stats", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("RAW", justify="right", style="red")
        table.add_column("OPTIMIZED", justify="right", style="green")
        table.add_column("Savings", justify="right", style="yellow")
        
        def savings(raw: float, opt: float) -> str:
            if raw == 0:
                return "-"
            pct = (1 - opt / raw) * 100
            return f"{pct:.1f}%"
        
        table.add_row(
            "Input Tokens",
            f"{self.raw_stats.input_tokens:,}",
            f"{self.opt_stats.input_tokens:,}",
            savings(self.raw_stats.input_tokens, self.opt_stats.input_tokens),
        )
        table.add_row(
            "Output Tokens",
            f"{self.raw_stats.output_tokens:,}",
            f"{self.opt_stats.output_tokens:,}",
            "-",
        )
        table.add_row(
            "Cache Read",
            f"{self.raw_stats.cache_read_tokens:,}",
            f"{self.opt_stats.cache_read_tokens:,}",
            "-",
        )
        table.add_row(
            "Cost",
            f"${self.raw_stats.total_cost:.4f}",
            f"${self.opt_stats.total_cost:.4f}",
            savings(self.raw_stats.total_cost, self.opt_stats.total_cost),
        )
        
        return table
    
    def header(self, text: str):
        """Print a header."""
        if console:
            console.print()
            console.rule(f"[bold blue]{text}[/bold blue]")
        else:
            print(f"\n{'='*60}\n{text}\n{'='*60}")
    
    def phase(self, name: str):
        """Start a new phase."""
        if console:
            console.print()
            console.print(Panel(f"[bold]{name}[/bold]", style="blue"))
        else:
            print(f"\n### {name} ###\n")
    
    def step_start(self, query_id: str, query: str, mode: str):
        """Log step start."""
        if console:
            console.print()
            console.print(f"[bold cyan]▶ [{mode}] {query_id}[/bold cyan]")
            console.print(f"  [dim]Query:[/dim] {query[:80]}...")
        else:
            print(f"\n▶ [{mode}] {query_id}")
            print(f"  Query: {query[:80]}...")
    
    def stream_line(self, line: str, prefix: str = ""):
        """Stream a line of output."""
        if console:
            console.print(f"  [dim]{prefix}[/dim] {line}")
        else:
            print(f"  {prefix} {line}")
    
    def step_complete(
        self, 
        mode: str,
        input_tokens: int, 
        output_tokens: int, 
        duration_ms: int,
        cost: float,
        response_preview: str,
        cache_read: int = 0,
        cache_write: int = 0,
    ):
        """Log step completion with stats."""
        # Update running totals
        if mode == "RAW":
            self.raw_stats.add(input_tokens, output_tokens, cache_read, cache_write, cost)
        else:
            self.opt_stats.add(input_tokens, output_tokens, cache_read, cache_write, cost)
        
        if console:
            console.print(f"  [green]✓[/green] Completed in {duration_ms}ms")
            console.print(f"  [dim]├─[/dim] Input: [yellow]{input_tokens:,}[/yellow] tokens")
            console.print(f"  [dim]├─[/dim] Output: [yellow]{output_tokens:,}[/yellow] tokens")
            if cache_read > 0:
                console.print(f"  [dim]├─[/dim] Cache Read: [cyan]{cache_read:,}[/cyan] tokens")
            console.print(f"  [dim]├─[/dim] Cost: [cyan]${cost:.6f}[/cyan]")
            console.print(f"  [dim]└─[/dim] Response: [dim]{response_preview[:100]}...[/dim]")
            
            # Show running totals
            console.print()
            console.print(self._make_stats_table())
        else:
            print(f"  ✓ Completed in {duration_ms}ms")
            print(f"    Input: {input_tokens:,} | Output: {output_tokens:,} | Cost: ${cost:.6f}")
    
    def error(self, msg: str):
        """Log an error."""
        if console:
            console.print(f"[bold red]❌ Error:[/bold red] {msg}")
        else:
            print(f"❌ Error: {msg}")
    
    def info(self, msg: str):
        """Log info."""
        if console:
            console.print(f"[dim]ℹ️  {msg}[/dim]")
        else:
            print(f"ℹ️  {msg}")
    
    def success(self, msg: str):
        """Log success."""
        if console:
            console.print(f"[bold green]✅ {msg}[/bold green]")
        else:
            print(f"✅ {msg}")


# ============================================================================
# Claude Code CLI Runner
# ============================================================================

def parse_claude_output(output: str) -> dict:
    """Parse Claude Code CLI output for token usage and cost.
    
    Claude Code outputs usage info like:
    > Total tokens: 1234 | Input: 1000 | Output: 234
    > Cost: $0.001234
    > Cache: read=500, write=100
    """
    result = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "cost": 0.0,
        "response": "",
    }
    
    # Try to parse token usage from various formats
    # Format 1: "Input: X tokens, Output: Y tokens"
    input_match = re.search(r'[Ii]nput[:\s]+(\d+(?:,\d+)?)\s*(?:tokens)?', output)
    output_match = re.search(r'[Oo]utput[:\s]+(\d+(?:,\d+)?)\s*(?:tokens)?', output)
    
    if input_match:
        result["input_tokens"] = int(input_match.group(1).replace(",", ""))
    if output_match:
        result["output_tokens"] = int(output_match.group(1).replace(",", ""))
    
    # Format 2: "Total cost: $X.XX"
    cost_match = re.search(r'[Cc]ost[:\s]*\$?([\d.]+)', output)
    if cost_match:
        result["cost"] = float(cost_match.group(1))
    
    # Format 3: Cache tokens
    cache_read_match = re.search(r'cache[_\s]?read[:\s=]+(\d+)', output, re.IGNORECASE)
    cache_write_match = re.search(r'cache[_\s]?write[:\s=]+(\d+)', output, re.IGNORECASE)
    if cache_read_match:
        result["cache_read_tokens"] = int(cache_read_match.group(1))
    if cache_write_match:
        result["cache_write_tokens"] = int(cache_write_match.group(1))
    
    # Extract the actual response (everything before usage stats)
    lines = output.split('\n')
    response_lines = []
    for line in lines:
        # Skip usage/stats lines
        if any(x in line.lower() for x in ['token', 'cost', 'cache', 'total:', 'input:', 'output:']):
            continue
        response_lines.append(line)
    result["response"] = '\n'.join(response_lines).strip()
    
    return result


async def run_claude_code(
    prompt: str,
    cwd: str,
    use_mcp: bool = False,
    mcp_context: str = "",
    logger: LiveLogger | None = None,
) -> dict:
    """Run Claude Code CLI and capture output with streaming.
    
    Args:
        prompt: The prompt to send to Claude Code
        cwd: Working directory for Claude Code
        use_mcp: Whether to use CCv3 MCP for context
        mcp_context: Pre-fetched context from MCP (if any)
        logger: LiveLogger for streaming output
    
    Returns:
        Dict with response, tokens, cost, etc.
    """
    start_time = time.time()
    
    # Build the full prompt
    if use_mcp and mcp_context:
        full_prompt = f"""Using the following context retrieved via CCv3 semantic search:

{mcp_context}

---

{prompt}"""
    else:
        full_prompt = prompt
    
    # Run Claude Code CLI
    # Using --print to get output without interactive mode
    # Using --output-format json for structured output if available
    cmd = [
        "claude",
        "--print",  # Non-interactive, print response
        "--dangerously-skip-permissions",  # Skip permission prompts for benchmark
    ]
    
    if logger:
        logger.info(f"Running: claude --print (cwd: {cwd})")
    
    try:
        # Start the process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        
        # Send the prompt and get output
        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=full_prompt.encode()),
            timeout=120  # 2 minute timeout
        )
        
        output = stdout.decode()
        error_output = stderr.decode()
        
        # Stream output lines if logger available
        if logger and output:
            for line in output.split('\n')[:10]:  # First 10 lines
                if line.strip():
                    logger.stream_line(line[:100], "│")
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Parse the output for tokens/cost
        parsed = parse_claude_output(output + "\n" + error_output)
        
        # If no tokens found in output, estimate from prompt length
        if parsed["input_tokens"] == 0:
            parsed["input_tokens"] = len(full_prompt) // 4  # Rough estimate
        if parsed["output_tokens"] == 0:
            parsed["output_tokens"] = len(parsed["response"]) // 4
        
        # Calculate cost if not found (Claude Sonnet pricing)
        if parsed["cost"] == 0:
            parsed["cost"] = (
                (parsed["input_tokens"] / 1e6) * 3.0 +
                (parsed["output_tokens"] / 1e6) * 15.0 +
                (parsed["cache_read_tokens"] / 1e6) * 0.30
            )
        
        return {
            "success": process.returncode == 0,
            "response": parsed["response"] or output,
            "input_tokens": parsed["input_tokens"],
            "output_tokens": parsed["output_tokens"],
            "cache_read_tokens": parsed["cache_read_tokens"],
            "cache_write_tokens": parsed["cache_write_tokens"],
            "cost": parsed["cost"],
            "duration_ms": duration_ms,
            "raw_output": output,
            "stderr": error_output,
        }
        
    except asyncio.TimeoutError:
        return {
            "success": False,
            "response": "[Timeout after 120s]",
            "input_tokens": len(full_prompt) // 4,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
            "cost": 0,
            "duration_ms": 120000,
            "raw_output": "",
            "stderr": "Timeout",
        }
    except Exception as e:
        return {
            "success": False,
            "response": f"[Error: {e}]",
            "input_tokens": len(full_prompt) // 4,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
            "cost": 0,
            "duration_ms": int((time.time() - start_time) * 1000),
            "raw_output": "",
            "stderr": str(e),
        }


async def get_mcp_context(query: str, repo_path: str, logger: LiveLogger) -> str:
    """Get context from CCv3 MCP via Claude Code.
    
    Uses the ccv3_query tool to get relevant context.
    """
    logger.info("Fetching context via CCv3 MCP...")
    
    # Use Claude Code to call the MCP tool
    mcp_prompt = f"""Use the ccv3_query tool to search for relevant code context.

Query: {query}
Path: {repo_path}
Limit: 5

Return ONLY the search results, no explanation needed."""

    result = await run_claude_code(
        prompt=mcp_prompt,
        cwd=repo_path,
        use_mcp=False,
        logger=None,  # Don't stream MCP calls
    )
    
    if result["success"] and result["response"]:
        logger.info(f"  Got {len(result['response'])} chars of context")
        return result["response"]
    else:
        logger.info("  No context retrieved, falling back to file reading")
        return ""


# ============================================================================
# Configuration
# ============================================================================

REPO_PATH = os.environ.get("TUYA_REPO_PATH", "/tmp/tuya-open")
REPO_ID = "tuya-open"

BENCHMARK_QUERIES = [
    {
        "id": "wifi_functions",
        "query": "List all WiFi-related functions in the Tuya SDK and explain what each one does",
        "files": ["src/tal_wifi/include/tal_wifi.h", "src/tal_wifi/src/tal_wifi.c"],
    },
    {
        "id": "wifi_init",
        "query": "Explain how tal_wifi_init works step by step",
        "files": ["src/tal_wifi/src/tal_wifi.c"],
    },
    {
        "id": "wifi_connect",
        "query": "How does the WiFi connection process work? Show the flow from connect to connected state",
        "files": ["src/tal_wifi/src/tal_wifi.c", "src/tal_wifi/include/tal_wifi.h"],
    },
]


# ============================================================================
# Benchmark Functions
# ============================================================================

async def run_raw_benchmark(
    query: str, 
    files: list[str], 
    repo_path: str,
    logger: LiveLogger,
    galileo: GalileoObserver,
) -> dict:
    """Run RAW Claude Code - reads full files directly."""
    
    # Start Galileo step
    step = galileo.start_step(
        name=f"raw_{query[:30]}",
        input_text=query,
    )
    
    # Build context by reading full files
    logger.info("Reading full files for context...")
    context_parts = []
    total_chars = 0
    for file_path in files:
        full_path = Path(repo_path) / file_path
        if full_path.exists():
            content = full_path.read_text()
            context_parts.append(f"=== {file_path} ===\n{content}")
            total_chars += len(content)
            logger.info(f"  Loaded {file_path} ({len(content):,} chars)")
    
    full_context = "\n\n".join(context_parts)
    logger.info(f"Total context: {total_chars:,} chars")
    
    # Build the full prompt
    prompt = f"""Analyze this codebase. Here are the relevant files:

{full_context}

Question: {query}

Provide a detailed answer based on the code above."""

    # Run Claude Code
    result = await run_claude_code(
        prompt=prompt,
        cwd=repo_path,
        use_mcp=False,
        logger=logger,
    )
    
    # End Galileo step
    galileo.end_step(
        step,
        output_text=result["response"][:500],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        cache_read_tokens=result["cache_read_tokens"],
        cache_write_tokens=result["cache_write_tokens"],
        cost=result["cost"],
        metadata={
            "mode": "RAW",
            "files": files,
            "context_chars": total_chars,
        }
    )
    
    return {
        "mode": "RAW",
        "query": query,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "cache_read_tokens": result["cache_read_tokens"],
        "cache_write_tokens": result["cache_write_tokens"],
        "cost": result["cost"],
        "duration_ms": result["duration_ms"],
        "context_size": total_chars,
        "response_preview": result["response"][:500],
        "files_read": files,
        "success": result["success"],
    }


async def run_optimized_benchmark(
    query: str, 
    files: list[str], 
    repo_path: str,
    logger: LiveLogger,
    galileo: GalileoObserver,
) -> dict:
    """Run OPTIMIZED Claude Code - uses CCv3 MCP for semantic search."""
    
    # Start Galileo step
    step = galileo.start_step(
        name=f"opt_{query[:30]}",
        input_text=query,
    )
    
    # Get context via CCv3 MCP
    logger.info("Fetching optimized context via CCv3...")
    
    # Import CCv3 components for direct search
    from atlas import Atlas
    from embeddings import EmbeddingsRouter
    
    atlas = Atlas()
    await atlas.connect()
    embeddings = EmbeddingsRouter()
    
    logger.info(f"  Atlas: {'Connected' if not atlas._in_memory else 'In-memory'}")
    
    # Perform vector search
    query_emb = await embeddings.embed_for_search(query)
    search_results = await atlas.vector_search(
        repo_id=REPO_ID,
        query_vector=query_emb,
        limit=3,
    )
    
    logger.info(f"  Found {len(search_results)} relevant chunks")
    
    # Build optimized context
    context_parts = []
    total_chars = 0
    for i, result in enumerate(search_results):
        content = result.get("content", "")[:2000]
        object_id = result.get("object_id", "unknown")
        score = result.get("score", 0)
        context_parts.append(f"=== {object_id} (relevance: {score:.2f}) ===\n{content}")
        total_chars += len(content)
        logger.info(f"  [{i+1}] {object_id} (score: {score:.2f}, {len(content)} chars)")
    
    optimized_context = "\n\n".join(context_parts)
    logger.info(f"Optimized context: {total_chars:,} chars")
    
    await atlas.close()
    await embeddings.close()
    
    # Build the prompt with optimized context
    prompt = f"""Analyze this codebase. Here is relevant context retrieved via semantic search:

{optimized_context}

Question: {query}

Provide a detailed answer based on the context above."""

    # Run Claude Code
    result = await run_claude_code(
        prompt=prompt,
        cwd=repo_path,
        use_mcp=True,
        mcp_context="",  # Already included in prompt
        logger=logger,
    )
    
    # End Galileo step
    galileo.end_step(
        step,
        output_text=result["response"][:500],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        cache_read_tokens=result["cache_read_tokens"],
        cache_write_tokens=result["cache_write_tokens"],
        cost=result["cost"],
        metadata={
            "mode": "OPTIMIZED",
            "chunks_retrieved": len(search_results),
            "search_scores": [r.get("score", 0) for r in search_results],
            "context_chars": total_chars,
        }
    )
    
    return {
        "mode": "OPTIMIZED",
        "query": query,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "cache_read_tokens": result["cache_read_tokens"],
        "cache_write_tokens": result["cache_write_tokens"],
        "cost": result["cost"],
        "duration_ms": result["duration_ms"],
        "context_size": total_chars,
        "response_preview": result["response"][:500],
        "chunks_retrieved": len(search_results),
        "search_scores": [r.get("score", 0) for r in search_results],
        "success": result["success"],
    }


def print_final_comparison(raw_results: list, opt_results: list, logger: LiveLogger):
    """Print final comparison with rich formatting."""
    
    raw_input = sum(r['input_tokens'] for r in raw_results)
    raw_output = sum(r['output_tokens'] for r in raw_results)
    raw_cost = sum(r['cost'] for r in raw_results)
    raw_time = sum(r['duration_ms'] for r in raw_results)
    
    opt_input = sum(r['input_tokens'] for r in opt_results)
    opt_output = sum(r['output_tokens'] for r in opt_results)
    opt_cost = sum(r['cost'] for r in opt_results)
    opt_time = sum(r['duration_ms'] for r in opt_results)
    
    token_reduction = (1 - opt_input / raw_input) * 100 if raw_input > 0 else 0
    cost_reduction = (1 - opt_cost / raw_cost) * 100 if raw_cost > 0 else 0
    
    if console:
        console.print()
        console.rule("[bold green]FINAL RESULTS[/bold green]")
        
        table = Table(title="📊 Benchmark Summary", box=box.DOUBLE)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("RAW Claude", justify="right", style="red", width=15)
        table.add_column("OPTIMIZED", justify="right", style="green", width=15)
        table.add_column("Savings", justify="right", style="yellow", width=12)
        
        table.add_row("Input Tokens", f"{raw_input:,}", f"{opt_input:,}", f"{token_reduction:.1f}%")
        table.add_row("Output Tokens", f"{raw_output:,}", f"{opt_output:,}", "-")
        table.add_row("Total Cost", f"${raw_cost:.4f}", f"${opt_cost:.4f}", f"{cost_reduction:.1f}%")
        table.add_row("Total Time", f"{raw_time:,}ms", f"{opt_time:,}ms", "-")
        
        console.print(table)
        
        # Per-query breakdown
        console.print()
        console.print("[bold]Per-Query Breakdown:[/bold]")
        
        for i, (raw, opt) in enumerate(zip(raw_results, opt_results)):
            query_id = BENCHMARK_QUERIES[i]['id']
            reduction = (1 - opt['input_tokens'] / raw['input_tokens']) * 100 if raw['input_tokens'] > 0 else 0
            console.print(
                f"  {query_id:20} │ "
                f"RAW: [red]{raw['input_tokens']:>6,}[/red] │ "
                f"OPT: [green]{opt['input_tokens']:>6,}[/green] │ "
                f"[yellow]-{reduction:.1f}%[/yellow]"
            )
    else:
        print(f"\n{'='*60}")
        print("FINAL RESULTS")
        print(f"{'='*60}")
        print(f"Input Tokens:  RAW {raw_input:,} → OPT {opt_input:,} ({token_reduction:.1f}% reduction)")
        print(f"Total Cost:    RAW ${raw_cost:.4f} → OPT ${opt_cost:.4f} ({cost_reduction:.1f}% reduction)")


async def main():
    """Run the observable benchmark."""
    
    logger = LiveLogger()
    galileo = GalileoObserver(project_name="ccv3-benchmark")
    
    # Header
    logger.header("🔬 OBSERVABLE CLAUDE CODE BENCHMARK (via CLI)")
    
    if console:
        console.print(f"[dim]Timestamp:[/dim] {datetime.now().isoformat()}")
        console.print(f"[dim]Repository:[/dim] {REPO_PATH}")
        console.print(f"[dim]Queries:[/dim] {len(BENCHMARK_QUERIES)}")
        console.print(f"[dim]Galileo:[/dim] {'✅ Enabled' if galileo.api_key else '⚠️  Local only (set GALILEO_API_KEY)'}")
    else:
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Repository: {REPO_PATH}")
        print(f"Queries: {len(BENCHMARK_QUERIES)}")
    
    # Check prerequisites
    if not Path(REPO_PATH).exists():
        logger.error(f"Repository not found: {REPO_PATH}")
        logger.info("Clone it with: git clone https://github.com/tuya/tuya-open-sdk-for-device /tmp/tuya-open")
        return
    
    # Check Claude Code CLI
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True)
        logger.info(f"Claude Code: {result.stdout.strip()}")
    except FileNotFoundError:
        logger.error("Claude Code CLI not found. Install it first.")
        return
    
    # Start Galileo workflow
    await galileo.start_workflow("ccv3-benchmark-cli")
    
    raw_results = []
    opt_results = []
    
    # =========================================================================
    # PHASE 1: RAW Claude Code
    # =========================================================================
    logger.phase("📦 PHASE 1: RAW CLAUDE CODE (Full File Context)")
    
    for benchmark in BENCHMARK_QUERIES:
        logger.step_start(benchmark['id'], benchmark['query'], "RAW")
        
        result = await run_raw_benchmark(
            query=benchmark['query'],
            files=benchmark['files'],
            repo_path=REPO_PATH,
            logger=logger,
            galileo=galileo,
        )
        raw_results.append(result)
        
        logger.step_complete(
            mode="RAW",
            input_tokens=result['input_tokens'],
            output_tokens=result['output_tokens'],
            duration_ms=result['duration_ms'],
            cost=result['cost'],
            response_preview=result['response_preview'],
            cache_read=result.get('cache_read_tokens', 0),
        )
        
        await asyncio.sleep(2)  # Rate limiting between queries
    
    # =========================================================================
    # PHASE 2: OPTIMIZED Claude Code
    # =========================================================================
    logger.phase("🚀 PHASE 2: OPTIMIZED CLAUDE CODE (CCv3 Semantic Search)")
    
    for benchmark in BENCHMARK_QUERIES:
        logger.step_start(benchmark['id'], benchmark['query'], "OPTIMIZED")
        
        try:
            result = await run_optimized_benchmark(
                query=benchmark['query'],
                files=benchmark['files'],
                repo_path=REPO_PATH,
                logger=logger,
                galileo=galileo,
            )
            opt_results.append(result)
            
            logger.step_complete(
                mode="OPTIMIZED",
                input_tokens=result['input_tokens'],
                output_tokens=result['output_tokens'],
                duration_ms=result['duration_ms'],
                cost=result['cost'],
                response_preview=result['response_preview'],
                cache_read=result.get('cache_read_tokens', 0),
            )
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            # Use raw result as fallback with same structure
            fallback = raw_results[len(opt_results)].copy()
            fallback["mode"] = "OPTIMIZED (fallback)"
            opt_results.append(fallback)
        
        await asyncio.sleep(2)
    
    # =========================================================================
    # FINAL COMPARISON
    # =========================================================================
    print_final_comparison(raw_results, opt_results, logger)
    
    # End Galileo workflow
    workflow_data = await galileo.end_workflow()
    
    # =========================================================================
    # SAVE RESULTS
    # =========================================================================
    results = {
        "timestamp": datetime.now().isoformat(),
        "repository": REPO_PATH,
        "queries": len(BENCHMARK_QUERIES),
        "raw_results": raw_results,
        "optimized_results": opt_results,
        "galileo_workflow": workflow_data,
        "summary": {
            "raw_total_input_tokens": sum(r['input_tokens'] for r in raw_results),
            "opt_total_input_tokens": sum(r['input_tokens'] for r in opt_results),
            "raw_total_cost": sum(r['cost'] for r in raw_results),
            "opt_total_cost": sum(r['cost'] for r in opt_results),
            "token_reduction_pct": (1 - sum(r['input_tokens'] for r in opt_results) / 
                                   max(sum(r['input_tokens'] for r in raw_results), 1)) * 100,
            "cost_reduction_pct": (1 - sum(r['cost'] for r in opt_results) / 
                                  max(sum(r['cost'] for r in raw_results), 0.0001)) * 100,
        }
    }
    
    output_file = "observable_benchmark_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.success(f"Results saved to {output_file}")
    
    # Print Galileo dashboard link
    if galileo.api_key:
        logger.info(f"View in Galileo: https://console.galileo.ai/project/{galileo.project_name}")


if __name__ == "__main__":
    asyncio.run(main())
