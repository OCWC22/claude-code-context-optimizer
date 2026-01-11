#!/usr/bin/env python3
"""
Live Demo Script - CCv3 Observable Benchmark
=============================================
Tests MongoDB Atlas, Voyage AI, and Galileo connections,
then runs a single observable benchmark query.

Usage:
    uv run python demo_live.py [repo_path]
    
Example:
    uv run python demo_live.py .
    uv run python demo_live.py /path/to/your/repo
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Rich for beautiful output
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

console = Console()

load_dotenv()


async def test_mongodb_connection() -> tuple[bool, str, int]:
    """Test MongoDB Atlas connection and return status."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        uri = os.environ.get("MONGODB_URI")
        db_name = os.environ.get("MONGODB_DB_NAME", "ccv3_hackathon")
        
        if not uri:
            return False, "MONGODB_URI not set", 0
        
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        
        # Test connection
        await client.admin.command('ping')
        
        # Count embeddings
        count = await db.embeddings.count_documents({})
        
        client.close()
        return True, f"Connected to {db_name}", count
        
    except Exception as e:
        return False, str(e)[:50], 0


async def test_voyage_connection() -> tuple[bool, str]:
    """Test Voyage AI API connection."""
    try:
        import httpx
        
        api_key = os.environ.get("VOYAGE_API_KEY")
        if not api_key:
            return False, "VOYAGE_API_KEY not set"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.voyageai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"input": ["test"], "model": "voyage-code-3"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                return True, "Voyage AI connected"
            else:
                return False, f"HTTP {response.status_code}"
                
    except Exception as e:
        return False, str(e)[:50]


async def test_galileo_connection() -> tuple[bool, str]:
    """Test Galileo API connection."""
    try:
        import httpx
        
        api_key = os.environ.get("GALILEO_API_KEY")
        if not api_key:
            return False, "GALILEO_API_KEY not set (will use local fallback)"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try the observe endpoint with a minimal test
            response = await client.post(
                "https://api.galileo.ai/v1/observe/workflows",
                headers={
                    "Content-Type": "application/json",
                    "Galileo-API-Key": api_key,
                },
                json={
                    "project_name": "ccv3-connection-test",
                    "workflows": []  # Empty test
                }
            )
            
            if response.status_code in [200, 201, 400, 422]:  # API is reachable (400/422 = validation error but reachable)
                return True, f"Galileo API connected (HTTP {response.status_code})"
            elif response.status_code in [401, 403]:
                return False, f"Galileo API key invalid (HTTP {response.status_code})"
            else:
                return False, f"HTTP {response.status_code}"
                
    except httpx.ConnectError:
        return False, "Cannot connect to api.galileo.ai"
    except httpx.TimeoutException:
        return False, "Connection timeout"
    except Exception as e:
        return False, f"Error: {str(e)[:40]}"


async def test_claude_cli() -> tuple[bool, str]:
    """Test Claude Code CLI availability."""
    try:
        process = await asyncio.create_subprocess_exec(
            "claude", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        
        if process.returncode == 0:
            version = stdout.decode().strip().split('\n')[0]
            return True, f"Claude CLI: {version}"
        else:
            return False, "Claude CLI not responding"
            
    except FileNotFoundError:
        return False, "Claude CLI not installed"
    except Exception as e:
        return False, str(e)[:50]


async def run_connection_tests():
    """Run all connection tests with live display."""
    
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]CCv3 Live Demo[/bold cyan]\n"
        "[dim]Testing connections to MongoDB Atlas, Voyage AI, Galileo, and Claude CLI[/dim]",
        border_style="cyan"
    ))
    console.print("\n")
    
    # Create status table
    table = Table(title="Connection Status", show_header=True, header_style="bold magenta")
    table.add_column("Service", style="cyan", width=20)
    table.add_column("Status", width=10)
    table.add_column("Details", style="dim")
    
    results = {}
    
    # Test all connections in parallel
    with console.status("[bold green]Testing connections...") as status:
        mongo_task = asyncio.create_task(test_mongodb_connection())
        voyage_task = asyncio.create_task(test_voyage_connection())
        galileo_task = asyncio.create_task(test_galileo_connection())
        claude_task = asyncio.create_task(test_claude_cli())
        
        mongo_ok, mongo_msg, embed_count = await mongo_task
        voyage_ok, voyage_msg = await voyage_task
        galileo_ok, galileo_msg = await galileo_task
        claude_ok, claude_msg = await claude_task
    
    # Build results table
    table.add_row(
        "MongoDB Atlas",
        "[green]✓ OK[/green]" if mongo_ok else "[red]✗ FAIL[/red]",
        f"{mongo_msg} ({embed_count:,} embeddings)" if mongo_ok else mongo_msg
    )
    table.add_row(
        "Voyage AI",
        "[green]✓ OK[/green]" if voyage_ok else "[red]✗ FAIL[/red]",
        voyage_msg
    )
    table.add_row(
        "Galileo",
        "[green]✓ OK[/green]" if galileo_ok else "[yellow]⚠ WARN[/yellow]",
        galileo_msg
    )
    table.add_row(
        "Claude CLI",
        "[green]✓ OK[/green]" if claude_ok else "[red]✗ FAIL[/red]",
        claude_msg
    )
    
    console.print(table)
    console.print("\n")
    
    results = {
        "mongodb": mongo_ok,
        "voyage": voyage_ok,
        "galileo": galileo_ok,
        "claude": claude_ok,
        "embed_count": embed_count
    }
    
    return results


async def run_full_benchmark():
    """Run the full observable benchmark."""
    
    console.print(Panel.fit(
        "[bold yellow]Running Full Observable Benchmark[/bold yellow]\n"
        "[dim]Comparing Raw vs Optimized Claude Code[/dim]",
        border_style="yellow"
    ))
    console.print("\n")
    
    # Import and run the main benchmark
    sys.path.insert(0, str(Path(__file__).parent))
    
    try:
        from run_observable_benchmark import main as benchmark_main
        await benchmark_main()
    except Exception as e:
        console.print(f"[red]Benchmark error: {e}[/red]")
        import traceback
        traceback.print_exc()
    
    console.print("\n[dim]Benchmark complete![/dim]\n")


async def main():
    """Main demo entry point."""
    
    # Get repo path from args or use current directory
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    repo_path = str(Path(repo_path).resolve())
    
    # Run connection tests
    results = await run_connection_tests()
    
    # Check if we can proceed
    if not results["mongodb"]:
        console.print("[red]❌ MongoDB connection failed. Cannot run benchmark.[/red]")
        console.print("[dim]Make sure MONGODB_URI is set in .env[/dim]")
        return
    
    if results["embed_count"] == 0:
        console.print("[yellow]⚠ No embeddings found in MongoDB.[/yellow]")
        console.print("[dim]Run: uv run python embed_codebase.py <repo_path>[/dim]\n")
    
    if not results["claude"]:
        console.print("[red]❌ Claude CLI not available. Cannot run benchmark.[/red]")
        console.print("[dim]Install Claude Code: https://claude.ai/code[/dim]")
        return
    
    # Check for --test flag (connection test only)
    if "--test" in sys.argv:
        console.print("[dim]Connection test complete. Use without --test to run full benchmark.[/dim]")
        return
    
    console.print("\n")
    
    # Run the full benchmark
    await run_full_benchmark()


if __name__ == "__main__":
    asyncio.run(main())
