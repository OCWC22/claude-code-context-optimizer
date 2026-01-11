# PRD: CCv3 Hackathon Edition - Final
## MongoDB Agentic Orchestration & Collaboration Hackathon - January 2026

**Problem Statement:** Statement One - Prolonged Coordination

**Tagline:** Context Engineering for Multi-Session Agentic Workflows via MCP

---

## Executive Summary

CCv3 (Continuous Context v3) is a **context engineering system** built as an **MCP server** for Claude Code. It enables AI agents to maintain coherent workflows across multiple sessions spanning hours or days. It solves the core challenge of **prolonged coordination**: how do you execute multi-step workflows, retain reasoning state, recover from failures, and ensure task consistency when sessions are interrupted?

### Proven Results

| Metric | RAW Claude | With CCv3 | Improvement |
|--------|------------|-----------|-------------|
| Input Tokens | 43,840 | 34,698 | **-20.9%** |
| Cost | $0.1605 | $0.1210 | **-24.6%** |
| Quality (Galileo) | - | 0.93 avg | ✓ |

### What Judges Will See

```
┌─────────────────────────────────────────────────────────────────────┐
│                  CCv3 + CLAUDE CODE INTEGRATION                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │  Claude Code │────▶│   CCv3 MCP   │────▶│ MongoDB Atlas│        │
│  │  (You type)  │     │   Server     │     │  (Context    │        │
│  │              │     │              │     │   Engine)    │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│         │                    │                     │               │
│         ▼                    ▼                     ▼               │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │ MCP Tools    │     │ Handoff Pack │     │  Run State   │        │
│  │ ccv3_index   │     │  (YAML/MD)   │     │  Tracking    │        │
│  │ ccv3_query   │     │              │     │              │        │
│  │ ccv3_handoff │     │              │     │              │        │
│  │ ccv3_sandbox │     │              │     │              │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│                                                                     │
│  DEPLOYMENT: uv + Docker + Vercel (serverless MCP)                │
│  SPONSORS: MongoDB Atlas + Fireworks AI + Voyage AI + Galileo + Vercel│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Table of Contents

1. [Hackathon Alignment](#1-hackathon-alignment)
2. [Current Implementation Status](#2-current-implementation-status)
3. [Sponsor Integrations](#3-sponsor-integrations)
4. [System Architecture](#4-system-architecture)
5. [MCP Server for Claude Code](#5-mcp-server-for-claude-code)
6. [Vercel Sandbox Integration](#6-vercel-sandbox-integration)
7. [Demo Script](#7-demo-script-for-judges)
8. [Deployment](#8-deployment)
9. [File Structure](#9-file-structure)
10. [Implementation Tasks](#10-implementation-tasks)

---

## 1. Hackathon Alignment

### Problem Statement One: Prolonged Coordination

> Create an agentic system capable of performing intricate, multi-step workflows that last hours or days, utilizing MongoDB as the context engine, while enduring failures, resisting modifications to tasks. How do you execute tool calls, retain reasoning state, recover from single failures, and ensure task consistency in multi-step tasks?

### How CCv3 Addresses This

| Requirement | CCv3 Solution | Implementation |
|-------------|---------------|----------------|
| **Hours/Days Workflows** | Session handoff packs stored in Atlas | `handoff.py` + `atlas.py` handoffs collection |
| **MongoDB Context Engine** | Single source of truth for all state | 9 collections: repos, files, symbols, graphs, handoffs, runs, embeddings, file_claims, sandbox_computations |
| **Failure Recovery** | Run state tracking with resumable steps | `atlas.py` runs collection with status tracking |
| **Tool Call Execution** | Inference router with function calling | `inference.py` with Fireworks AI |
| **Reasoning State Retention** | YAML/MD handoff packs with citations | `handoff.py` HandoffCompiler |
| **Task Consistency** | Quality gates via Galileo evaluation | `galileo.py` RAG Triad metrics |

### Winning Differentiators

1. **Real MongoDB Usage** - Not a wrapper. Atlas is the actual backend with:
   - Vector Search for semantic retrieval
   - TTL indexes for file claims
   - Hybrid RRF search (text + vector)
   - Run history tracking
   - Sandbox computation storage

2. **All Sponsors Integrated** - Each sponsor has a visible, defensible role:
   - MongoDB Atlas: Persistence + Vector Search (P0 required)
   - Fireworks AI: LLM inference with cost optimization ($0.03/M tokens)
   - Voyage AI: Embeddings with input_type adapters (query vs document)
   - Galileo AI: Quality gates before commit
   - Vercel: Deployment infrastructure + Vercel Sandbox

3. **Production-Ready Code** - Not a demo hack:
   - Async/await throughout
   - Proper error handling
   - In-memory fallbacks for testing
   - Type hints and documentation

---

## 2. Current Implementation Status

### Completed Components

| Module | File | Lines | Status | Sponsor |
|--------|------|-------|--------|---------|
| MongoDB Atlas Backbone | `atlas.py` | 840 | ✅ Complete | MongoDB |
| Voyage AI Embeddings | `embeddings.py` | 275 | ✅ Complete | Voyage AI |
| Fireworks Inference | `inference.py` | 362 | ✅ Complete | Fireworks |
| Galileo Evaluation | `galileo.py` | 452 | ✅ Complete | Galileo |
| Handoff Compiler | `handoff.py` | 376 | ✅ Complete | - |
| FastAPI Endpoints | `api.py` | 669 | ✅ Complete | Vercel |
| CLI Interface | `cli.py` | 392 | ✅ Complete | - |
| MCP Server | `mcp_server_standalone.py` | 430 | ✅ Complete | - |
| Vercel Sandbox | `sandbox/vercel_sandbox.py` | 253 | ✅ Complete | Vercel |
| Offline Embedder | `embed_codebase.py` | 318 | ✅ Complete | Voyage AI |
| Benchmark Suite | `benchmark_claude_comparison.py` | - | ✅ Complete | - |
| Evaluation Suite | `evals/` | - | ✅ Complete | Galileo |

### Data Model (All Collections)

```javascript
// MongoDB Atlas Collections (9 total)
repos: { repo_id, name, root_path_hash, languages, created_at }
files: { repo_id, path, sha, last_indexed_at, language }
symbols: { repo_id, file_path, symbol_id, kind, name, signature, span }
graphs: { repo_id, graph_type, file_path, nodes, edges, version, computed_at }
handoffs: { repo_id, task_id, yaml, markdown, citations, token_estimates, created_at }
runs: { repo_id, run_id, command, plan, patches, validations, eval_results, status, commit_sha }
embeddings: { repo_id, object_type, object_id, vector, metadata, content }
file_claims: { repo_id, file_path, session_id, claimed_at, expires_at }  // TTL index
sandbox_computations: { computation_id, code, result, config, created_at }  // Vercel Sandbox results
```

### Cost Optimization Status

**All Fireworks AI tasks use `minimax-m2p1` ($0.03/M tokens):**

```python
TASK_MODEL_MAP: dict[TaskType, str] = {
    "planning": "accounts/fireworks/models/minimax-m2p1",    # CHEAPEST
    "analysis": "accounts/fireworks/models/minimax-m2p1",    # CHEAPEST
    "coding": "accounts/fireworks/models/minimax-m2p1",      # CHEAPEST
    "patching": "accounts/fireworks/models/minimax-m2p1",    # CHEAPEST
    "cheap": "accounts/fireworks/models/minimax-m2p1",       # CHEAPEST
    "strong": "accounts/fireworks/models/minimax-m2p1",      # CHEAPEST
}
```

---

## 3. Sponsor Integrations

### P0 (Required for Finals)

#### MongoDB Atlas

**Role:** Single source of truth for all context and state

**Features Implemented:**
- ✅ 9 collections for complete data model
- ✅ Vector Search with `vector_index`
- ✅ Hybrid RRF search (text + vector fusion)
- ✅ TTL indexes for file claims
- ✅ Sandbox computation storage
- ✅ In-memory fallback for local development

**Demo Visibility:**
```python
# Shows in demo output:
✓ Connected to MongoDB Atlas: ccv3_hackathon
✓ Collections: repos, files, symbols, graphs, handoffs, runs, embeddings, file_claims, sandbox_computations
✓ Vector search enabled for RRF fusion
```

**Code Location:** `atlas.py` (840 lines)

#### Fireworks AI

**Role:** Cost-optimized LLM inference

**Features Implemented:**
- ✅ All tasks use minimax-m2p1 ($0.03/M tokens)
- ✅ OpenAI-compatible API
- ✅ Function calling support
- ✅ Streaming support

**Demo Visibility:**
```python
# Shows in demo output:
Provider: fireworks
Model: minimax-m2p1
Cost: $0.03 per million tokens
```

**Code Location:** `inference.py` (362 lines)

### P1 (Strong Differentiators)

#### Voyage AI

**Role:** High-quality embeddings for asymmetric retrieval

**Features Implemented:**
- ✅ voyage-3 model (1024 dimensions)
- ✅ Input type adapters: `query` vs `document`
- ✅ Batch embedding support (128 texts per request)
- ✅ Rate limit handling with exponential backoff
- ✅ Local hash-based fallback

**Demo Visibility:**
```python
# Shows in demo output:
Provider: voyage-3
Input Type: document (for storage)
Input Type: query (for search)
Dimensions: 1024
```

**Code Location:** `embeddings.py` (275 lines)

#### Galileo AI

**Role:** Quality evaluation gates

**Features Implemented:**
- ✅ RAG Triad metrics (context_adherence, chunk_relevance, correctness)
- ✅ Local heuristic fallback with improved tokenization
- ✅ Workflow evaluation
- ✅ Context quality evaluation

**Demo Visibility:**
```python
# Shows in demo output:
Quality Gate: PASSED
  context_adherence: 0.85 ✓
  chunk_relevance: 0.78 ✓
  correctness: 0.82 ✓
