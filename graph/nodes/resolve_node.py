"""resolve_node: Entity resolution (3-Signal Lock) + two-layer domain check.
Phase 1 stub: Passes all candidates through. Phase 2: Real disambiguation."""
from __future__ import annotations
import structlog
from graph.state import ShortlistState

logger = structlog.get_logger()


async def resolve_node(state: ShortlistState) -> dict:
    """Disambiguate candidates and filter wrong-domain entries."""
    raw = state["raw_candidates"]
    logger.info("resolve_node_start", candidates_in=len(raw))

    # Phase 1 stub — pass everything through
    # Phase 2: 3-Signal Lock + keyword blacklist + LLM domain check
    resolved = list(raw)

    logger.info("resolve_node_complete", candidates_out=len(resolved))

    return {
        "resolved_candidates": resolved,
        "disambiguation_results": {},
        "domain_blacklist_blocked": 0,
        "domain_llm_checked": 0,
    }
