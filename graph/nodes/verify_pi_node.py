"""verify_pi_node: Career-stage verification with faculty directory hard gate.
Phase 1 stub: Passes all candidates. Phase 2: Rule-based + faculty dir + LLM."""
from __future__ import annotations
import structlog
from graph.state import ShortlistState

logger = structlog.get_logger()


async def verify_pi_node(state: ShortlistState) -> dict:
    """Verify candidates are faculty PIs, not students or postdocs."""
    candidates = state["resolved_candidates"]
    logger.info("verify_pi_node_start", candidates_in=len(candidates))

    # Phase 1 stub — pass everything through
    # Phase 2: rule_based_pi_check → staleness check → faculty dir → LLM verify
    verified = list(candidates)

    logger.info("verify_pi_node_complete", candidates_out=len(verified))

    return {"resolved_candidates": verified}