```

**Code Location:** `galileo.py` (452 lines)

### P2 (Deployment & Infrastructure)

#### Vercel

**Role:** Deployment infrastructure + Vercel Sandbox for code execution

**Features Implemented:**
- ✅ FastAPI ready for Vercel Python runtime
- ✅ Vercel Sandbox integration with official Python SDK
- ✅ Firecracker microVM isolation
- ✅ Python 3.13 runtime support
- ✅ Up to 16GB RAM, 5 hour timeout
- ✅ Results stored in MongoDB Atlas

**Code Location:** `api.py` (669 lines), `sandbox/vercel_sandbox.py` (253 lines)

---

## 4. System Architecture

### Core Philosophy: "Compound Then Clear"

CCv3 follows the **continuous compounding** approach:

1. **Compound Phase:** Sessions build on each other, accumulating:
   - Decisions made
   - Code diffs
   - Insights discovered
   - Gotchas encountered
   - Constraints identified
   - TODOs tracked

2. **Clear Phase:** Periodically distill into canonical artifacts:
   - `spec.md` - Clean goal + constraints + acceptance tests
   - `handoff.yaml` - Machine-readable task state
   - `decisions.md` - Why we chose X over Y
   - `context_pack.md` - Exact context fed to model

This avoids "summary-of-summary rot" while allowing progress to compound.

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DEVELOPER / AGENT                               │
│  CLI: /build /fix /premortem /handoff /query                            │
│  API: POST /chat /embed /search /eval /handoff /sandbox/execute         │
└─────────────────────────────────────────┬───────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        CCv3 Core                                        │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Handoff     │  │ Inference    │  │ Embeddings  │  │ Galileo     │  │
│  │ Compiler    │  │ Router       │  │ Router      │  │ Evaluator   │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └──────┬──────┘  │
└─────────┼────────────────┼─────────────────┼─────────────────┼──────────┘
          │                │                 │                 │
          ▼                ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      MongoDB Atlas (Backbone)                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ repos   │ │ handoffs│ │ runs    │ │embeds   │ │ sandbox │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│                                                                       │
│  Vector Search (RRF Fusion)  ←  Voyage Embeddings                     │
│  TTL Index (file_claims)     ←  Session Management                    │
│  Run History                 ←  Failure Recovery                     │
│  Sandbox Results             ←  Code Execution History               │
└─────────────────────────────────────────────────────────────────────────┘
          │                │                 │                 │
          ▼                ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────┐ ┌────────────┐ ┌────────────┐
│  Fireworks AI   │ │  Voyage AI  │ │  Galileo AI │ │   Vercel   │
│  (minimax-m2p1) │ │  (voyage-3) │ │  (RAG Triad)│ │  (Sandbox) │
└─────────────────┘ └─────────────┘ └────────────┘ └────────────┘
```

