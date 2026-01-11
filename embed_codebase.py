#!/usr/bin/env python3
"""Offline Codebase Embedding Script.

Embeds a codebase using Voyage AI and stores embeddings in MongoDB Atlas.
This runs OFFLINE, separate from any online embedding pipeline.

Usage:
    # Embed TuyaOpen WiFi module
    uv run python embed_codebase.py /tmp/tuya-open --repo-id tuya-open

    # Embed current directory
    uv run python embed_codebase.py . --repo-id my-project

    # Embed with specific file patterns
    uv run python embed_codebase.py /path/to/repo --patterns "*.py" "*.ts" "*.js"

Requirements:
    - VOYAGE_API_KEY (for Voyage AI embeddings)
    - MONGODB_URI (for MongoDB Atlas storage)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

load_dotenv()


# Default file patterns to embed
DEFAULT_PATTERNS = [
    "*.py", "*.ts", "*.tsx", "*.js", "*.jsx",
    "*.c", "*.h", "*.cpp", "*.hpp",
    "*.go", "*.rs", "*.java", "*.kt",
    "*.md", "*.txt", "*.yaml", "*.yml", "*.json",
]

# Files/directories to skip
SKIP_PATTERNS = [
    "__pycache__", "node_modules", ".git", ".venv", "venv",
    "dist", "build", ".next", "target", "*.pyc", "*.pyo",
    "*.min.js", "*.min.css", "*.map", "*.lock",
]


def should_skip(path: Path) -> bool:
    """Check if a path should be skipped."""
    path_str = str(path)
    for pattern in SKIP_PATTERNS:
        if pattern in path_str:
            return True
    return False


def find_files(root: Path, patterns: list[str]) -> Iterator[Path]:
    """Find all files matching patterns in root directory."""
    for pattern in patterns:
        for file_path in root.rglob(pattern):
            if file_path.is_file() and not should_skip(file_path):
                yield file_path


def chunk_text(text: str, max_chars: int = 6000, overlap: int = 500) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks


async def embed_codebase(
    root_path: Path,
    repo_id: str,
    patterns: list[str] | None = None,
    batch_size: int = 32,
    max_files: int | None = None,
) -> dict:
    """Embed a codebase and store in MongoDB Atlas.
    
    Args:
        root_path: Root directory of the codebase
        repo_id: Unique identifier for this repository
        patterns: File patterns to match (default: common code files)
        batch_size: Number of texts to embed at once
        max_files: Maximum number of files to embed (None for all)
    
    Returns:
        Summary dict with counts and stats
    """
    from embeddings import EmbeddingsRouter
    from atlas import Atlas
    
    patterns = patterns or DEFAULT_PATTERNS
    
    print(f"Embedding codebase: {root_path}")
    print(f"Repository ID: {repo_id}")
    print(f"Patterns: {patterns}")
    print()
    
    # Initialize services
    embeddings = EmbeddingsRouter()
    print(f"Embeddings provider: {embeddings.provider_name}")
    
    atlas = Atlas()
    await atlas.connect()
    print(f"MongoDB: {'Atlas' if not atlas._in_memory else 'In-memory fallback'}")
    print()
    
    # Collect files
    print("Scanning for files...")
    files = list(find_files(root_path, patterns))
    if max_files:
        files = files[:max_files]
    print(f"Found {len(files)} files to embed")
    print()
    
    # Process files
    stats = {
        "files_processed": 0,
        "files_skipped": 0,
        "chunks_embedded": 0,
        "total_chars": 0,
        "errors": [],
    }
    
    # Prepare all chunks
    all_chunks = []
    chunk_metadata = []
    
    for file_path in files:
        try:
            content = file_path.read_text(errors="ignore")
            if len(content) < 50:  # Skip very small files
                stats["files_skipped"] += 1
                continue
            
            rel_path = str(file_path.relative_to(root_path))
            chunks = chunk_text(content)
            
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                chunk_metadata.append({
                    "file_path": rel_path,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "language": file_path.suffix,
                })
            
            stats["files_processed"] += 1
            stats["total_chars"] += len(content)
            
        except Exception as e:
            stats["files_skipped"] += 1
            stats["errors"].append(f"{file_path}: {e}")
    
    print(f"Prepared {len(all_chunks)} chunks from {stats['files_processed']} files")
    print()
    
    # Embed in batches with retry logic
    print("Embedding chunks...")
    import time as time_module
    
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        batch_meta = chunk_metadata[i:i + batch_size]
        
        # Retry with exponential backoff
        max_retries = 3
        for retry in range(max_retries):
            try:
                # Get embeddings
                batch_embeddings = await embeddings.embed_batch(batch, input_type="document")
                
                # Store each embedding
                for j, (emb, meta) in enumerate(zip(batch_embeddings, batch_meta)):
                    object_id = f"{meta['file_path']}:{meta['chunk_index']}"
                    
                    await atlas.store_embedding(
                        repo_id=repo_id,
                        object_type="file",
                        object_id=object_id,
                        vector=emb,
                        content=batch[j],  # Full content for search
                        metadata=meta,
                    )
                    
                    stats["chunks_embedded"] += 1
                
                print(f"  Embedded {min(i + batch_size, len(all_chunks))}/{len(all_chunks)} chunks")
                break  # Success, exit retry loop
                
            except Exception as e:
                if "429" in str(e) and retry < max_retries - 1:
                    wait_time = (2 ** retry) * 5  # 5, 10, 20 seconds
                    print(f"  Rate limited, waiting {wait_time}s...")
                    time_module.sleep(wait_time)
                else:
                    stats["errors"].append(f"Batch {i}: {e}")
                    print(f"  Error in batch {i}: {e}")
                    break
        
        # Add delay between batches to avoid rate limiting
        time_module.sleep(1)
    
    # Close connections
    await embeddings.close()
    await atlas.close()
    
    # Summary
    print()
    print("="*60)
    print("EMBEDDING COMPLETE")
    print("="*60)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files skipped: {stats['files_skipped']}")
    print(f"Chunks embedded: {stats['chunks_embedded']}")
    print(f"Total characters: {stats['total_chars']:,}")
    print(f"Estimated tokens: {stats['total_chars'] // 4:,}")
    
    if stats["errors"]:
        print(f"\nErrors ({len(stats['errors'])}):")
        for err in stats["errors"][:5]:
            print(f"  - {err}")
        if len(stats["errors"]) > 5:
            print(f"  ... and {len(stats['errors']) - 5} more")
    
    return stats


async def main():
    parser = argparse.ArgumentParser(
        description="Embed a codebase offline using Voyage AI and store in MongoDB Atlas"
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the codebase root directory",
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        required=True,
        help="Unique identifier for this repository",
    )
    parser.add_argument(
        "--patterns",
        nargs="+",
        default=None,
        help="File patterns to match (e.g., '*.py' '*.ts')",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Number of texts to embed at once (default: 8)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Maximum number of files to embed (default: all)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON file for stats",
    )
    
    args = parser.parse_args()
    
    # Validate path
    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}")
        sys.exit(1)
    
    # Check API keys
    if not os.environ.get("VOYAGE_API_KEY"):
        print("Warning: VOYAGE_API_KEY not set - using local embeddings")
    
    if not (os.environ.get("MONGODB_URI") or os.environ.get("ATLAS_URI")):
        print("Warning: MONGODB_URI not set - using in-memory storage")
    
    # Run embedding
    stats = await embed_codebase(
        root_path=args.path.resolve(),
        repo_id=args.repo_id,
        patterns=args.patterns,
        batch_size=args.batch_size,
        max_files=args.max_files,
    )
    
    # Save stats
    if args.output:
        stats["timestamp"] = datetime.now(timezone.utc).isoformat()
        stats["repo_id"] = args.repo_id
        stats["path"] = str(args.path)
        args.output.write_text(json.dumps(stats, indent=2))
        print(f"\nStats saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
