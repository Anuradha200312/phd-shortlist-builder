"""
ingest_node: Parses student profile and expands search queries via LangChain.
Phase 1: Stub that returns raw research interests as queries.
Phase 2: Full LLM query expansion chain.
"""
from __future__ import annotations
import structlog
from graph.state import ShortlistState

logger = structlog.get_logger()


async def ingest_node(state: ShortlistState) -> dict:
    """Parse student profile and generate search queries."""
    profile = state["student_profile"]
    logger.info("ingest_node_start", student_id=profile.get("student_id"))

    # Phase 1 stub: use raw research interests as queries
    # Phase 2 will replace this with LLM query_expansion_chain
    interests = profile.get("research_interests", [])
    education = profile.get("education", [])
    thesis_titles = [e.get("thesis_title", "") for e in education if e.get("thesis_title")]

    # Combine interests + thesis keywords as initial queries
    queries = list(set(interests + thesis_titles))[:15]

    logger.info("ingest_node_complete", queries_generated=len(queries))

    return {
        "search_queries": queries,
        "run_start_time": __import__("datetime").datetime.utcnow().isoformat(),
    }