### Context Layers (from PRD)

```
Layer 0: Raw Code ──────────────▶ Don't feed this (huge, noisy)
    │
Layer 1: AST ───────────────────▶ Symbols, signatures, spans
    │
Layer 2: Call Graph ────────────▶ What calls what, dependencies
    │
Layer 3: Control Flow ──────────▶ Branches, loops, complexity
    │
Layer 4: Data Flow ─────────────▶ Where values originate
    │
Layer 5: PDG ───────────────────▶ What affects line X
    │
Layer 6: Handoff Pack ──────────▶ YAML/MD for model input
```

---

## 5. MCP Server for Claude Code

### Why MCP?

**MCP (Model Context Protocol)** is the standard way to extend Claude Code with custom tools. Instead of building a separate CLI, CCv3 exposes its functionality directly through MCP tools that Claude can call.

### Available MCP Tools

| Tool | Description | Use in Claude Code |
|------|-------------|---------------------|
| `ccv3_init` | Connect to MongoDB Atlas | `ccv3_init(path=".")` |
| `ccv3_index` | Index codebase with embeddings | `ccv3_index(path=".", extensions=".py,.ts")` |
| `ccv3_query` | Search indexed code | `ccv3_query(query="authentication flow")` |
| `ccv3_handoff` | Generate context pack | `ccv3_handoff(task="Add OAuth2")` |
| `ccv3_sandbox_execute` | Execute Python in Vercel Sandbox | `ccv3_sandbox_execute(code="print('hello')")` |
| `ccv3_status` | Check sponsor connections | `ccv3_status()` |

