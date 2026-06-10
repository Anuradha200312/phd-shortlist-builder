"""
Lightweight ChromaDB stub for local development.

This module provides a minimal interface expected by the pipeline: `query_similarity`
that returns an embedding similarity score in 0.0-1.0. It uses the embedder heuristics
when no real vector DB is configured.
"""
from __future__ import annotations
from typing import Dict

from .embedder import compute_candidate_similarity
from .embedder import get_embedding, get_text_for_candidate, cosine_similarity
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from chromadb.utils import embedding_functions
    _CHROMA_AVAILABLE = True
except Exception:
    chromadb = None
    _CHROMA_AVAILABLE = False


class ChromaStore:
    def __init__(self, index_path: str | None = None):
        self.index_path = index_path
        self.client = None
        self.collection = None
        if _CHROMA_AVAILABLE:
            try:
                self.client = chromadb.Client(ChromaSettings(chroma_db_impl="duckdb+parquet", persist_directory=index_path))
            except Exception:
                self.client = chromadb.Client()

    def ensure_collection(self, name: str = "supervisors"):
        if not _CHROMA_AVAILABLE:
            return None
        if self.collection is None:
            try:
                self.collection = self.client.get_or_create_collection(name=name)
            except Exception:
                self.collection = self.client.create_collection(name=name)
        return self.collection

    async def index_candidates(self, candidates: list[Dict], model_name: str = "all-MiniLM-L6-v2") -> None:
        """Index candidate embeddings into Chroma when available.

        This is a best-effort async function; failures are non-fatal and logged.
        """
        if not _CHROMA_AVAILABLE:
            return
        coll = self.ensure_collection()
        if coll is None:
            return

        ids = []
        metadatas = []
        documents = []
        embeddings = []

        for c in candidates:
            cid = c.get("id") or c.get("supervisor", {}).get("semantic_scholar_id") or c.get("supervisor", {}).get("id")
            text = get_text_for_candidate(c)
            emb = get_embedding(text, model_name=model_name)
            if emb is None:
                continue
            ids.append(cid)
            metadatas.append({"rank": c.get("rank"), "name": c.get("supervisor", {}).get("name")})
            documents.append(text)
            embeddings.append(emb)

        if not ids:
            return

        try:
            coll.add(ids=ids, metadatas=metadatas, documents=documents, embeddings=embeddings)
            if self.index_path:
                try:
                    self.client.persist()
                except Exception:
                    pass
        except Exception:
            return

    async def _compute_similarity_via_embeddings(self, candidate: Dict, student_profile: Dict) -> float:
        # Build text for candidate and student interests
        cand_text = get_text_for_candidate(candidate)
        student_text = " ".join(student_profile.get("research_interests", []) or [])

        cand_vec = get_embedding(cand_text)
        stu_vec = get_embedding(student_text)
        if cand_vec is None or stu_vec is None:
            return -1.0
        return cosine_similarity(cand_vec, stu_vec)

    async def query_similarity(self, candidate: Dict, student_profile: Dict) -> float:
        # Prefer real embeddings when available
        try:
            emb_sim = await self._compute_similarity_via_embeddings(candidate, student_profile)
            if emb_sim is not None and emb_sim >= 0.0:
                return emb_sim
        except Exception:
            pass

        # Fallback to deterministic overlap heuristic
        return compute_candidate_similarity(candidate, student_profile)


# Singleton accessor for simple use
_store: ChromaStore | None = None

def get_chroma_store(index_path: str | None = None) -> ChromaStore:
    global _store
    if _store is None:
        _store = ChromaStore(index_path=index_path)
    return _store
