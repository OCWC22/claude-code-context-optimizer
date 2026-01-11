"""Voyage AI Embeddings - voyage-3 Model.

Voyage AI provides high-quality embeddings optimized for retrieval.
Uses input_type="document" for storage and input_type="query" for search.

Sponsor: Voyage AI (replacing Jina AI)
Docs: https://docs.voyageai.com/docs/embeddings

Usage:
    embeddings = VoyageEmbeddings()

    # For documents/passages (stored in Atlas)
    doc_emb = await embeddings.embed("def calculate_total()...", input_type="document")

    # For queries (used for search)
    query_emb = await embeddings.embed("find total calculation", input_type="query")
"""

import os
from typing import Literal

import httpx

# Voyage AI input types
VoyageInputType = Literal[
    "query",      # For search queries
    "document",   # For documents being indexed
]


class VoyageEmbeddings:
    """Voyage AI Embeddings client (voyage-3 model).

    Features:
    - voyage-3: 1024 dimensions, optimized for retrieval
    - Input type support: query vs document
    - Batch embedding support
    """

    API_URL = "https://api.voyageai.com/v1/embeddings"
    MODEL = "voyage-3"
    DIMENSIONS = 1024

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "voyage-3",
    ):
        self.api_key = api_key or os.environ.get("VOYAGE_API_KEY")
        self.model = model
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def embed(
        self,
        text: str | list[str],
        input_type: VoyageInputType = "document",
        max_retries: int = 5,
    ) -> list[float] | list[list[float]]:
        """Generate embeddings with Voyage AI.

        Args:
            text: Single text or list of texts
            input_type: "query" for search queries, "document" for indexed content
            max_retries: Number of retries on rate limit

        Returns:
            Embedding vector(s) - 1024 dimensions
        """
        import asyncio
        
        if not self.api_key:
            raise ValueError("Set VOYAGE_API_KEY environment variable")

        client = await self._get_client()

        texts = [text] if isinstance(text, str) else text

        for attempt in range(max_retries):
            response = await client.post(
                self.API_URL,
                json={
                    "model": self.model,
                    "input": texts,
                    "input_type": input_type,
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            
            if response.status_code == 429:
                wait_time = (2 ** attempt) * 5  # 5, 10, 20, 40, 80 seconds
                print(f"  Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(wait_time)
                continue
            
            response.raise_for_status()
            break
        else:
            response.raise_for_status()  # Final attempt failed

        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]

        # Return single embedding if single text input
        if isinstance(text, str):
            return embeddings[0]
        return embeddings

    async def embed_for_search(
        self,
        query: str,
    ) -> list[float]:
        """Embed a search query (uses input_type="query")."""
        return await self.embed(query, input_type="query")

    async def embed_for_storage(
        self,
        content: str | list[str],
    ) -> list[float] | list[list[float]]:
        """Embed content for storage (uses input_type="document")."""
        return await self.embed(content, input_type="document")

    async def embed_batch(
        self,
        texts: list[str],
        input_type: VoyageInputType = "document",
        batch_size: int = 128,
    ) -> list[list[float]]:
        """Embed texts in batches.

        Voyage AI supports up to 128 texts per request.
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = await self.embed(batch, input_type=input_type)
            if isinstance(embeddings[0], list):
                all_embeddings.extend(embeddings)
            else:
                all_embeddings.append(embeddings)

        return all_embeddings


class LocalEmbeddings:
    """Fallback to local embeddings.

    Tries sentence-transformers first, then falls back to hash-based
    pseudo-embeddings for testing/demo purposes.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dimensions: int = 1024):
        self.model_name = model_name
        self.dimensions = dimensions
        self._model = None
        self._use_hash = False

    def _get_model(self):
        if self._model is None and not self._use_hash:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                self._use_hash = True
        return self._model

    def _hash_embed(self, text: str) -> list[float]:
        """Generate pseudo-embedding from text hash.

        NOT for production - use for testing/demo only.
        Creates deterministic embeddings that preserve some similarity.
        """
        import hashlib
        import math

        # Normalize text
        text = text.lower().strip()

        # Create multiple hashes from different offsets
        embedding = []
        for i in range(self.dimensions):
            h = hashlib.md5(f"{text}_{i}".encode()).hexdigest()
            # Convert hex to float in [-1, 1]
            val = (int(h[:8], 16) / 0xFFFFFFFF) * 2 - 1
            embedding.append(val)

        # Normalize to unit vector
        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    async def embed(
        self,
        text: str | list[str],
        input_type: str = "document",  # Ignored for local
    ) -> list[float] | list[list[float]]:
        """Generate embeddings locally."""
        self._get_model()  # Try to load model

        if self._use_hash:
            # Hash-based fallback
            if isinstance(text, str):
                return self._hash_embed(text)
            return [self._hash_embed(t) for t in text]

        # Use sentence-transformers
        if isinstance(text, str):
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding.tolist()

        embeddings = self._model.encode(text, convert_to_numpy=True)
        return [e.tolist() for e in embeddings]

    async def close(self):
        pass


class EmbeddingsRouter:
    """Routes to Voyage AI or local fallback based on availability."""

    def __init__(self):
        if os.environ.get("VOYAGE_API_KEY"):
            self._provider = VoyageEmbeddings()
            self.provider_name = "voyage-3"
        else:
            self._provider = LocalEmbeddings()
            self.provider_name = "local"

    async def embed(
        self,
        text: str | list[str],
        input_type: VoyageInputType = "document",
    ) -> list[float] | list[list[float]]:
        return await self._provider.embed(text, input_type=input_type)

    async def embed_for_search(self, query: str) -> list[float]:
        return await self.embed(query, input_type="query")

    async def embed_for_storage(self, content: str | list[str]) -> list[float] | list[list[float]]:
        return await self.embed(content, input_type="document")

    async def embed_batch(
        self,
        texts: list[str],
        input_type: VoyageInputType = "document",
        batch_size: int = 128,
    ) -> list[list[float]]:
        """Embed texts in batches (forwards to underlying provider)."""
        if hasattr(self._provider, "embed_batch"):
            return await self._provider.embed_batch(texts, input_type, batch_size)
        # Fallback for LocalEmbeddings which doesn't have embed_batch
        result = []
        for text in texts:
            emb = await self.embed(text, input_type=input_type)
            result.append(emb if isinstance(emb, list) else [emb])
        return result

    async def close(self):
        await self._provider.close()
