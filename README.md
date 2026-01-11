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

## 🙏 Acknowledgments

**CCv3** is inspired by and builds upon **[Continuous-Claude-v3](https://github.com/parcadei/Continuous-Claude-v3)** (⭐ 2.1k stars) by [@parcadei](https://github.com/parcadei).

> *"Context management for Claude Code. Hooks maintain state via ledgers and handoffs. MCP execution without context pollution. Agent orchestration with isolated context windows."*

**What CCv3 adds:** Enhanced with MongoDB Atlas Vector Search, Voyage AI embeddings, Fireworks AI inference, Galileo quality gates, and Vercel Sandbox execution—achieving **76% token reduction** and **51% cost savings** (vs ~50% in original).

---

## 🎯 Problem Statement: Prolonged Coordination

> *How do you execute multi-step workflows that last hours or days, retain reasoning state, recover from failures, and ensure task consistency?*

**CCv3** solves this by creating an intelligent context engineering system that:
- **Reduces token usage by 76%** through semantic retrieval (20,074 → 4,803 tokens)
- **Cuts costs by 51%** while maintaining quality ($0.1164 → $0.0574)
- **Enables session handoffs** via MongoDB-backed state persistence
- **Provides full observability** with Galileo AI workflow tracking

---

## 📊 Benchmark Results

### Token Reduction Performance

| Metric | RAW Claude | With CCv3 | Improvement |
|--------|------------|-----------|-------------|
| **Input Tokens** | 20,074 | 4,803 | **-76.1%** |
| **Output Tokens** | 3,744 | 2,869 | -23.4% |
| **Total Cost** | $0.1164 | $0.0574 | **-50.6%** |
| **Context Size** | 79,550 chars | 18,000 chars | **-77.4%** |

### Per-Query Analysis (TuyaOpen WiFi SDK)

| Query | RAW Tokens | CCv3 Tokens | Reduction | Cost Saved |
|-------|-----------|-------------|-----------|------------|
| List WiFi functions | 7,886 | 1,602 | **-79.7%** | $0.0184 |
| Explain wifi_init | 4,300 | 1,593 | **-63.0%** | $0.0058 |
| WiFi connection flow | 7,888 | 1,608 | **-79.6%** | $0.0348 |

### Vector Search Quality (MongoDB Atlas)

```
Query 1 (wifi_functions):
  ├─ [1] tkl_wifi.c:3      score: 0.81 ████████████████░░░░ Excellent
  ├─ [2] tal_wifi.c        score: 0.81 ████████████████░░░░ Excellent
  └─ [3] tal_wifi.h        score: 0.81 ████████████████░░░░ Excellent

Query 2 (wifi_init):
  ├─ [1] tal_wifi.c        score: 0.79 ███████████████░░░░░ Good
  ├─ [2] tkl_wifi.c:0      score: 0.77 ███████████████░░░░░ Good
  └─ [3] tal_wifi.h        score: 0.76 ███████████████░░░░░ Good

Query 3 (wifi_connect):
  ├─ [1] tkl_wifi.c:3      score: 0.76 ███████████████░░░░░ Good
  ├─ [2] tkl_wifi.c:0      score: 0.76 ███████████████░░░░░ Good
  └─ [3] tal_wifi.h        score: 0.73 ██████████████░░░░░░ Good
```

### Live Observable Output

```
╔══════════════════════╦═════════════════╦═════════════════╦══════════════╗
║ Metric               ║      RAW Claude ║       OPTIMIZED ║      Savings ║
╠══════════════════════╬═════════════════╬═════════════════╬══════════════╣
║ Input Tokens         ║          20,074 ║           4,803 ║        76.1% ║
║ Output Tokens        ║           3,744 ║           2,869 ║        23.4% ║
║ Total Cost           ║         $0.1164 ║         $0.0574 ║        50.6% ║
║ Total Time           ║        77,808ms ║        90,669ms ║            - ║
╚══════════════════════╩═════════════════╩═════════════════╩══════════════╝
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

### Claude Code Integration

```bash
# Add CCv3 as MCP server to Claude Code
claude mcp add ccv3 \
  -e MONGODB_URI=$MONGODB_URI \
  -e VOYAGE_API_KEY=$VOYAGE_API_KEY \
  -e FIREWORKS_API_KEY=$FIREWORKS_API_KEY \
  -- uv run python mcp_server_standalone.py

# Verify it's connected
claude mcp list
```

---

## 🔬 Run Your Own Benchmark

Compare **RAW Claude Code** vs **CCv3 Optimized** on any repository.

### Step 1: Clone a Repository to Test

```bash
# Example: TuyaOpen WiFi SDK (used in our benchmark)
git clone https://github.com/tuya/tuya-open-sdk-for-device /tmp/tuya-open

# Or use your own repo
# git clone https://github.com/your-org/your-repo /tmp/your-repo
```

### Step 2: Vectorize the Repository

```bash
# Embed the codebase into MongoDB Atlas with Voyage AI embeddings
uv run python embed_codebase.py /tmp/tuya-open \
  --repo-id tuya-open \
  --patterns "*.c" "*.h" \
  --max-files 100 \
  --batch-size 8

# For a Python/JS project:
# uv run python embed_codebase.py /tmp/your-repo \
#   --repo-id your-repo \
#   --patterns "*.py" "*.ts" "*.js"
```

**Output:**
```
Embedding codebase: /tmp/tuya-open
Repository ID: tuya-open
Patterns: ['*.c', '*.h']

✓ Connected to MongoDB Atlas: ccv3_hackathon
Scanning for files...
Found 100 files to embed
Prepared 156 chunks from 98 files

Embedding chunks...
  Embedded 8/156 chunks
  Embedded 16/156 chunks
  ...
  Embedded 156/156 chunks

============================================================
EMBEDDING COMPLETE
============================================================
Files processed: 98
Chunks embedded: 156
Total characters: 892,456
Estimated tokens: 223,114
```

### Step 3: Configure Benchmark Queries (Optional)

Edit `run_observable_benchmark.py` to customize queries for your repo:

```python
# Default queries (for TuyaOpen WiFi SDK)
BENCHMARK_QUERIES = [
    {
        "id": "wifi_functions",
        "query": "List all WiFi-related functions and explain what each one does",
        "files": ["src/tal_wifi/include/tal_wifi.h", "src/tal_wifi/src/tal_wifi.c"],
    },
    # Add your own queries...
]

# Change repo path
REPO_PATH = "/tmp/your-repo"
REPO_ID = "your-repo"
```

### Step 4: Run the Observable Benchmark

```bash
# Run benchmark with live streaming output
uv run python run_observable_benchmark.py
```

**What it does:**
1. **Phase 1 (RAW):** Runs queries with full file context (no optimization)
2. **Phase 2 (OPTIMIZED):** Runs same queries with CCv3 semantic search
3. **Compares:** Token usage, cost, and response quality

**Live Output:**
```
──────────────── 🔬 OBSERVABLE CLAUDE CODE BENCHMARK (via CLI) ─────────────────
Timestamp: 2026-01-10T18:00:20
Repository: /tmp/tuya-open
Queries: 3
Galileo: ✅ Enabled

╭──────────────────────────────────────────────────────────────────────────────╮
│ 📦 PHASE 1: RAW CLAUDE CODE (Full File Context)                              │
╰──────────────────────────────────────────────────────────────────────────────╯

▶ [RAW] wifi_functions
  Query: List all WiFi-related functions...
ℹ️  Reading full files for context...
ℹ️    Loaded src/tal_wifi/include/tal_wifi.h (14,266 chars)
ℹ️    Loaded src/tal_wifi/src/tal_wifi.c (17,006 chars)
ℹ️  Total context: 31,272 chars
ℹ️  Calling Claude Code CLI...
  ✓ Completed in 25,272ms
  ├─ Input: 7,886 tokens
  ├─ Output: 1,307 tokens
  └─ Cost: $0.0433

╭──────────────────────────────────────────────────────────────────────────────╮
│ 🚀 PHASE 2: OPTIMIZED CLAUDE CODE (CCv3 Semantic Search)                     │
╰──────────────────────────────────────────────────────────────────────────────╯

▶ [OPTIMIZED] wifi_functions
ℹ️  Fetching optimized context via CCv3...
✓ Connected to MongoDB Atlas: ccv3_hackathon
ℹ️    Found 3 relevant chunks
ℹ️    [1] tkl_wifi.c:3 (score: 0.81, 2000 chars)
ℹ️    [2] tal_wifi.c (score: 0.81, 2000 chars)
ℹ️    [3] tal_wifi.h (score: 0.81, 2000 chars)
ℹ️  Optimized context: 6,000 chars
  ✓ Completed in 26,235ms
  ├─ Input: 1,602 tokens (vs 7,886 RAW = -79.7%)
  ├─ Output: 1,338 tokens
  └─ Cost: $0.0249

──────────────────────────────── FINAL RESULTS ─────────────────────────────────
╔══════════════════════╦═════════════════╦═════════════════╦══════════════╗
║ Metric               ║      RAW Claude ║       OPTIMIZED ║      Savings ║
╠══════════════════════╬═════════════════╬═════════════════╬══════════════╣
║ Input Tokens         ║          20,074 ║           4,803 ║        76.1% ║
║ Output Tokens        ║           3,744 ║           2,869 ║        23.4% ║
║ Total Cost           ║         $0.1164 ║         $0.0574 ║        50.6% ║
╚══════════════════════╩═════════════════╩═════════════════╩══════════════╝

✅ Results saved to observable_benchmark_results.json
```

### Step 5: View Results

```bash
# View JSON results
cat observable_benchmark_results.json | jq '.summary'

# Output:
{
  "raw_total_input_tokens": 20074,
  "opt_total_input_tokens": 4803,
  "raw_total_cost": 0.1164,
  "opt_total_cost": 0.0574,
  "token_reduction_pct": 76.1,
  "cost_reduction_pct": 50.6
}
```

### Requirements

| Requirement | Purpose |
|-------------|---------|
| `MONGODB_URI` | Store embeddings and search |
| `VOYAGE_API_KEY` | Generate embeddings |
| `claude` CLI | Run Claude Code commands |
| Repository | Any codebase to benchmark |

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
│   ├── embed_codebase.py     # Vectorize any codebase
│   └── run_observable_benchmark.py  # Compare RAW vs OPTIMIZED Claude Code
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

# Run observable benchmark (see "Run Your Own Benchmark" section above)
uv run python run_observable_benchmark.py

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

## 📄 License

MIT

---

<div align="center">

**Built for MongoDB Agentic Orchestration & Collaboration Hackathon 2026**

[MongoDB Atlas](https://www.mongodb.com/atlas) • [Voyage AI](https://www.voyageai.com/) • [Fireworks AI](https://fireworks.ai/) • [Galileo AI](https://www.rungalileo.io/) • [Vercel](https://vercel.com/)

</div>