### Installation

```bash
# 1. Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Add to Claude Code
claude mcp add ccv3 \
  -e MONGODB_URI=your_mongo_uri \
  -e FIREWORKS_API_KEY=your_key \
  -e VOYAGE_API_KEY=your_key \
  -e VERCEL_OIDC_TOKEN=your_token \
  -- uv run python mcp_server_standalone.py
```

### Usage in Claude Code

```
You: /mcp

Claude: Available MCP servers:
  - ccv3 (connected)

You: Initialize CCv3 for this repo

Claude: [calls ccv3_init()]
✅ Connected to MongoDB Atlas
✅ All sponsors configured

You: Index this codebase

Claude: [calls ccv3_index()]
✅ Indexed 47 files with embeddings

You: Search for authentication code

Claude: [calls ccv3_query("authentication")]
Found 5 files:
  - auth_service.py (AuthService class)
  - routes.py (POST /login endpoint)
  ...

You: Execute this Python code in sandbox

Claude: [calls ccv3_sandbox_execute(code="import numpy; print(numpy.version.version)")]
🔧 Sandbox Execution Result
Status: completed
Exit Code: 0
--- STDOUT ---
1.26.0
```

---

## 6. Vercel Sandbox Integration

### Overview

CCv3 uses **Vercel Sandbox** for executing AI-generated code securely. This is critical for:
- **Multi-agent code execution** - Agents can share computed results
- **Mathematical computations** - numpy, scipy, pandas available
- **Security isolation** - Firecracker microVMs

### Implementation

File: `sandbox/vercel_sandbox.py`

```python
"""Vercel Sandbox Client - Isolated Python code execution.

Uses Vercel's official Python SDK for Sandbox execution.
- `from vercel.sandbox import Sandbox`
- `with Sandbox.create(runtime="python3.13") as sandbox: ...`

Authentication (preferred → fallback):
- **Preferred**: `VERCEL_OIDC_TOKEN`
- **Fallback**: `VERCEL_TOKEN` + `VERCEL_TEAM_ID` + `VERCEL_PROJECT_ID`
"""

class VercelSandboxClient:
    """Thin wrapper around vercel.sandbox.Sandbox."""

    async def execute(self, code: str, config: SandboxConfig) -> SandboxResult:
        """Execute Python code in Firecracker microVM."""
        with Sandbox.create(runtime="python3.13") as sandbox:
            cmd = sandbox.run_command("python", ["-c", code])
            return SandboxResult(
                status=SandboxStatus.COMPLETED,
                stdout=cmd.stdout(),
                stderr=cmd.stderr(),
                exit_code=cmd.exit_code,
            )
```

