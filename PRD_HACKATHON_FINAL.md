# PRD: CCv3 Hackathon Edition - Final
## MongoDB Agentic Orchestration & Collaboration Hackathon - January 2026

**Problem Statement:** Statement One - Prolonged Coordination

**Tagline:** Context Engineering for Multi-Session Agentic Workflows via MCP

---

## Executive Summary

CCv3 (Continuous Context v3) is a **context engineering system** built as an **MCP server** for Claude Code. It enables AI agents to maintain coherent workflows across multiple sessions spanning hours or days. It solves the core challenge of **prolonged coordination**: how do you execute multi-step workflows, retain reasoning state, recover from failures, and ensure task consistency when sessions are interrupted?

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
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│                                                                     │
│  DEPLOYMENT: uv + Docker + Vercel (serverless MCP)                │
│  SPONSORS: MongoDB Atlas + Fireworks AI + Jina AI + Galileo + Vercel│
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
| **MongoDB Context Engine** | Single source of truth for all state | 7 collections: repos, files, symbols, graphs, handoffs, runs, embeddings |
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

2. **All Sponsors Integrated** - Each sponsor has a visible, defensible role:
   - MongoDB Atlas: Persistence + Vector Search (P0 required)
   - Fireworks AI: LLM inference with cost optimization ($0.03/M tokens)
   - Jina AI: Embeddings with task adapters (retrieval.query vs retrieval.passage)
   - Galileo AI: Quality gates before commit
   - Vercel: Deployment infrastructure + optional Vercel Sandbox

3. **Production-Ready Code** - Not a demo hack:
   - Async/await throughout
   - Proper error handling
   - In-memory fallbacks for testing
   - Type hints and documentation

---

## 2. Current Implementation Status

### Completed Components

| Module | File | Status | Sponsor |
|--------|------|--------|---------|
| MongoDB Atlas Backbone | `atlas.py` | ✅ Complete | MongoDB |
| Jina v3 Embeddings | `embeddings.py` | ✅ Complete | Jina AI |
| Fireworks Inference | `inference.py` | ✅ Complete | Fireworks |
| Galileo Evaluation | `galileo.py` | ✅ Complete | Galileo |
| Handoff Compiler | `handoff.py` | ✅ Complete | - |
| FastAPI Endpoints | `api.py` | ✅ Complete | Vercel |
| CLI Interface | `cli.py` | ✅ Complete | - |
| Demo Script | `demo_hackathon.py` | ✅ Complete | - |
| Vercel Config | `vercel.json` | ✅ Complete | Vercel |

### Data Model (All Collections)

