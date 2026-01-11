# CCv3 - Claude Code Context Optimizer

<div align="center">

**🏆 MongoDB Agentic Orchestration & Collaboration Hackathon - January 2026**

*Context Engineering for Multi-Session Agentic Workflows via MCP*

[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green?logo=mongodb)](https://www.mongodb.com/atlas)
[![Voyage AI](https://img.shields.io/badge/Voyage-AI-blue)](https://www.voyageai.com/)
[![Fireworks](https://img.shields.io/badge/Fireworks-AI-orange)](https://fireworks.ai/)
[![Galileo](https://img.shields.io/badge/Galileo-AI-purple)](https://www.rungalileo.io/)
[![Vercel](https://img.shields.io/badge/Vercel-Sandbox-black?logo=vercel)](https://vercel.com/)

</div>

---

## 🎯 Problem Statement: Prolonged Coordination

> *How do you execute multi-step workflows that last hours or days, retain reasoning state, recover from failures, and ensure task consistency?*

**CCv3** solves this by creating an intelligent context engineering system that:
- **Reduces token usage by 77%** through semantic retrieval
- **Cuts costs by 67%** while maintaining quality
- **Enables session handoffs** via MongoDB-backed state persistence
- **Validates quality** with Galileo AI RAG Triad metrics

---

## 📊 Benchmark Results

### Token Reduction Performance

| Metric | RAW Claude | With CCv3 | Improvement |
|--------|------------|-----------|-------------|
| **Input Tokens** | 20,085 | 4,594 | **-77.1%** |
| **Total Cost** | $0.0693 | $0.0228 | **-67.1%** |
| **Quality Score** | - | 0.93 avg | ✓ Maintained |

### Per-Query Analysis (TuyaOpen WiFi SDK)

| Query | RAW Tokens | CCv3 Tokens | Reduction |
|-------|-----------|-------------|-----------|
| List WiFi functions | 7,889 | 1,498 | **81.0%** |
| Explain wifi_init | 4,304 | 1,489 | **65.4%** |
| WiFi connection flow | 7,892 | 1,607 | **79.6%** |

### Quality Validation (Galileo RAG Triad)

```
✓ Context Adherence:  0.94  │████████████████████░░░│  Excellent
✓ Chunk Relevance:    0.91  │███████████████████░░░░│  Excellent  
✓ Correctness:        0.93  │████████████████████░░░│  Excellent
─────────────────────────────────────────────────────────────────
  Average:            0.93  │████████████████████░░░│  PASSED ✓
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CCv3 SYSTEM ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │  Claude Code │────▶│   CCv3 MCP   │────▶│ MongoDB Atlas│        │
│  │  (You type)  │     │   Server     │     │  (9 Collections)│     │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│         │                    │                     │               │
│         ▼                    ▼                     ▼               │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │ MCP Tools    │     │ Handoff Pack │     │  Run State   │        │
│  │ • ccv3_index │     │  (YAML/MD)   │     │  Tracking    │        │
│  │ • ccv3_query │     │              │     │              │        │
│  │ • ccv3_handoff│    │              │     │              │        │
│  │ • ccv3_sandbox│    │              │     │              │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Voyage AI    │     │  Fireworks AI │     │  Galileo AI   │
│  voyage-3     │     │  minimax-m2p1 │     │  RAG Triad    │
│  1024d embed  │     │  $0.03/M tok  │     │  Quality Gate │
└───────────────┘     └───────────────┘     └───────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │    Vercel     │
                      │   Sandbox     │
                      │  Firecracker  │
                      └───────────────┘
```

---

## 🔌 Sponsor Integrations

### MongoDB Atlas (P0 - Required)
**Role:** Single source of truth for all context and state

| Feature | Implementation |
|---------|---------------|
| Vector Search | `vector_index` with RRF fusion |
| Collections | 9 total (repos, files, symbols, graphs, handoffs, runs, embeddings, file_claims, sandbox_computations) |
| TTL Indexes | Automatic file claim expiration |
| Hybrid Search | Text + Vector with Reciprocal Rank Fusion |

### Fireworks AI (P0 - Required)
**Role:** Cost-optimized LLM inference

| Feature | Value |
|---------|-------|
| Model | `minimax-m2p1` |
| Cost | **$0.03/M tokens** (cheapest) |
| API | OpenAI-compatible |
| Features | Function calling, streaming |

### Voyage AI (P1 - Differentiator)
**Role:** High-quality embeddings for retrieval

| Feature | Value |
|---------|-------|
| Model | `voyage-3` |
| Dimensions | 1024 |
| Input Types | `query` vs `document` adapters |
| Batch Size | 128 texts per request |

### Galileo AI (P1 - Differentiator)
**Role:** Quality evaluation gates

| Metric | Threshold | Purpose |
|--------|-----------|---------|
| Context Adherence | ≥0.7 | Response grounded in context |
| Chunk Relevance | ≥0.6 | Retrieved chunks are relevant |
| Correctness | ≥0.7 | Answer addresses query |

### Vercel (P2 - Infrastructure)
**Role:** Deployment + Isolated code execution

| Feature | Capability |
|---------|------------|
| Runtime | Python 3.13 |
| Max RAM | 16GB |
| Max Timeout | 5 hours |
| Isolation | Firecracker microVM |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/claude-code-context-optimizer.git
cd claude-code-context-optimizer

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```bash
# MongoDB Atlas (Required)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/ccv3_hackathon

# Voyage AI - Embeddings (Required)
VOYAGE_API_KEY=pa-...

# Fireworks AI - Inference (Required)
FIREWORKS_API_KEY=fw_...

# Galileo AI - Evaluation (Optional)
GALILEO_API_KEY=...

# Vercel Sandbox - Code Execution (Optional)
VERCEL_OIDC_TOKEN=...  # Preferred
# OR
VERCEL_TOKEN=...
VERCEL_TEAM_ID=team_...
VERCEL_PROJECT_ID=prj_...
```

### Usage

```bash
# 1. Embed a codebase (one-time)
uv run python embed_codebase.py /path/to/repo --repo-id my-repo

# 2. Run benchmark to verify token reduction
uv run python benchmark_claude_comparison.py

# 3. Start MCP server for Claude Code integration
uv run python mcp_server_standalone.py

# 4. Start API server (optional)
uv run uvicorn api:app --reload --port 8000
```

### Claude Code Integration

```bash
# Add CCv3 as MCP server
claude mcp add ccv3 \
  -e MONGODB_URI=$MONGODB_URI \
  -e VOYAGE_API_KEY=$VOYAGE_API_KEY \
  -e FIREWORKS_API_KEY=$FIREWORKS_API_KEY \
  -- uv run python mcp_server_standalone.py
```

---

## 🛠️ MCP Tools

| Tool | Description | Example |
|------|-------------|---------|
| `ccv3_init` | Connect to MongoDB Atlas | `ccv3_init(path=".")` |
| `ccv3_index` | Index codebase with embeddings | `ccv3_index(path=".", extensions=".py,.ts")` |
| `ccv3_query` | Semantic search indexed code | `ccv3_query(query="authentication")` |
| `ccv3_handoff` | Generate minimal context pack | `ccv3_handoff(task="Add OAuth2")` |
| `ccv3_sandbox_execute` | Execute Python in Vercel Sandbox | `ccv3_sandbox_execute(code="print(1+1)")` |
| `ccv3_status` | Check all sponsor connections | `ccv3_status()` |

---

## 📁 Project Structure

```
claude-code-context-optimizer/
├── Core Modules
│   ├── atlas.py              # MongoDB Atlas backbone (840 lines)
│   ├── embeddings.py         # Voyage AI embeddings (275 lines)
│   ├── inference.py          # Fireworks AI inference (362 lines)
│   ├── galileo.py            # Galileo evaluation (452 lines)
│   └── handoff.py            # Context pack compiler (376 lines)
│
├── Interfaces
│   ├── api.py                # FastAPI endpoints (669 lines)
│   ├── cli.py                # CLI commands (392 lines)
│   └── mcp_server_standalone.py  # MCP server (430 lines)
│
├── Tools
│   ├── embed_codebase.py     # Offline embedding script
│   ├── benchmark_claude_comparison.py  # Token benchmark
│   └── run_claude_benchmark.py  # Claude benchmark runner
│
├── Evaluation Suite
│   └── evals/
│       ├── atlas_store.py    # Atlas storage for evals
│       ├── fireworks_client.py  # Fireworks client
│       ├── galileo_observe.py   # Galileo integration
│       └── run_evals.py      # Eval runner
│
├── Vercel Sandbox
│   └── sandbox/
│       └── vercel_sandbox.py # Vercel SDK wrapper (253 lines)
│
└── Docker
    ├── Dockerfile.mcp
    └── docker-compose.mcp.yml
```

---

## 🐳 Docker Deployment

```bash
# Build MCP server image
docker build -f Dockerfile.mcp -t ccv3-mcp .

# Run with docker-compose
docker-compose -f docker-compose.mcp.yml up -d

# Check logs
docker-compose -f docker-compose.mcp.yml logs -f
```

---

## 📈 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Sponsor showcase |
| `/health` | GET | Health check |
| `/status` | GET | All sponsor status |
| `/embed` | POST | Voyage AI embeddings |
| `/chat` | POST | Fireworks inference |
| `/search` | POST | Atlas hybrid search |
| `/eval` | POST | Galileo evaluation |
| `/handoff` | POST | Generate handoff pack |
| `/sandbox/execute` | POST | Vercel Sandbox execution |
| `/sandbox/status` | GET | Sandbox health check |
| `/sandbox/history` | GET | Computation history |
| `/demo` | GET | Full workflow demo |

---

## 💰 Cost Analysis

### Per-Request Costs

| Service | Model | Cost |
|---------|-------|------|
| Fireworks AI | minimax-m2p1 | $0.03/M tokens |
| Voyage AI | voyage-3 | ~$0.00013/1K tokens |
| Vercel Sandbox | - | $0.00026/sec active |

### Typical Workflow Cost

```
Planning (500 tokens):     $0.000015
Coding (2000 tokens):      $0.00006
Embedding (1K files):      $0.065 (one-time)
Sandbox (10 sec):          $0.0026
────────────────────────────────────
Total per feature:         ~$0.07
```

### Savings vs Raw Approach

| Scenario | Raw Cost | CCv3 Cost | Savings |
|----------|----------|-----------|---------|
| Single query | $0.027 | $0.008 | **70%** |
| Full workflow | $0.069 | $0.023 | **67%** |
| Large codebase | $0.161 | $0.121 | **25%** |

---

## 🧪 Running Tests

```bash
# Run all tests
uv run pytest

# Run benchmark
uv run python benchmark_claude_comparison.py

# Run evaluation suite
uv run python -m evals.run_evals
```

---

## 📋 Problem Statement Alignment

| Requirement | CCv3 Solution |
|-------------|---------------|
| **Multi-step workflows** | Run tracking with step-by-step state in Atlas |
| **Hours/days duration** | Handoff packs enable session resumption |
| **MongoDB context engine** | 9 collections for complete state management |
| **Failure recovery** | Status tracking: running → interrupted → resumed |
| **Task consistency** | Galileo quality gates before commit |
| **Tool call execution** | Inference router with function calling |
| **Reasoning retention** | YAML/MD handoff packs with citations |

---

---

## 🙏 Acknowledgments

### Based On

This project is inspired by and builds upon the concepts from **[Continuous-Claude-v3](https://github.com/parcadei/Continuous-Claude-v3)** (⭐ 2.1k stars) by [@parcadei](https://github.com/parcadei).

> *"Context management for Claude Code. Hooks maintain state via ledgers and handoffs. MCP execution without context pollution. Agent orchestration with isolated context windows."*

Key concepts adapted from Continuous-Claude-v3:
- **Continuity Ledgers** - Persistent state across sessions
- **Handoff Packs** - YAML/MD context bundles for session resumption
- **MCP Integration** - Native Claude Code tool integration
- **Context Engineering** - Intelligent context window management

### What CCv3 Adds

| Feature | Continuous-Claude-v3 | CCv3 (This Project) |
|---------|----------------------|---------------------|
| Storage | PostgreSQL | **MongoDB Atlas** (Vector Search) |
| Embeddings | - | **Voyage AI** (voyage-3, 1024d) |
| Inference | - | **Fireworks AI** (minimax-m2p1) |
| Quality Gates | - | **Galileo AI** (RAG Triad) |
| Code Execution | Local MCP | **Vercel Sandbox** (Firecracker) |
| Search | Text-based | **Hybrid RRF** (Text + Vector) |
| Token Reduction | ~50% | **77%** measured |

### Sponsor Technologies

- **[MongoDB Atlas](https://www.mongodb.com/atlas)** - Vector storage and hybrid search
- **[Voyage AI](https://www.voyageai.com/)** - High-quality embeddings
- **[Fireworks AI](https://fireworks.ai/)** - Cost-optimized LLM inference
- **[Galileo AI](https://www.rungalileo.io/)** - RAG quality evaluation
- **[Vercel](https://vercel.com/)** - Sandbox execution and deployment

### Other Inspirations

- **[Anthropic](https://www.anthropic.com/)** - Claude Code and MCP protocol
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package management

---

## 📄 License

MIT

---

<div align="center">

**Built for MongoDB Agentic Orchestration & Collaboration Hackathon 2026**

Based on [Continuous-Claude-v3](https://github.com/parcadei/Continuous-Claude-v3) • Enhanced with MongoDB Atlas Vector Search

[MongoDB Atlas](https://www.mongodb.com/atlas) • [Voyage AI](https://www.voyageai.com/) • [Fireworks AI](https://fireworks.ai/) • [Galileo AI](https://www.rungalileo.io/) • [Vercel](https://vercel.com/)

</div>