### Stored Results in MongoDB

Code execution results are stored in the `sandbox_computations` collection:

```javascript
{
  computation_id: "sbx-20260110-120000-abc12345",
  code: "print('hello')",
  result: { status: "completed", stdout: "hello\n", exit_code: 0 },
  config: { timeout: 120, memory_mb: 512 },
  created_at: "2026-01-10T12:00:00Z"
}
```

### Why Vercel Sandbox?

| Feature | Traditional Docker | Vercel Sandbox |
|---------|-------------------|----------------|
| Startup time | 1-2 seconds | **Milliseconds** |
| Max timeout | 30 seconds | **5 hours** |
| Resources | Fixed 512MB RAM | **Up to 16GB** |
| Isolation | Container | **Firecracker microVM** |
| Deployment | Manual | **Vercel managed** |

---

## 7. Demo Script for Judges

### 3-Minute Demo (First Round)

```
[00:00] INTRO (15 seconds)
───────────────────────────────────────────────────────────────
"The problem we're solving: AI agents can't maintain context
across sessions. When a workflow spans hours or days, how do
you recover from failures and maintain reasoning state?"

[00:15] SOLUTION OVERVIEW (30 seconds)
───────────────────────────────────────────────────────────────
"CCv3 is a context engineering system. We don't feed raw code
to LLMs. We compile structured 'handoff packs' stored in
MongoDB Atlas that capture only what's relevant."

[Shows architecture diagram with all sponsor logos]

[00:45] DEMO PART 1: Indexing (30 seconds)
───────────────────────────────────────────────────────────────
$ ccv3 init .
✓ Repository registered: ccv3-hackathon-a1b2c3d4

$ ccv3 index --full
✓ Indexed 47 files
✓ Generated 238 embeddings with Voyage AI voyage-3
✓ Stored in MongoDB Atlas: wctest cluster

[Shows MongoDB Atlas Collections in browser]

[01:15] DEMO PART 2: Query & Handoff (45 seconds)
───────────────────────────────────────────────────────────────
$ ccv3 query "authentication flow"
[1] [0.8923] auth_service.py
   AuthService.login() calls verify_token() and UserRepository.find()

$ ccv3 handoff "Add OAuth2 Google login"
─────────────────────────────────────────────────────────────
Token estimate: 1,247 (vs 23,456 raw)
Citations: 8 files

Handoff Pack:
  task: Add OAuth2 Google login
  symbols:
    - function: AuthService.login()
    - class: OAuth2Provider
    - function: TokenManager.generate()
  ...

"Notice: We went from 23k tokens to 1.2k tokens - 95% reduction
with full provenance."

[02:00] DEMO PART 3: Prolonged Workflow (60 seconds)
───────────────────────────────────────────────────────────────
$ ccv3 run /build "Add OAuth2 Google login"

[1/5] Planning...
Plan: 1) Create OAuth2Client 2) Add routes 3) Update AuthService

[2/5] Implementing...
✓ Created oauth2_client.py
✓ Modified auth_service.py

⚠️ SIMULATED FAILURE (Session interrupt)

[Session Resume]
$ ccv3 run /build --resume
Resuming from step 2/5...
✓ Routes added
✓ Tests passing

[Shows MongoDB run history with status changes:
 running → interrupted → running → completed]

[03:00] QUALITY GATE (15 seconds)
───────────────────────────────────────────────────────────────
Galileo Evaluation:
  context_adherence: 0.85 ✓
  chunk_relevance: 0.78 ✓
  correctness: 0.82 ✓

✓ Quality gate passed - ready to commit

[03:15] SPONSOR SUMMARY (30 seconds)
───────────────────────────────────────────────────────────────
"CCv3 uses MongoDB Atlas as the context engine, Voyage AI for
embeddings, Fireworks AI for cost-optimized inference, Galileo
for quality evaluation, and Vercel Sandbox for code execution.
Together, they enable AI agents to coordinate across prolonged
workflows."

[Shows all sponsor integrations working]
```

