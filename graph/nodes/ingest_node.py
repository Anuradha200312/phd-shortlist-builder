"""
ingest_node: Parses student profile and expands search queries via LangChain.
Phase 1: Stub that returns raw research interests as queries.
Phase 2: Full LLM query expansion chain.
"""
from __future__ import annotations
import structlog
from graph.state import ShortlistState

logger = structlog.get_logger()


from chains.query_expansion_chain import expand_queries

async def ingest_node(state: ShortlistState) -> dict:
    """Parse student profile and generate search queries."""
    profile = state["student_profile"]
    logger.info("ingest_node_start", student_id=profile.get("student_id"))

    # Call LLM query expansion chain
    queries = await expand_queries(profile)

    # Fallback/merge with raw interests if empty
    if not queries:
        interests = profile.get("research_interests", [])
        education = profile.get("education", [])
        thesis_titles = [e.get("thesis_title", "") for e in education if e.get("thesis_title")]
        queries = list(set(interests + thesis_titles))[:15]

    logger.info("ingest_node_complete", queries_generated=len(queries))

    return {
        "search_queries": queries,
        "run_start_time": __import__("datetime").datetime.utcnow().isoformat(),
    }
