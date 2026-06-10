"""retrieve_node: Fetches candidates from data source APIs in parallel.
Phase 1 stub: Returns empty list. Phase 2: Real API calls."""
from __future__ import annotations
import structlog
from graph.state import ShortlistState

logger = structlog.get_logger()


async def retrieve_node(state: ShortlistState) -> dict:
    """Fetch supervisor candidates from all data sources."""
    queries = state["search_queries"]
    countries = state["target_countries"]
    attempt = state["retrieval_attempts"]

    logger.info(
        "retrieve_node_start",
        queries=len(queries),
        countries=countries,
        attempt=attempt + 1,
    )

    # Phase 1 stub — returns empty candidates
    # Phase 2 will call: semantic_scholar, openalex, nih_reporter, ukri, findhaphd
    raw_candidates = []
    sources_used = []

    logger.info("retrieve_node_complete", candidates_fetched=len(raw_candidates))

    return {
        "raw_candidates": state.get("raw_candidates", []) + raw_candidates,
        "retrieval_attempts": attempt + 1,
        "data_sources_used": list(set(state.get("data_sources_used", []) + sources_used)),
    }