### 5-Minute Demo (Finals)

Include additional sections:
- Handoff pack YAML/MD format deep dive
- RRF fusion visualization (MongoDB Atlas Vector Search)
- Cost breakdown (Fireworks minimax-m2p1)
- Multi-agent collaboration demo (file claims)
- Vercel Sandbox execution demo

---

## 8. Deployment

### Local Development

```bash
# Install dependencies
uv sync

# Configure environment
# Create `.env` with your API keys

# Required environment variables:
export MONGODB_URI=mongodb+srv://...
export VOYAGE_API_KEY=pa-...
export FIREWORKS_API_KEY=fw_...
export GALILEO_API_KEY=...
export VERCEL_OIDC_TOKEN=...  # or VERCEL_TOKEN

# Embed a codebase (offline)
uv run python embed_codebase.py /path/to/repo --repo-id my-repo

# Run benchmark
uv run python benchmark_claude_comparison.py

# Start API server
uv run uvicorn api:app --reload --port 8000

# Start MCP server
uv run python mcp_server_standalone.py
```

### Docker Deployment

```bash
# Build MCP server
docker build -f Dockerfile.mcp -t ccv3-mcp .

# Run with docker-compose
docker-compose -f docker-compose.mcp.yml up
```

### Vercel Deployment

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel --prod

# Set environment variables in Vercel dashboard:
# MONGODB_URI, FIREWORKS_API_KEY, VOYAGE_API_KEY, GALILEO_API_KEY
```

### Environment Variables

```bash
# Required
MONGODB_URI=mongodb+srv://user:pass@cluster/db
FIREWORKS_API_KEY=fw_*
VOYAGE_API_KEY=pa-*
GALILEO_API_KEY=*

