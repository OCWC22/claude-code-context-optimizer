#!/usr/bin/env python3
"""Claude Code Benchmark: WITH vs WITHOUT Context Optimizer.

Compares actual Claude Code token usage:
1. RAW: Claude reads files directly
2. OPTIMIZED: Claude uses pre-computed handoff packs

Usage:
    uv run python benchmark_claude_comparison.py
"""

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

TUYA_REPO = Path("/tmp/tuya-open")


@dataclass
class ClaudeResult:
    """Parsed Claude CLI result."""
    success: bool
    result_text: str
    duration_ms: int
    total_cost_usd: float
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    model_usage: dict
    error: str | None = None


def run_claude(prompt: str, cwd: Path, max_budget: float = 0.15) -> ClaudeResult:
    """Run Claude CLI and parse the JSON response."""
    
    cmd = [
        "claude",
        "--print",
        "--output-format", "json",
        "--model", "sonnet",
        "--max-budget-usd", str(max_budget),
        "--tools", "Read,Bash",
        "--dangerously-skip-permissions",
        prompt,
    ]
    
    start = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=180,
        )
        
        wall_time = int((time.time() - start) * 1000)
        
        if result.returncode != 0:
            return ClaudeResult(
                success=False,
                result_text="",
                duration_ms=wall_time,
                total_cost_usd=0,
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                model_usage={},
                error=result.stderr[:500] if result.stderr else "Unknown error",
            )
        
        data = json.loads(result.stdout)
        usage = data.get("usage", {})
        
        return ClaudeResult(
            success=data.get("subtype") == "success",
            result_text=data.get("result", ""),
            duration_ms=data.get("duration_ms", wall_time),
            total_cost_usd=data.get("total_cost_usd", 0),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_read_tokens=usage.get("cache_read_input_tokens", 0),
            model_usage=data.get("modelUsage", {}),
        )
        
    except subprocess.TimeoutExpired:
        return ClaudeResult(
            success=False,
            result_text="",
            duration_ms=180000,
            total_cost_usd=0,
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            model_usage={},
            error="Timeout after 180s",
        )
    except Exception as e:
        return ClaudeResult(
            success=False,
            result_text="",
            duration_ms=0,
            total_cost_usd=0,
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            model_usage={},
            error=str(e),
        )


def create_handoff_pack(task: str, files: list[str]) -> str:
    """Create a handoff pack with curated context."""
    
    pack_lines = [
        f"# Context Pack: {task}",
        "",
        "## Relevant Files",
        "",
    ]
    
    for file_path in files:
        full_path = TUYA_REPO / file_path
        if full_path.exists():
            content = full_path.read_text(errors="ignore")
            # Truncate long files
            if len(content) > 4000:
                content = content[:4000] + "\n... (truncated)"
            
            pack_lines.extend([
                f"### {file_path}",
                "```c",
                content,
                "```",
                "",
            ])
    
    return "\n".join(pack_lines)


