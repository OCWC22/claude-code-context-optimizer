from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


try:
    from motor.motor_asyncio import AsyncIOMotorClient

    HAS_MOTOR = True
except Exception:
    HAS_MOTOR = False


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    denom = math.sqrt(na) * math.sqrt(nb)
    return (dot / denom) if denom else 0.0


@dataclass
class AtlasEvalStoreConfig:
    uri: str | None = None
    db_name: str = "ccv3_evals"
    vector_index: str = "retrieval_vectors"


class AtlasEvalStore:
    """MongoDB Atlas-backed persistence for eval runs.

    Collections:
      - tasks
      - runs
      - artifacts
      - eval_results
      - corpus (chunks + embeddings)
    """

    def __init__(self, config: AtlasEvalStoreConfig | None = None):
        cfg = config or AtlasEvalStoreConfig()
        self.uri = cfg.uri or os.environ.get("MONGODB_URI") or os.environ.get("ATLAS_URI")
        self.db_name = os.environ.get("ATLAS_DB_NAME") or cfg.db_name
        self.vector_index = os.environ.get("ATLAS_VECTOR_INDEX") or cfg.vector_index

        self._client: Any | None = None
        self._db: Any | None = None

        # In-memory fallback for local development / CI without Atlas
        self.is_in_memory = not (HAS_MOTOR and self.uri)
        self._mem: dict[str, list[dict[str, Any]]] = {
            "tasks": [],
            "runs": [],
            "artifacts": [],
            "eval_results": [],
            "corpus": [],
        }

    async def connect(self) -> None:
        if self.is_in_memory:
            return
        self._client = AsyncIOMotorClient(self.uri)
        self._db = self._client[self.db_name]

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
        self._client = None
        self._db = None

    def _coll(self, name: str):
        if self.is_in_memory:
            raise RuntimeError("collection access not available in in-memory mode")
        if self._db is None:
            raise RuntimeError("AtlasEvalStore not connected")
        return self._db[name]

    # ---------------------------------------------------------------------
    # Upserts / Inserts
    # ---------------------------------------------------------------------

    async def upsert_task(self, task: dict[str, Any]) -> str:
        task_id = task.get("task_id") or task.get("id") or str(uuid4())
        doc = {**task, "task_id": task_id}
        if self.is_in_memory:
            self._mem["tasks"] = [t for t in self._mem["tasks"] if t.get("task_id") != task_id]
            self._mem["tasks"].append(doc)
            return task_id

        await self._coll("tasks").update_one({"task_id": task_id}, {"$set": doc}, upsert=True)
        return task_id

    async def create_run(self, run: dict[str, Any]) -> str:
        run_id = run.get("run_id") or str(uuid4())
        doc = {**run, "run_id": run_id}
        if self.is_in_memory:
            self._mem["runs"].append(doc)
            return run_id

        await self._coll("runs").insert_one(doc)
        return run_id

    async def update_run(self, run_id: str, updates: dict[str, Any]) -> None:
        """Update a run document by run_id (best-effort)."""
        if self.is_in_memory:
            for i, r in enumerate(self._mem["runs"]):
                if r.get("run_id") == run_id:
                    self._mem["runs"][i] = {**r, **updates}
                    return
            return

        await self._coll("runs").update_one({"run_id": run_id}, {"$set": updates})

    async def append_artifact(self, artifact: dict[str, Any]) -> str:
        artifact_id = artifact.get("artifact_id") or str(uuid4())
        doc = {**artifact, "artifact_id": artifact_id}
        if self.is_in_memory:
            self._mem["artifacts"].append(doc)
            return artifact_id
        await self._coll("artifacts").insert_one(doc)
        return artifact_id

    async def append_eval_result(self, result: dict[str, Any]) -> str:
        result_id = result.get("result_id") or str(uuid4())
        doc = {**result, "result_id": result_id}
        if self.is_in_memory:
            self._mem["eval_results"].append(doc)
            return result_id
        await self._coll("eval_results").insert_one(doc)
        return result_id

    async def upsert_corpus_chunks(self, *, corpus_id: str, chunks: list[dict[str, Any]]) -> None:
        if self.is_in_memory:
            for c in chunks:
                self._mem["corpus"].append({**c, "corpus_id": corpus_id})
            return

        # Simple bulk insert (idempotency handled by chunk_id uniqueness if index exists)
        docs = [{**c, "corpus_id": corpus_id} for c in chunks]
        if docs:
            await self._coll("corpus").insert_many(docs, ordered=False)

    # ---------------------------------------------------------------------
    # Retrieval
    # ---------------------------------------------------------------------

    async def vector_search(
        self,
        *,
        corpus_id: str,
        query_vector: list[float],
        limit: int = 5,
        num_candidates: int = 50,
    ) -> list[dict[str, Any]]:
        """Vector search over `corpus` by corpus_id.

        - Atlas mode: tries $vectorSearch (requires Atlas Vector Search index)
        - Fallback: cosine over in-memory corpus (or small corpus fetch)
        """

        if self.is_in_memory:
            scored = []
            for doc in self._mem["corpus"]:
                if doc.get("corpus_id") != corpus_id:
                    continue
                vec = doc.get("embedding") or []
                scored.append((float(_cosine(query_vector, vec)), doc))
            scored.sort(key=lambda x: x[0], reverse=True)
            out: list[dict[str, Any]] = []
            for score, doc in scored[:limit]:
                out.append({**doc, "score": score})
            return out

        coll = self._coll("corpus")
        try:
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.vector_index,
                        "path": "embedding",
                        "queryVector": query_vector,
                        "numCandidates": num_candidates,
                        "limit": limit,
                        "filter": {"corpus_id": corpus_id},
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "chunk_id": 1,
                        "file_path": 1,
                        "text": 1,
                        "metadata": 1,
                        "score": {"$meta": "vectorSearchScore"},
                    }
                },
            ]
            return [doc async for doc in coll.aggregate(pipeline)]
        except Exception:
            # Graceful fallback: fetch corpus and cosine-rank locally (small corpora only)
            docs = [doc async for doc in coll.find({"corpus_id": corpus_id}, {"_id": 0})]
            scored = []
            for doc in docs:
                vec = doc.get("embedding") or []
                scored.append((float(_cosine(query_vector, vec)), doc))
            scored.sort(key=lambda x: x[0], reverse=True)
            out: list[dict[str, Any]] = []
            for score, doc in scored[:limit]:
                out.append({**doc, "score": score})
            return out