# Vercel Sandbox (one of these)
VERCEL_OIDC_TOKEN=*          # Preferred
VERCEL_TOKEN=*               # Fallback
VERCEL_TEAM_ID=team_*        # With VERCEL_TOKEN
VERCEL_PROJECT_ID=prj_*      # With VERCEL_TOKEN
```

---

## 9. File Structure

### Project Layout

```
claude-code-context-optimizer/
├── .env                      # Local env (not committed)
├── .gitignore                # Git ignore rules
├── pyproject.toml            # Python dependencies (uv)
├── uv.lock                   # Lockfile for reproducible builds
│
├── Core Modules
├── atlas.py                  # MongoDB Atlas backbone (840 lines)
├── embeddings.py             # Voyage AI embeddings router (275 lines)
├── inference.py              # Fireworks AI inference (362 lines)
├── galileo.py                # Galileo evaluation (452 lines)
├── handoff.py                # Handoff pack compiler (376 lines)
│
├── Interfaces
├── api.py                    # FastAPI endpoints (669 lines)
├── app.py                    # Vercel FastAPI entrypoint
├── cli.py                    # CLI commands (392 lines)
├── mcp_server_standalone.py  # MCP server (430 lines)
│
├── Tools
├── embed_codebase.py         # Offline embedding script (318 lines)
├── benchmark_claude_comparison.py  # Token benchmark
├── run_claude_benchmark.py   # Claude benchmark runner
│
├── Evaluation Suite
├── evals/
│   ├── __init__.py
│   ├── atlas_store.py        # Atlas storage for evals
│   ├── fireworks_client.py   # Fireworks client for evals
│   ├── galileo_observe.py    # Galileo integration
│   ├── run_evals.py          # Eval runner
│   └── utils.py              # Eval utilities
│
├── Vercel Sandbox
├── sandbox/
│   ├── __init__.py
│   └── vercel_sandbox.py     # Vercel SDK wrapper (253 lines)
│
├── Docker
├── Dockerfile.mcp            # MCP server Docker image
├── docker-compose.mcp.yml    # Docker Compose config
│
├── Documentation
├── PRD_HACKATHON_FINAL.md    # This document
├── README.md                 # Quick start guide
├── CLAUDE_BENCHMARK_REPORT.md
└── ATLAS_BENCHMARK_REPORT.md
```

---

## 10. Benchmark Results

### Token Reduction Analysis

**Test Setup:**
- Codebase: TuyaOpen WiFi module (1,847 files, 238 chunks embedded)
- Task: "Add a new WiFi scanning function"
- Provider: Claude 3.5 Sonnet

**Results:**

| Approach | Input Tokens | Output Tokens | Total Cost |
|----------|-------------|---------------|------------|
| RAW (full codebase) | 43,840 | 1,247 | $0.1605 |
| CCv3 (optimized) | 34,698 | 1,089 | $0.1210 |
| **Savings** | **-20.9%** | **-12.7%** | **-24.6%** |

**Quality Metrics (Galileo RAG Triad):**
- Context Adherence: 0.94
- Chunk Relevance: 0.91
- Correctness: 0.93
- **Average: 0.93** ✓

---

## Appendix A: API Endpoints

### FastAPI Endpoints

```
GET  /                          # Sponsor showcase
GET  /health                    # Health check
GET  /status                    # All sponsor status
POST /embed                     # Voyage AI embeddings
POST /chat                      # Fireworks inference
POST /search                    # Atlas hybrid search
POST /eval                      # Galileo evaluation
POST /handoff                   # Generate handoff pack
POST /sandbox/execute           # Vercel Sandbox execution
GET  /sandbox/status            # Sandbox health check
GET  /sandbox/history           # Computation history
GET  /sandbox/{computation_id}  # Get specific result
GET  /demo                      # Full workflow demo
```

### CLI Commands

```
ccv3 init .                     # Initialize repository
ccv3 index --full              # Build indexes
ccv3 query "text"              # Search context
ccv3 handoff "task"            # Generate pack
ccv3 status                    # Show provider status
ccv3 run /build "task"         # Execute workflow
ccv3 eval --query --response --context  # Evaluate quality
```

---

## Appendix B: Cost Analysis

### Fireworks AI (Current)

```
Model: minimax-m2p1
Cost: $0.03 per million tokens

Typical workflow:
- Planning: 500 tokens → $0.000015
- Coding: 2000 tokens → $0.00006
- Total per feature: ~$0.0001
```

### Voyage AI Embeddings

```
Model: voyage-3
Cost: ~$0.00013 per 1K tokens
Dimensions: 1024

Typical codebase (1000 files):
- ~500K tokens embedded → ~$0.065
- One-time cost, reuse for many queries
```

### Vercel Sandbox

```
Pricing: Active CPU only
- 1 vCPU = $0.00026/second (active)
- Idle time = FREE

Typical execution:
- Code execution: 5 seconds → $0.0013
- With numpy/scipy: 10 seconds → $0.0026
```

---

## Appendix C: Sponsor Contact Links

- **MongoDB Atlas**: https://www.mongodb.com/atlas
- **Fireworks AI**: https://fireworks.ai/
- **Voyage AI**: https://www.voyageai.com/
- **Galileo AI**: https://www.rungalileo.io/
- **Vercel**: https://vercel.com/

---

## Appendix D: Problem Statement Alignment Matrix

| Criteria | How CCv3 Addresses |
|----------|-------------------|
| **Intricate multi-step workflows** | Run tracking with step-by-step state in Atlas |
| **Hours or days duration** | Handoff packs enable session resumption |
| **MongoDB as context engine** | All state stored in Atlas (9 collections) |
| **Endure failures** | Status tracking: running → interrupted → running |
| **Resist task modifications** | Citations provide provenance for all decisions |
| **Execute tool calls** | Inference router with function calling |
| **Retain reasoning state** | YAML/MD handoff packs capture reasoning |
| **Recover from failures** | Run history allows exact state recovery |
| **Ensure task consistency** | Galileo quality gates before commit |

---

**Status:** ✅ READY FOR HACKATHON

**Last Updated:** 2026-01-10

**Version:** 2.1 - Updated to reflect actual implementation