def main():
    print("="*80)
    print("CLAUDE CODE BENCHMARK: WITH vs WITHOUT CONTEXT OPTIMIZER")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Repository: {TUYA_REPO}")
    print()
    
    # Check prerequisites
    if not TUYA_REPO.exists():
        print(f"❌ Repository not found: {TUYA_REPO}")
        sys.exit(1)
    
    result = subprocess.run(["which", "claude"], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Claude CLI not found")
        sys.exit(1)
    
    print("✓ Prerequisites OK")
    print()
    
    # Define tasks
    tasks = [
        {
            "name": "List WiFi Functions",
            "raw_prompt": "Read src/tal_wifi/include/tal_wifi.h and list all function declarations that start with 'OPERATE_RET'. Show the function name and parameters.",
            "context_files": ["src/tal_wifi/include/tal_wifi.h"],
            "optimized_query": "Based on the context, list all WiFi API functions with their parameters.",
        },
        {
            "name": "Explain WiFi Init",
            "raw_prompt": "Read src/tal_wifi/src/tal_wifi.c and explain what tal_wifi_init does. Be concise.",
            "context_files": ["src/tal_wifi/src/tal_wifi.c"],
            "optimized_query": "Based on the context, explain what tal_wifi_init does.",
        },
    ]
    
    results = []
    
    for task in tasks:
        print(f"\n{'#'*80}")
        print(f"# Task: {task['name']}")
        print(f"{'#'*80}")
        
        # RAW approach
        print("\n[RAW] Running Claude with file reading...")
        raw_result = run_claude(task["raw_prompt"], TUYA_REPO)
        
        print(f"  Success: {raw_result.success}")
        print(f"  Input tokens: {raw_result.input_tokens:,}")
        print(f"  Output tokens: {raw_result.output_tokens:,}")
        print(f"  Cache tokens: {raw_result.cache_read_tokens:,}")
        print(f"  Cost: ${raw_result.total_cost_usd:.6f}")
        print(f"  Duration: {raw_result.duration_ms}ms")
        
        # OPTIMIZED approach
        print("\n[OPTIMIZED] Running Claude with handoff pack...")
        handoff_pack = create_handoff_pack(task["name"], task["context_files"])
        pack_tokens = len(handoff_pack) // 4
        
        optimized_prompt = f"""You have been given a curated context pack. Answer the question using ONLY this context.

{handoff_pack}

Question: {task["optimized_query"]}
"""
        
        opt_result = run_claude(optimized_prompt, TUYA_REPO)
        
        print(f"  Handoff pack: ~{pack_tokens:,} tokens")
        print(f"  Success: {opt_result.success}")
        print(f"  Input tokens: {opt_result.input_tokens:,}")
        print(f"  Output tokens: {opt_result.output_tokens:,}")
        print(f"  Cache tokens: {opt_result.cache_read_tokens:,}")
        print(f"  Cost: ${opt_result.total_cost_usd:.6f}")
        print(f"  Duration: {opt_result.duration_ms}ms")
        
        # Calculate savings
        if raw_result.input_tokens > 0 and opt_result.input_tokens > 0:
            token_reduction = (raw_result.input_tokens - opt_result.input_tokens) / raw_result.input_tokens * 100
            cost_reduction = (raw_result.total_cost_usd - opt_result.total_cost_usd) / raw_result.total_cost_usd * 100 if raw_result.total_cost_usd > 0 else 0
            
            print(f"\n  📊 Token reduction: {token_reduction:.1f}%")
            print(f"  📊 Cost reduction: {cost_reduction:.1f}%")
        
        results.append({
            "task": task["name"],
            "raw": {
                "success": raw_result.success,
                "input_tokens": raw_result.input_tokens,
                "output_tokens": raw_result.output_tokens,
                "cache_tokens": raw_result.cache_read_tokens,
                "cost_usd": raw_result.total_cost_usd,
                "duration_ms": raw_result.duration_ms,
                "result_preview": raw_result.result_text[:300] if raw_result.result_text else "",
            },
            "optimized": {
                "success": opt_result.success,
                "handoff_tokens": pack_tokens,
                "input_tokens": opt_result.input_tokens,
                "output_tokens": opt_result.output_tokens,
                "cache_tokens": opt_result.cache_read_tokens,
                "cost_usd": opt_result.total_cost_usd,
                "duration_ms": opt_result.duration_ms,
                "result_preview": opt_result.result_text[:300] if opt_result.result_text else "",
            },
        })
    
    # Summary
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    
    total_raw_tokens = sum(r["raw"]["input_tokens"] for r in results)
    total_opt_tokens = sum(r["optimized"]["input_tokens"] for r in results)
    total_raw_cost = sum(r["raw"]["cost_usd"] for r in results)
    total_opt_cost = sum(r["optimized"]["cost_usd"] for r in results)
    
    print()
    print("| Metric | RAW | OPTIMIZED | Reduction |")
    print("|--------|-----|-----------|-----------|")
    print(f"| Input Tokens | {total_raw_tokens:,} | {total_opt_tokens:,} | {(total_raw_tokens - total_opt_tokens) / total_raw_tokens * 100:.1f}% |" if total_raw_tokens > 0 else "| Input Tokens | 0 | 0 | N/A |")
    print(f"| Total Cost | ${total_raw_cost:.6f} | ${total_opt_cost:.6f} | {(total_raw_cost - total_opt_cost) / total_raw_cost * 100:.1f}% |" if total_raw_cost > 0 else "| Total Cost | $0 | $0 | N/A |")
    
    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "tasks": results,
        "totals": {
            "raw_tokens": total_raw_tokens,
            "optimized_tokens": total_opt_tokens,
            "raw_cost": total_raw_cost,
            "optimized_cost": total_opt_cost,
            "token_reduction_pct": (total_raw_tokens - total_opt_tokens) / total_raw_tokens * 100 if total_raw_tokens > 0 else 0,
            "cost_reduction_pct": (total_raw_cost - total_opt_cost) / total_raw_cost * 100 if total_raw_cost > 0 else 0,
        },
    }
    
    Path("benchmark_comparison.json").write_text(json.dumps(report, indent=2))
    print()
    print("✓ Results saved to benchmark_comparison.json")


if __name__ == "__main__":
    main()
