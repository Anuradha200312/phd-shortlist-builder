"""
Minimal embedder utilities for testing and local similarity heuristics.

In production this module will wrap HuggingFace or OpenAI embeddings and ChromaDB.
For tests we provide a deterministic overlap-based similarity function.
"""
from __future__ import annotations
from typing import List
import math
from typing import Optional


def _try_import_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer
    except Exception:
        return None


def text_to_tokens(text: str) -> List[str]:
    if not text:
        return []
    tokens = [t.strip().lower() for t in text.split() if t.strip()]
    return tokens


def overlap_similarity(text_a: str, text_b: str) -> float:
    """Return a simple Jaccard-like overlap (0.0-1.0) suitable for tests."""
    a = set(text_to_tokens(text_a))
    b = set(text_to_tokens(text_b))
    if not a or not b:
        return 0.0
    inter = a.intersection(b)
    union = a.union(b)
    return len(inter) / len(union)


def compute_candidate_similarity(candidate: dict, student_profile: dict) -> float:
    """Compute a heuristic similarity between candidate and student's interests.

    Prefers candidate abstracts/title + student research_interests concatenated.
    """
    interests = " ".join(student_profile.get("research_interests", []) or [])
    content = " ".join(filter(None, [candidate.get("title"), candidate.get("abstract")]))
    return overlap_similarity(content, interests)


def get_text_for_candidate(candidate: dict) -> str:
    return " ".join(filter(None, [candidate.get("title"), candidate.get("abstract"), candidate.get("research_areas") and " ".join(candidate.get("research_areas") or [])]))


def get_embedding(text: str, model_name: str = "all-MiniLM-L6-v2") -> Optional[List[float]]:
    """Return embedding vector using sentence-transformers if available, else None."""
    Model = _try_import_sentence_transformer()
    if Model is None:
        return None
    try:
        model = Model(model_name)
        vec = model.encode(text)
        return [float(x) for x in vec]
    except Exception:
        return None


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    cos = dot / (norm_a * norm_b)
    # map from [-1,1] to [0,1]
    return max(0.0, min(1.0, (cos + 1.0) / 2.0))