```javascript
// MongoDB Atlas Collections
repos: { repo_id, name, root_path_hash, languages, created_at }
files: { repo_id, path, sha, last_indexed_at, language }
symbols: { repo_id, file_path, symbol_id, kind, name, signature, span }
graphs: { repo_id, graph_type, file_path, nodes, edges, version, computed_at }
handoffs: { repo_id, task_id, yaml, markdown, citations, token_estimates, created_at }
runs: { repo_id, run_id, command, plan, patches, validations, eval_results, status, commit_sha }
embeddings: { repo_id, object_type, object_id, vector, metadata }
file_claims: { repo_id, file_path, session_id, claimed_at, expires_at }  // TTL index
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
- ✅ 7 collections for complete data model
- ✅ Vector Search with `vector_index`
- ✅ Hybrid RRF search (text + vector fusion)
- ✅ TTL indexes for file claims
- ✅ In-memory fallback for local development

**Demo Visibility:**
```python
# Shows in demo output:
✓ Connected to MongoDB Atlas: ccv3_hackathon
✓ Collections: repos, files, symbols, graphs, handoffs, runs, embeddings
✓ Vector search enabled for RRF fusion
```

**Code Location:** `atlas.py` (749 lines)

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

#### Jina AI

**Role:** Task-specific embeddings for asymmetric retrieval

**Features Implemented:**
- ✅ jina-embeddings-v3 (1024 dimensions)
- ✅ Task adapters: `retrieval.query` vs `retrieval.passage`
- ✅ Local hash-based fallback

**Demo Visibility:**
```python
# Shows in demo output:
Provider: jina-v3
Task: retrieval.passage (for storage)
Task: retrieval.query (for search)
Dimensions: 1024
```

**Code Location:** `embeddings.py` (249 lines)

#### Galileo AI

**Role:** Quality evaluation gates

**Features Implemented:**
- ✅ RAG Triad metrics (context_adherence, chunk_relevance, correctness)
- ✅ Local heuristic fallback
- ✅ Workflow evaluation

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

**Role:** Deployment infrastructure + optional Vercel Sandbox

**Features Implemented:**
- ✅ FastAPI ready for Vercel Python runtime
- ✅ `vercel.json` configuration
- ✅ Environment variable management

**Code Location:** `api.py` (499 lines), `vercel.json`

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
│  API: POST /chat /embed /search /eval /handoff                          │
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
│  │ repos   │ │ handoffs│ │ runs    │ │embeds   │ │ symbols │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│                                                                       │
│  Vector Search (RRF Fusion)  ←  Jina Embeddings                       │
│  TTL Index (file_claims)     ←  Session Management                    │
│  Run History                 ←  Failure Recovery                     │
└─────────────────────────────────────────────────────────────────────────┘
          │                │                 │
          ▼                ▼                 ▼
┌─────────────────┐ ┌─────────────┐ ┌────────────┐
│  Fireworks AI   │ │   Jina AI   │ │  Galileo AI │
│  (minimax-m2p1) │ │  (jina-v3)  │ │  (RAG Triad)│
└─────────────────┘ └─────────────┘ └────────────┘
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
| `ccv3_init` | Connect to MongoDB Atlas | `use ccv3 mcp` then `ccv3_init()` |
| `ccv3_index` | Index codebase with embeddings | `ccv3_index(path=".")` |
| `ccv3_query` | Search indexed code | `ccv3_query("authentication flow")` |
| `ccv3_handoff` | Generate context pack | `ccv3_handoff("Add OAuth2")` |
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
  -e JINA_API_KEY=your_key \
  -- uv run python mcp_server_standalone.py
```

### Usage in Claude Code

```
You: /mcp

Claude: Available MCP servers:
  - ccv3 (connected)

You: use ccv3 mcp

Claude: I'll use the CCv3 MCP tools.

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
"""Vercel Sandbox for CCv3 - AI-generated code execution."""

from vercel.sandbox import Sandbox

class VercelSandboxClient:
    """Execute Python code in Vercel Sandbox (Firecracker microVMs)."""

    def execute(
        self,
        code: str,
    ) -> dict:
        """Execute code and return results.

        Args:
            code: Python code to execute
        """
        with Sandbox.create(runtime="python3.13") as sandbox:
            command = sandbox.run_command("python", ["-c", code])
            return {
                "stdout": command.stdout(),
                "stderr": command.stderr(),
                "exit_code": getattr(command, "exit_code", None),
            }
```

### Stored Results in MongoDB

Code execution results are stored in the `sandbox_computations` collection:

```javascript
{
  repo_id: "my-repo",
  session_id: "abc-123",
  code: "print('hello')",
  result: { stdout: "hello\n", exit_code: 0 },
  timestamp: "2026-01-10T12:00:00Z"
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
✓ Generated 238 embeddings with Jina v3
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
"CCv3 uses MongoDB Atlas as the context engine, Jina v3 for
task-specific embeddings, Fireworks AI for cost-optimized
inference, and Galileo for quality evaluation. Together,
they enable AI agents to coordinate across prolonged workflows."

[Shows all sponsor integrations working]
```

### 5-Minute Demo (Finals)

