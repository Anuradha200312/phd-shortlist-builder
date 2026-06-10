"""enrich_node: why_match generation + eligibility extraction.
Phase 1 stub: Sets placeholder why_match. Phase 2: LLM chains."""
from __future__ import annotations
import structlog
from graph.state import ShortlistState

logger = structlog.get_logger()


async def enrich_node(state: ShortlistState) -> dict:
    """Generate why_match blurbs and extract eligibility flags."""
    candidates = state["scored_candidates"]
    logger.info("enrich_node_start", candidates_in=len(candidates))

    # Phase 1 stub — placeholder why_match
    # Phase 2: why_match_chain.abatch() + eligibility_chain
    enriched = []
    for c in candidates:
        c_copy = dict(c)
        c_copy["why_match"] = f"Placeholder: {c.get('name', 'Unknown')} is a potential match."
        c_copy["eligibility_flags"] = []
        enriched.append(c_copy)

    logger.info("enrich_node_complete", candidates_enriched=len(enriched))

    return {
        "enriched_candidates": enriched,
        "llm_provider_used": "stub",
    }
