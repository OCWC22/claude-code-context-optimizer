#!/usr/bin/env python3
"""Sponsor-aligned eval runner for CCv3 (Hackathon edition).

This is intentionally hackathon-minimal:
  - Regression suite: deterministic fixture-based code changes + unittest pass/fail
  - Benchmark suite: baseline vs enhanced token usage (measured from Fireworks usage tokens)
  - Sponsor integrations:
      - MongoDB Atlas: runs/tasks/artifacts/results/corpus
      - Jina v3: 1024-d embeddings for retrieval corpus
      - Fireworks: MiniMax M2 inference
      - Galileo: Observe workflow logging (best-effort)

USAGE (from repo root):
  # Install dependencies with uv
  uv sync

  # Benchmark: baseline vs enhanced
  uv run python evals/run_evals.py --suite benchmark --mode both

  # Regression: deterministic fixture tasks
  uv run python evals/run_evals.py --suite regression --mode both
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from evals.atlas_store import AtlasEvalStore
from evals.fireworks_client import FireworksChatClient
from evals.galileo_observe import GalileoObserveClient
from evals.utils import (
    build_baseline_context,
    build_retrieved_context,
    chunk_file_text,
    copy_tree,
    json_dumps,
    now_ms,
    read_text,
    render_json_only_system_prompt,
    safe_relpath,
    write_text,
)


try:
    import yaml  # type: ignore

    HAS_YAML = True
except Exception:
    HAS_YAML = False


Mode = Literal["baseline", "enhanced"]
Suite = Literal["benchmark", "regression"]


def _tokenize(text: str) -> set[str]:
    import re

    toks = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    return set(toks)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def local_rag_triad(query: str, answer: str, context: str) -> dict[str, float]:
    """Local, deterministic triad-like heuristics (fallback when Galileo metrics aren't available)."""
    q = _tokenize(query)
    a = _tokenize(answer)
    c = _tokenize(context)
    return {
        "context_relevance": _jaccard(q, c),
        "answer_relevance": _jaccard(q, a),
        "groundedness_proxy": _jaccard(a, c),
    }


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sponsor-aligned eval runner")
    p.add_argument("--suite", choices=["benchmark", "regression"], default="benchmark")
    p.add_argument("--mode", choices=["baseline", "enhanced", "both"], default="both")
    p.add_argument("--case", default="all", help="Case id to run, or 'all'")
    p.add_argument("--top-k", type=int, default=5, help="Top-k retrieved chunks for enhanced mode")
    p.add_argument("--baseline-max-chars", type=int, default=120_000)
    p.add_argument("--enhanced-max-chars", type=int, default=20_000)
    p.add_argument("--chunk-max-chars", type=int, default=1200)
    p.add_argument("--chunk-overlap-chars", type=int, default=150)
    p.add_argument("--max-tokens", type=int, default=900)
    p.add_argument("--temperature", type=float, default=0.0)
    return p.parse_args([a for a in sys.argv[1:] if not a.endswith(".py")])


def _load_yaml(path: Path) -> dict[str, Any]:
    if not HAS_YAML:
        raise RuntimeError("PyYAML not installed. Install with: uv add pyyaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _repo_root() -> Path:
    # evals/run_evals.py → evals → repo root
    return Path(__file__).resolve().parents[1]


def _cases_path(suite: Suite) -> Path:
    base = Path(__file__).resolve().parent / "cases"
    return base / ("benchmark.yaml" if suite == "benchmark" else "regression.yaml")


def _fixture_root(fixture_name: str) -> Path:
    return Path(__file__).resolve().parent / "fixtures" / fixture_name


def _collect_files(root: Path, rel_paths: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for rp in rel_paths:
        full = (root / rp).resolve()
        if full.exists() and full.is_file():
            out.append((rp, read_text(full)))
    return out


def _collect_fixture_files_for_baseline(fixture_root: Path) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = []
    for rel in ["README.md"]:
        p = fixture_root / rel
        if p.exists():
            files.append((rel, read_text(p)))

    src_dir = fixture_root / "src"
    if src_dir.exists():
        for p in sorted(src_dir.rglob("*.py")):
            rel = str(p.relative_to(fixture_root)).replace("\\", "/")
            files.append((rel, read_text(p)))

    tests_dir = fixture_root / "tests"
    if tests_dir.exists():
        for p in sorted(tests_dir.rglob("test_*.py")):
            rel = str(p.relative_to(fixture_root)).replace("\\", "/")
            files.append((rel, read_text(p)))

    return files


async def _build_corpus_and_retrieve(
    *,
    store: AtlasEvalStore,
    corpus_id: str,
    files: list[tuple[str, str]],
    query: str,
    top_k: int,
    chunk_max_chars: int,
    chunk_overlap_chars: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Embed chunks with Jina (or fallback) and retrieve top-k from Atlas."""

    # NOTE:
    # This repo's embedding implementation lives in `embeddings.py` (Jina v3 + local fallback).
    # The previous implementation referenced `scripts.core...` from a different codebase.
    from embeddings import JinaEmbeddings

    # Deterministic 1024-d fallback embedder (keeps evals runnable without network/API keys).
    # Not for production retrieval quality — only for “does the pipeline work” testing.
    class _HashEmbedder:
        def __init__(self, *, dimensions: int = 1024):
            self.dimensions = dimensions

        def _hash_embed(self, text: str) -> list[float]:
            import hashlib
            import math

            seed = text.strip().lower().encode("utf-8", errors="ignore")
            vec: list[float] = []
            for i in range(self.dimensions):
                h = hashlib.sha256(seed + b"::" + str(i).encode("ascii")).digest()
                # Map first 8 bytes to a float in [-1, 1]
                x = int.from_bytes(h[:8], "big") / ((1 << 64) - 1)
                vec.append(x * 2.0 - 1.0)
            # Normalize to unit length (cosine-friendly)
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            return [v / norm for v in vec]

        async def embed(self, text: str, *, task: str) -> list[float]:
            _ = task
            return self._hash_embed(text)

        async def embed_batch(self, texts: list[str], *, task: str) -> list[list[float]]:
            _ = task
            return [self._hash_embed(t) for t in texts]

    use_jina = bool(os.environ.get("JINA_API_KEY"))
    passage_provider = "jina" if use_jina else "hash"
    query_provider = "jina" if use_jina else "hash"
    if use_jina:
        passage_embedder: Any = JinaEmbeddings(dimensions=1024)
        query_embedder: Any = JinaEmbeddings(dimensions=1024)
    else:
        passage_embedder = _HashEmbedder(dimensions=1024)
        query_embedder = _HashEmbedder(dimensions=1024)

    # Chunk + embed
    chunk_docs: list[dict[str, Any]] = []
    all_texts: list[str] = []
    for rel_path, content in files:
        for ch in chunk_file_text(
            rel_path,
            content,
            max_chars=chunk_max_chars,
            overlap_chars=chunk_overlap_chars,
        ):
            chunk_docs.append(
                {
                    "chunk_id": ch.chunk_id,
                    "file_path": ch.file_path,
                    "text": ch.text,
                    "metadata": ch.metadata or {},
                }
            )
            all_texts.append(ch.text)

    if use_jina:
        embeddings = await passage_embedder.embed_batch(all_texts, task="retrieval.passage", batch_size=256)
    else:
        embeddings = await passage_embedder.embed_batch(all_texts, task="retrieval.passage")
    for doc, emb in zip(chunk_docs, embeddings):
        doc["embedding"] = emb

    await store.upsert_corpus_chunks(corpus_id=corpus_id, chunks=chunk_docs)

    if use_jina:
        q_vec = await query_embedder.embed(query, task="retrieval.query")
    else:
        q_vec = await query_embedder.embed(query, task="retrieval.query")
    retrieved = await store.vector_search(corpus_id=corpus_id, query_vector=q_vec, limit=top_k)

    stats = {
        "corpus_id": corpus_id,
        "provider_passage": passage_provider,
        "provider_query": query_provider,
        "dimension": len(q_vec),
        "chunks_indexed": len(chunk_docs),
        "chunks_returned": len(retrieved),
        "top_k": top_k,
        "vector_index": store.vector_index,
    }

    # Close HTTP clients if using Jina (best-effort; don't fail evals if close errors)
    if use_jina:
        try:
            await passage_embedder.close()
        except Exception:
            pass
        try:
            await query_embedder.close()
        except Exception:
            pass
    return retrieved, stats


async def _fireworks_answer(
    *,
    fw: FireworksChatClient,
    prompt: str,
    context: str,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Answer using only the provided context when possible.",
        },
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nTASK:\n{prompt}"},
    ]
    result = await fw.chat(messages=messages, temperature=temperature, max_tokens=max_tokens)
    return {
        "text": result.content,
        "model": result.model,
        "usage": {
            "prompt_tokens": result.usage.prompt_tokens,
            "completion_tokens": result.usage.completion_tokens,
            "total_tokens": result.usage.total_tokens,
        },
        "latency_ms": result.latency_ms,
        "raw": result.raw,
    }


async def _fireworks_code_change(
    *,
    fw: FireworksChatClient,
    prompt: str,
    context: str,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": render_json_only_system_prompt()},
        {"role": "user", "content": f"REPO CONTEXT:\n{context}\n\nTASK:\n{prompt}"},
    ]
    result = await fw.chat(messages=messages, temperature=temperature, max_tokens=max_tokens)
    return {
        "text": result.content,
        "model": result.model,
        "usage": {
            "prompt_tokens": result.usage.prompt_tokens,
            "completion_tokens": result.usage.completion_tokens,
            "total_tokens": result.usage.total_tokens,
        },
        "latency_ms": result.latency_ms,
        "raw": result.raw,
    }


def _apply_model_files(workdir: Path, model_text: str) -> list[str]:
    """Parse JSON and write files into workdir. Returns list of written rel paths."""
    try:
        obj = json.loads(model_text)
    except Exception as e:
        raise ValueError(f"Model output is not valid JSON: {type(e).__name__}: {e}")

    files = obj.get("files")
    if not isinstance(files, list):
        raise ValueError("Model JSON must contain a 'files' list")

    written: list[str] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            continue
        rel = safe_relpath(path)
        write_text(workdir, rel, content)
        written.append(rel)
    return written


def _run_cmd(cmd: str, cwd: Path, *, extra_env: dict[str, str] | None = None) -> tuple[int, str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc.returncode, proc.stdout


def _run_test_command(test_command: str, cwd: Path, *, extra_env: dict[str, str] | None = None) -> tuple[int, str]:
    """Run test commands in a way that is robust under `uv run`.

    Many CI/dev environments run the harness via `uv run python ...`. In that case,
    shelling out to `python ...` may accidentally pick up a different interpreter.

    We special-case the most common pattern used by our fixtures:
      - `python -m unittest ...`
    """
    prefix = "python -m unittest "
    if test_command.strip().startswith(prefix):
        args = test_command.strip().split()[3:]  # after: python -m unittest
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", *args],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        return proc.returncode, proc.stdout
    return _run_cmd(test_command, cwd, extra_env=extra_env)


def _assertions_ok(assertions: list[dict[str, Any]], *, workdir: Path, response_text: str | None = None) -> tuple[bool, str]:
    for a in assertions:
        t = a.get("type")
        if t == "file_contains":
            rel = a.get("path")
            needle = a.get("contains")
            if not isinstance(rel, str) or not isinstance(needle, str):
                return False, "invalid file_contains assertion"
            p = (workdir / rel).resolve()
            if not p.exists():
                return False, f"missing file for assertion: {rel}"
            content = read_text(p)
            if needle not in content:
                return False, f"assertion failed: {rel} missing {needle!r}"
        elif t == "response_contains":
            needle = a.get("contains")
            if not isinstance(needle, str) or response_text is None:
                return False, "invalid response_contains assertion"
            if needle.lower() not in response_text.lower():
                return False, f"assertion failed: response missing {needle!r}"
        else:
            return False, f"unknown assertion type: {t}"
    return True, "ok"


async def run_benchmark_case(
    *,
    case: dict[str, Any],
    mode: Mode,
    args: argparse.Namespace,
    store: AtlasEvalStore,
    fw: FireworksChatClient,
    galileo: GalileoObserveClient,
) -> dict[str, Any]:
    case_id = case["id"]
    name = case.get("name", case_id)
    baseline_files: list[str] = case.get("baseline_files") or []
    prompt: str = case.get("prompt") or ""
    retrieval_query: str = case.get("retrieval_query") or prompt
    assertions: list[dict[str, Any]] = case.get("assertions") or []

    root = _repo_root()
    files = _collect_files(root, baseline_files)

    started_at_ms = now_ms()
    run_id = await store.create_run(
        {
            "suite": "benchmark",
            "case_id": case_id,
            "case_name": name,
            "mode": mode,
            "started_at_ms": started_at_ms,
        }
    )

    corpus_id = str(uuid4())
    retrieval_stats: dict[str, Any] | None = None
    if mode == "baseline":
        context = build_baseline_context(files, max_chars=args.baseline_max_chars)
    else:
        retrieved, retrieval_stats = await _build_corpus_and_retrieve(
            store=store,
            corpus_id=corpus_id,
            files=files,
            query=retrieval_query,
            top_k=args.top_k,
            chunk_max_chars=args.chunk_max_chars,
            chunk_overlap_chars=args.chunk_overlap_chars,
        )
        context = build_retrieved_context(retrieved, max_chars=args.enhanced_max_chars)

    resp = await _fireworks_answer(
        fw=fw,
        prompt=prompt,
        context=context,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )

    ok, why = _assertions_ok(assertions, workdir=root, response_text=resp["text"])
    triad = local_rag_triad(retrieval_query, resp["text"], context)

    await store.append_artifact(
        {
            "run_id": run_id,
            "type": "model_response",
            "model": resp["model"],
            "usage": resp["usage"],
            "latency_ms": resp["latency_ms"],
            "response_text": resp["text"][:20_000],
        }
    )
    await store.append_eval_result(
        {
            "run_id": run_id,
            "triad": triad,
            "assertions_ok": ok,
            "assertions_reason": why,
            "retrieval_stats": retrieval_stats or {},
        }
    )

    # Also store a compact summary on the run document (easy querying / charts)
    await store.update_run(
        run_id,
        {
            "completed_at_ms": now_ms(),
            "metrics": {
                "ok": ok,
                "reason": why,
                "model": resp["model"],
                "usage": resp["usage"],
                "latency_ms": resp["latency_ms"],
                "triad": triad,
                "retrieval_stats": retrieval_stats or {},
            },
        },
    )

    # Best-effort Galileo logging
    await galileo.log_workflow(
        name=f"{case_id}:{mode}",
        input_text=prompt,
        output_text=resp["text"][:20_000],
        metadata={
            "suite": "benchmark",
            "mode": mode,
            "case_id": case_id,
            "run_id": run_id,
            "usage": resp["usage"],
            "triad": triad,
            "retrieval": retrieval_stats or {},
        },
    )

    return {
        "run_id": run_id,
        "case_id": case_id,
        "case_name": name,
        "mode": mode,
        "ok": ok,
        "reason": why,
        "usage": resp["usage"],
        "latency_ms": resp["latency_ms"],
        "triad": triad,
        "retrieval": retrieval_stats or {},
    }


async def run_regression_case(
    *,
    case: dict[str, Any],
    mode: Mode,
    args: argparse.Namespace,
    store: AtlasEvalStore,
    fw: FireworksChatClient,
    galileo: GalileoObserveClient,
    fixture_root: Path,
) -> dict[str, Any]:
    case_id = case["id"]
    name = case.get("name", case_id)
    kind = case.get("kind", "code_change")

    started_at_ms = now_ms()
    run_id = await store.create_run(
        {
            "suite": "regression",
            "case_id": case_id,
            "case_name": name,
            "mode": mode,
            "started_at_ms": started_at_ms,
        }
    )

    workdir = copy_tree(fixture_root)
    try:
        baseline_files = _collect_fixture_files_for_baseline(workdir)

        async def do_phase(phase: dict[str, Any], *, handoff_context: str | None = None) -> dict[str, Any]:
            prompt = phase.get("prompt") or ""
            retrieval_query = phase.get("retrieval_query") or prompt
            test_command = phase.get("test_command")
            assertions: list[dict[str, Any]] = phase.get("assertions") or []

            if mode == "baseline":
                context = build_baseline_context(baseline_files, max_chars=args.baseline_max_chars)
            else:
                # Enhanced: prefer handoff context if provided (resume case)
                if handoff_context is not None:
                    context = handoff_context
                else:
                    corpus_id = str(uuid4())
                    retrieved, retrieval_stats = await _build_corpus_and_retrieve(
                        store=store,
                        corpus_id=corpus_id,
                        files=baseline_files,
                        query=retrieval_query,
                        top_k=args.top_k,
                        chunk_max_chars=args.chunk_max_chars,
                        chunk_overlap_chars=args.chunk_overlap_chars,
                    )
                    context = build_retrieved_context(retrieved, max_chars=args.enhanced_max_chars)
                    await store.append_artifact(
                        {"run_id": run_id, "type": "retrieval_stats", "retrieval": retrieval_stats}
                    )

            resp = await _fireworks_code_change(
                fw=fw,
                prompt=prompt,
                context=context,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )

            written: list[str] = []
            parse_ok = True
            parse_err = ""
            try:
                written = _apply_model_files(workdir, resp["text"])
            except Exception as e:
                parse_ok = False
                parse_err = str(e)

            test_ok = True
            test_out = ""
            test_rc = 0
            if parse_ok and isinstance(test_command, str) and test_command.strip():
                test_rc, test_out = _run_test_command(
                    test_command,
                    cwd=workdir,
                    extra_env={"PYTHONPATH": "src"},
                )
                test_ok = test_rc == 0

            asserts_ok, asserts_reason = _assertions_ok(assertions, workdir=workdir)

            ok = parse_ok and test_ok and asserts_ok
            reason = "ok"
            if not parse_ok:
                reason = f"model_output_parse_failed: {parse_err}"
            elif not test_ok:
                reason = f"tests_failed (rc={test_rc})"
            elif not asserts_ok:
                reason = f"assertions_failed: {asserts_reason}"

            await store.append_artifact(
                {
                    "run_id": run_id,
                    "type": "phase_result",
                    "phase_id": phase.get("id"),
                    "written_files": written,
                    "parse_ok": parse_ok,
                    "parse_error": parse_err,
                    "test_command": test_command,
                    "test_rc": test_rc,
                    "test_output": test_out[-20_000:],
                    "usage": resp["usage"],
                    "latency_ms": resp["latency_ms"],
                    "model": resp["model"],
                }
            )

            triad = local_rag_triad(retrieval_query, resp["text"], context)
            await store.append_eval_result(
                {
                    "run_id": run_id,
                    "phase_id": phase.get("id"),
                    "ok": ok,
                    "reason": reason,
                    "triad": triad,
                }
            )

            await galileo.log_workflow(
                name=f"{case_id}:{mode}:{phase.get('id')}",
                input_text=prompt,
                output_text=resp["text"][:20_000],
                metadata={
                    "suite": "regression",
                    "mode": mode,
                    "case_id": case_id,
                    "phase_id": phase.get("id"),
                    "run_id": run_id,
                    "ok": ok,
                    "reason": reason,
                    "usage": resp["usage"],
                },
            )

            return {
                "phase_id": phase.get("id"),
                "ok": ok,
                "reason": reason,
                "usage": resp["usage"],
                "latency_ms": resp["latency_ms"],
                "written_files": written,
            }

        # Execute phases
        if kind == "multi_phase":
            phases: list[dict[str, Any]] = case.get("phases") or []
            if not phases:
                await store.update_run(
                    run_id,
                    {
                        "completed_at_ms": now_ms(),
                        "metrics": {"ok": False, "reason": "no phases", "phases": []},
                    },
                )
                return {"run_id": run_id, "case_id": case_id, "ok": False, "reason": "no phases"}

            # Phase 1
            r1 = await do_phase(phases[0])

            # Build a tiny handoff pack (stored as artifact) for resume phase
            handoff_pack = json_dumps(
                {
                    "case_id": case_id,
                    "phase_id": r1["phase_id"],
                    "ok": r1["ok"],
                    "reason": r1["reason"],
                    "written_files": r1["written_files"],
                }
            )
            await store.append_artifact({"run_id": run_id, "type": "handoff_pack", "content": handoff_pack})

            # Phase 2 (resume): enhanced uses handoff pack as the primary context
            r2 = await do_phase(phases[1], handoff_context=handoff_pack if mode == "enhanced" else None)
            ok = bool(r1["ok"] and r2["ok"])

            phase_summaries = [r1, r2]
            total_tokens = sum(int(p["usage"]["total_tokens"]) for p in phase_summaries)
            total_latency_ms = sum(float(p["latency_ms"]) for p in phase_summaries)
            await store.update_run(
                run_id,
                {
                    "completed_at_ms": now_ms(),
                    "metrics": {
                        "ok": ok,
                        "reason": "ok" if ok else "phase_failed",
                        "phase_count": len(phase_summaries),
                        "total_tokens": total_tokens,
                        "total_latency_ms": total_latency_ms,
                        "phases": phase_summaries,
                    },
                },
            )
            return {"run_id": run_id, "case_id": case_id, "case_name": name, "mode": mode, "ok": ok, "phases": [r1, r2]}

        # Single phase
        phase = {
            "id": case_id,
            "prompt": case.get("prompt"),
            "retrieval_query": case.get("retrieval_query"),
            "test_command": case.get("test_command"),
            "assertions": case.get("assertions") or [],
        }
        r = await do_phase(phase)
        await store.update_run(
            run_id,
            {
                "completed_at_ms": now_ms(),
                "metrics": {
                    "ok": bool(r["ok"]),
                    "reason": r.get("reason", ""),
                    "phase_count": 1,
                    "total_tokens": int(r["usage"]["total_tokens"]),
                    "total_latency_ms": float(r["latency_ms"]),
                    "phases": [r],
                },
            },
        )
        return {"run_id": run_id, "case_id": case_id, "case_name": name, "mode": mode, "ok": r["ok"], "phases": [r]}

    finally:
        # Keep temp dir only when debugging (opt-in)
        if os.environ.get("CCV3_EVAL_KEEP_SANDBOX") != "1":
            import shutil

            shutil.rmtree(workdir, ignore_errors=True)


async def main() -> int:
    args = _parse_args()
    suite: Suite = args.suite

    store = AtlasEvalStore()
    await store.connect()

    fw = FireworksChatClient()
    galileo = GalileoObserveClient()

    try:
        config = _load_yaml(_cases_path(suite))
        cases: list[dict[str, Any]] = config.get("cases") or []
        if args.case != "all":
            cases = [c for c in cases if c.get("id") == args.case]
        if not cases:
            print("No cases selected.")
            return 1

        modes: list[Mode]
        if args.mode == "both":
            modes = ["baseline", "enhanced"]
        else:
            modes = [args.mode]

        results: list[dict[str, Any]] = []

        if suite == "benchmark":
            for c in cases:
                await store.upsert_task({"task_id": c.get("id"), "suite": "benchmark", "case": c})
                for m in modes:
                    results.append(await run_benchmark_case(case=c, mode=m, args=args, store=store, fw=fw, galileo=galileo))

        else:
            fixture_root_name = config.get("fixture_root") or "toy_repo"
            fixture_root = _fixture_root(fixture_root_name)
            for c in cases:
                await store.upsert_task({"task_id": c.get("id"), "suite": "regression", "case": c})
                for m in modes:
                    results.append(
                        await run_regression_case(
                            case=c, mode=m, args=args, store=store, fw=fw, galileo=galileo, fixture_root=fixture_root
                        )
                    )

        # Print summary
        print(json_dumps({"suite": suite, "mode": args.mode, "results": results}))

        # Token reduction summary for pairs
        if args.mode == "both" and suite == "benchmark":
            by_case: dict[str, dict[str, Any]] = {}
            for r in results:
                cid = r["case_id"]
                by_case.setdefault(cid, {})
                by_case[cid][r["mode"]] = r

            reductions = []
            for cid, pair in by_case.items():
                if "baseline" not in pair or "enhanced" not in pair:
                    continue
                b = pair["baseline"]["usage"]["total_tokens"]
                e = pair["enhanced"]["usage"]["total_tokens"]
                if b:
                    reductions.append((cid, (b - e) / b))

            if reductions:
                overall = sum(x[1] for x in reductions) / len(reductions)
                print("\n=== Token Reduction Summary (benchmark) ===")
                for cid, frac in reductions:
                    print(f"- {cid}: {frac*100:.1f}%")
                print(f"- OVERALL: {overall*100:.1f}%")

        return 0

    finally:
        await fw.close()
        await galileo.close()
        await store.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

