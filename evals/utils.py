from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


def now_ns() -> int:
    # Python 3.7+: time.time_ns exists, but avoid importing time in hot paths elsewhere
    import time

    return time.time_ns()


def now_ms() -> int:
    return now_ns() // 1_000_000


def read_text(path: Path, *, max_chars: int | None = None) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + "\n\n…(truncated)…\n"
    return text


def safe_relpath(path: str) -> str:
    """Normalize and reject path traversal for model-proposed file writes."""
    norm = path.replace("\\", "/").strip()
    norm = re.sub(r"^/+", "", norm)  # strip absolute prefixes
    if norm.startswith("..") or "/../" in norm or norm == "..":
        raise ValueError(f"Disallowed path traversal: {path!r}")
    return norm


def write_text(root: Path, rel_path: str, content: str) -> Path:
    rel_path = safe_relpath(rel_path)
    full = (root / rel_path).resolve()
    if not str(full).startswith(str(root.resolve())):
        raise ValueError(f"Refusing to write outside sandbox root: {rel_path}")
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return full


def copy_tree(src: Path) -> Path:
    """Copy a fixture directory to a temp working dir and return the new path."""
    dst = Path(tempfile.mkdtemp(prefix="ccv3_eval_"))
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return dst


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    file_path: str
    text: str
    start_line: int | None = None
    end_line: int | None = None
    metadata: dict[str, Any] | None = None


def chunk_file_text(
    file_path: str,
    text: str,
    *,
    max_chars: int = 1200,
    overlap_chars: int = 150,
) -> list[Chunk]:
    """Chunk text into overlapping windows (simple, deterministic)."""
    chunks: list[Chunk] = []
    if not text:
        return chunks

    i = 0
    n = len(text)
    idx = 0
    while i < n:
        j = min(n, i + max_chars)
        chunk_text = text[i:j]
        chunk_id = f"{file_path}::chunk-{idx}"
        chunks.append(Chunk(chunk_id=chunk_id, file_path=file_path, text=chunk_text))
        idx += 1
        if j >= n:
            break
        i = max(0, j - overlap_chars)
    return chunks


def build_baseline_context(files: Iterable[tuple[str, str]], *, max_chars: int = 80_000) -> str:
    """Concatenate raw files for a baseline prompt context."""
    parts: list[str] = []
    total = 0
    for rel_path, content in files:
        header = f"\n\n=== FILE: {rel_path} ===\n"
        piece = header + content
        if total + len(piece) > max_chars:
            remaining = max(0, max_chars - total)
            parts.append(piece[:remaining] + "\n\n…(baseline context truncated)…\n")
            break
        parts.append(piece)
        total += len(piece)
    return "".join(parts).strip()


def build_retrieved_context(chunks: list[dict[str, Any]], *, max_chars: int = 20_000) -> str:
    """Render retrieved chunks into a compact context block."""
    parts: list[str] = []
    total = 0
    for item in chunks:
        rel_path = item.get("file_path") or item.get("metadata", {}).get("file_path") or "unknown"
        score = item.get("score")
        header = f"\n\n--- RETRIEVED: {rel_path} (score={score}) ---\n"
        text = item.get("text") or item.get("content") or ""
        piece = header + text
        if total + len(piece) > max_chars:
            remaining = max(0, max_chars - total)
            parts.append(piece[:remaining] + "\n\n…(retrieved context truncated)…\n")
            break
        parts.append(piece)
        total += len(piece)
    return "".join(parts).strip()


MODEL_OUTPUT_SCHEMA_HINT = {
    "files": [
        {"path": "relative/path/from/project/root.py", "content": "full file content here"}
    ]
}


def render_json_only_system_prompt() -> str:
    """A strict system prompt that makes parsing deterministic."""
    return (
        "You are an expert software engineer. "
        "Return ONLY a single JSON object and nothing else. "
        "No markdown, no backticks, no explanations. "
        "The JSON must match this schema:\n"
        f"{json_dumps(MODEL_OUTPUT_SCHEMA_HINT)}\n"
        "If you are not confident, still return JSON with an empty files list: {\"files\": []}."
    )