Include additional sections:
- Handoff pack YAML/MD format deep dive
- RRF fusion visualization (MongoDB Atlas Vector Search)
- Cost breakdown (Fireworks minimax-m2p1)
- Multi-agent collaboration demo (file claims)

---

## 7. Deployment

### Local Development

```bash
# Install dependencies
uv sync

# Configure environment
# Create `.env` with your API keys (see `README_SETUP.md`)

# Run tests
uv run python test_hackathon_setup.py

# Run demo
uv run python demo_hackathon.py

# Start API server
uv run uvicorn api:app --reload --port 8000
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
# MONGODB_URI, FIREWORKS_API_KEY, JINA_API_KEY, GALILEO_API_KEY
```

### Environment Variables

```bash
# Required
MONGODB_URI=mongodb+srv://user:pass@cluster/db
FIREWORKS_API_KEY=fw_*
JINA_API_KEY=jina_*
GALILEO_API_KEY=*

# Optional
VERCEL_OIDC_TOKEN=*
VERCEL_TOKEN=*
VERCEL_TEAM_ID=team_*
VERCEL_PROJECT_ID=prj_*
```

---

## 8. File Structure

### Project Layout

```
claude-code-context-optimizer/
├── .env                      # Local env (not committed)
├── .gitignore                # Git ignore rules
├── pyproject.toml            # Python dependencies (uv)
├── vercel.json               # Vercel deployment config
│
├── Core Modules
├── atlas.py                  # MongoDB Atlas backbone (749 lines)
├── embeddings.py             # Jina v3 embeddings router (249 lines)
├── inference.py              # Fireworks AI inference (362 lines)
├── galileo.py                # Galileo evaluation (452 lines)
├── handoff.py                # Handoff pack compiler (376 lines)
│
├── Interfaces
├── api.py                    # FastAPI endpoints (499 lines)
├── app.py                    # Vercel FastAPI entrypoint (re-exports api.app)
├── cli.py                    # CLI commands (392 lines)
│
├── Demo & Testing
├── demo_hackathon.py         # Interactive demo (397 lines)
├── test_hackathon_setup.py   # Integration tests
├── test_simple.py            # Quick tests
├── test_connection.py        # Connection tests
│
├── Documentation
├── PRD_HACKATHON_FINAL.md    # This document
├── README_SETUP.md           # Setup guide
├── VERIFICATION_REPORT.md    # Code verification status
│
├── .agent/                   # Artifact Directory (CCv3 convention)
│   ├── spec.md               # Canonical goal + constraints + acceptance tests
│   ├── handoff.yaml          # Machine-readable task state
│   ├── decisions.md          # Non-obvious choices with rationale
│   ├── risks_premortem.md    # Edge cases + failure modes + mitigations
│   ├── context_pack.md       # What was fed to model (reproducibility)
│   ├── memory_working.md     # Scratch workspace (allowed to be ugly)
│   ├── memory_clear.md       # Cleaned canonical memory
│   └── run_log.md            # Timeline of actions (debugging)
│
└── Vercel Sandbox
    └── sandbox/
        ├── vercel_sandbox.py  # Vercel Python SDK wrapper (Sandbox.create + run_command)
        └── CLAUDE.md          # Notes / usage
```

### .agent/ Artifact Format (CCv3 Core Concept)

Every repo tracked by CCv3 has a `.agent/` directory containing canonical artifacts.

**spec.md** - Generated by `/discover`:
```markdown
# Feature: OAuth2 Google Login

## Scope
- Add Google OAuth2 authentication
- Support existing user accounts

## Constraints
- Must use existing AuthService
- No breaking changes to current login
- Must pass existing tests

## Acceptance Tests
- [ ] Google OAuth button visible on login page
- [ ] Callback handler creates/links user accounts
- [ ] Existing users can link Google to their account
- [ ] All existing tests still pass

## Out of Scope
- Other OAuth providers (Facebook, GitHub, etc.)
- Mobile app integration
```

