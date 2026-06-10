"""score_node: Embedding similarity + confidence breakdown scoring.
Phase 1 stub: Passes candidates through with default scores. Phase 2: Real scoring."""
from __future__ import annotations
import structlog
from graph.state import ShortlistState

logger = structlog.get_logger()


async def score_node(state: ShortlistState) -> dict:
    """Score candidates by embedding similarity and multi-signal confidence."""
    candidates = state["resolved_candidates"]
    logger.info("score_node_start", candidates_in=len(candidates))

    # Phase 1 stub — pass through with default score
    # Phase 2: ChromaDB similarity + confidence breakdown
    scored = []
    for i, c in enumerate(candidates):
        c_copy = dict(c)
        c_copy["confidence_score"] = 0.5
        c_copy["rank"] = i + 1
        scored.append(c_copy)

    # Sort by confidence (descending) for downstream nodes
    scored.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)

    logger.info("score_node_complete", candidates_scored=len(scored))

    return {"scored_candidates": scored}
