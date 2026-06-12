"""Conditional edge functions for the LangGraph pipeline."""
from __future__ import annotations
import structlog

logger = structlog.get_logger()

MAX_RETRIEVAL_ATTEMPTS = 5   # increased from 3 to give more chances to reach 50
MIN_CANDIDATES_REQUIRED = 50


def should_retry_retrieval(state: dict) -> str:
    """
    After verify_pi_node, check if we have enough candidates.

    Uses validated_shortlist count (post country-filter, post evidence-check)
    as the true measure of usable candidates. Falls back to scored_candidates
    if validate hasn't run yet on this loop iteration.

    Retries up to MAX_RETRIEVAL_ATTEMPTS times if below MIN_CANDIDATES_REQUIRED.
    """
    # Use the most-filtered count available as a signal
    validated_count = len(state.get("validated_shortlist") or [])
    scored_count = len(state.get("scored_candidates") or [])
    resolved_count = len(state.get("resolved_candidates") or [])

    # Best estimate of how many valid supervisors we actually have
    # (validated > scored > resolved, each progressively less filtered)
    usable = validated_count or scored_count or resolved_count
    attempts = state.get("retrieval_attempts", 0)

    if usable < MIN_CANDIDATES_REQUIRED and attempts < MAX_RETRIEVAL_ATTEMPTS:
        logger.warning(
            "retry_retrieval",
            usable_candidates=usable,
            validated=validated_count,
            scored=scored_count,
            resolved=resolved_count,
            attempt=attempts,
            max_attempts=MAX_RETRIEVAL_ATTEMPTS,
        )
        return "retrieve_node"

    if usable < MIN_CANDIDATES_REQUIRED:
        logger.warning(
            "proceeding_with_low_candidates",
            usable_candidates=usable,
            reason="max_retries_exhausted",
        )

    logger.info("proceeding_to_score", usable_candidates=usable)
    return "score_node"