**risks_premortem.md** - Generated by `/premortem`:
```markdown
# Premortem: OAuth2 Google Login

## Identified Risks

1. **Callback URL Configuration**
   - Risk: Wrong callback URL in Google Console
   - Mitigation: Validate config on startup
   - Detection: Integration test with real callback

2. **State Parameter Mismatch**
   - Risk: CSRF attack via OAuth state forgery
   - Mitigation: Use signed state tokens
   - Detection: Security test suite

3. **User Account Linking Conflicts**
   - Risk: Google email already exists with different auth method
   - Mitigation: Account merge flow with confirmation
   - Detection: Test with pre-existing accounts

## Rollback Plan
1. Feature flag: `ENABLE_GOOGLE_OAUTH=false` disables entirely
2. Database changes are additive (no destructive migrations)
3. UI changes are behind feature flags
```

**decisions.md** - Updated after each significant decision:
```markdown
# Decision Log

## 2026-01-10: Use `google-auth-library-python` over `requests`

**Context:** Need OAuth2 client implementation

**Options:**
1. `google-auth-library-python` - Official, maintained
2. `requests` + manual OAuth - More control, more code
3. `authlib` - Generic OAuth support

**Decision:** Option 1 - `google-auth-library-python`

**Rationale:**
- Official Google library = fewer breaking changes
- Handles token refresh automatically
- Less code to maintain

**Trade-offs:**
- Less fine-grained control over flow
- Additional dependency
```

---

## 11. Shift-Left Validation Hooks

### Pre-Hackathon Checklist

- [x] MongoDB Atlas connection working
- [x] Fireworks AI API configured with minimax-m2p1
- [x] Jina AI API configured with task adapters
- [x] Galileo AI API configured
- [x] All modules passing tests
- [x] Demo script running
- [x] Vercel deployment configuration

### During Hackathon

1. **Setup (30 min)**
   - Deploy to Vercel
   - Verify all API keys
   - Run full test suite

2. **Demo Preparation (2 hours)**
   - Practice demo script
   - Prepare MongoDB Atlas screenshots
   - Test failure recovery flow

3. **Contingency (1 hour)**
   - Have backup local demo ready
   - Prepare offline screenshots
   - Test in-memory fallbacks

### Final Submission Deliverables

- [ ] GitHub repository with:
  - [ ] README with quickstart
  - [ ] All source code
  - [ ] Demo video (1 minute)
  - [ ] `.env.example` (no secrets!)
- [ ] Deployed API endpoint
- [ ] Working demo for judges

---

## Appendix A: API Endpoints

### FastAPI Endpoints

```
GET  /                          # Sponsor showcase
GET  /health                    # Health check
GET  /status                    # All sponsor status
POST /embed                     # Jina embeddings
POST /chat                      # Fireworks inference
POST /search                    # Atlas hybrid search
POST /eval                      # Galileo evaluation
POST /handoff                   # Generate handoff pack
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

### Vercel Sandbox (Optional)

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
- **Jina AI**: https://jina.ai/
- **Galileo AI**: https://www.rungalileo.io/
- **Vercel**: https://vercel.com/

---

## Appendix D: Problem Statement Alignment Matrix

| Criteria | How CCv3 Addresses |
|----------|-------------------|
| **Intricate multi-step workflows** | Run tracking with step-by-step state in Atlas |
| **Hours or days duration** | Handoff packs enable session resumption |
| **MongoDB as context engine** | All state stored in Atlas (7 collections) |
| **Endure failures** | Status tracking: running → interrupted → running |
| **Resist task modifications** | Citations provide provenance for all decisions |
| **Execute tool calls** | Inference router with function calling |
| **Retain reasoning state** | YAML/MD handoff packs capture reasoning |
| **Recover from failures** | Run history allows exact state recovery |
| **Ensure task consistency** | Galileo quality gates before commit |

---

**Status:** ✅ READY FOR HACKATHON

**Last Updated:** 2026-01-10

**Version:** 2.0 - Hackathon Final
