# CCv3 - Claude Code Context Optimizer

**Hackathon Project**: Reduce Claude Code token usage by 20-25% through intelligent context engineering.

## 🎯 What It Does

CCv3 optimizes Claude Code's context window by:
1. **Embedding codebase** with Voyage AI → stored in MongoDB Atlas
2. **Vector search** to find only relevant code chunks
3. **Handoff packs** that provide minimal context for each task
4. **Quality validation** via Galileo AI RAG Triad metrics

## 📊 Results

| Metric | RAW Claude | With CCv3 | Improvement |
|--------|------------|-----------|-------------|
| Input Tokens | 43,840 | 34,698 | **-20.9%** |
| Cost | $0.1605 | $0.1210 | **-24.6%** |
| Quality (Galileo) | - | 0.93 avg | ✓ |

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ User Query  │────▶│ Voyage AI   │────▶│ MongoDB     │
│             │     │ (Embed)     │     │ Atlas       │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌─────────────┐     ┌──────▼──────┐
                    │ Galileo AI  │◀────│ Fireworks   │
                    │ (Evaluate)  │     │ (Inference) │
                    └─────────────┘     └─────────────┘
```

## 🚀 Quick Start

```bash
# Install dependencies
uv sync

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Embed a codebase
uv run python embed_codebase.py /path/to/repo --repo-id my-repo

# Run benchmark
uv run python benchmark_claude_comparison.py

# Start MCP server (for Claude Code integration)
uv run python mcp_server_standalone.py
```

## 🔧 Environment Variables

```bash
# MongoDB Atlas
MONGODB_URI=mongodb+srv://...
MONGODB_DB_NAME=ccv3_hackathon

# Voyage AI (Embeddings)
VOYAGE_API_KEY=pa-...

# Fireworks AI (Inference)  
FIREWORKS_API_KEY=fw_...

# Galileo AI (Evaluation)
GALILEO_API_KEY=...
```

## 📁 Project Structure

```
├── atlas.py              # MongoDB Atlas client (vector search)
├── embeddings.py         # Voyage AI embeddings
├── inference.py          # Fireworks AI inference router
├── galileo.py            # Galileo AI evaluation
├── handoff.py            # Context handoff pack generator
├── embed_codebase.py     # Offline embedding script
├── mcp_server_standalone.py  # MCP server for Claude Code
├── api.py                # FastAPI endpoints
├── cli.py                # CLI commands
├── evals/                # Evaluation suite
└── sandbox/              # Vercel Sandbox integration
```

## 🐳 Docker

```bash
# Build MCP server
docker build -f Dockerfile.mcp -t ccv3-mcp .

# Run with docker-compose
docker-compose -f docker-compose.mcp.yml up
```

## 📈 Sponsors

- **MongoDB Atlas** - Vector storage and search
- **Voyage AI** - Embeddings (voyage-3, 1024d)
- **Fireworks AI** - LLM inference (minimax-m2p1)
- **Galileo AI** - RAG quality evaluation
- **Vercel** - Sandbox execution

## 📄 License

MIT
