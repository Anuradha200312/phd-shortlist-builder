"""Conditional edge functions for the LangGraph pipeline."""
from __future__ import annotations
import structlog

logger = structlog.get_logger()

MAX_RETRIEVAL_ATTEMPTS = 3
MIN_CANDIDATES_REQUIRED = 50


def should_retry_retrieval(state: dict) -> str:
    """
    After verify_pi_node, check if we have enough candidates.
    If < 50 and haven't exhausted retries, loop back to retrieve_node.
    Otherwise, proceed to score_node.
    """
    candidate_count = len(state.get("resolved_candidates", []))
    attempts = state.get("retrieval_attempts", 0)

    if candidate_count < MIN_CANDIDATES_REQUIRED and attempts < MAX_RETRIEVAL_ATTEMPTS:
        logger.warning(
            "retry_retrieval",
            candidates=candidate_count,
            attempt=attempts,
            max_attempts=MAX_RETRIEVAL_ATTEMPTS,
        )
        return "retrieve_node"

    if candidate_count < MIN_CANDIDATES_REQUIRED:
        logger.warning(
            "proceeding_with_low_candidates",
            candidates=candidate_count,
            reason="max_retries_exhausted",
        )

    logger.info("proceeding_to_score", candidates=candidate_count)
    return "score_node"
