"""audit_node: Contamination self-audit on top-30 shortlist entries.
Phase 1 stub: Passes all candidates through. Phase 3: Full audit rules."""
from __future__ import annotations
import structlog
from graph.state import ShortlistState

logger = structlog.get_logger()


async def audit_node(state: ShortlistState) -> dict:
    """Self-audit the top-30 for contamination risk before output."""
    shortlist = state["validated_shortlist"]
    logger.info("audit_node_start", candidates_in=len(shortlist))

    # Phase 1 stub — pass through, no audit
    # Phase 3: CONTAMINATION_RISK_RULES applied to top-30
    audit_summary = {
        "total_audited": len(shortlist),
        "clean": len(shortlist),
        "flagged": 0,
        "tier_downgraded": 0,
        "removed": 0,
    }

    logger.info("audit_node_complete", **audit_summary)

    return {
        "audited_shortlist": list(shortlist),
        "audit_summary": audit_summary,
    }
