"""validate_node: Quality gates — country filter, evidence check, schema validation.
Phase 1 stub: Passes all candidates. Phase 2: Hard constraint enforcement."""
from __future__ import annotations
import structlog
from graph.state import ShortlistState

logger = structlog.get_logger()


async def validate_node(state: ShortlistState) -> dict:
    """Apply quality gates: country adherence, evidence, schema checks."""
    candidates = state["enriched_candidates"]
    countries = state["target_countries"]
    logger.info("validate_node_start", candidates_in=len(candidates), target_countries=countries)

    # Phase 1 stub — hard country filter only (this MUST work from day 1)
    validated = []
    country_rejected = 0

    for c in candidates:
        c_country = c.get("country", "")
        if countries and c_country and c_country not in countries:
            country_rejected += 1
            continue
        validated.append(c)

    logger.info(
        "validate_node_complete",
        candidates_out=len(validated),
        country_rejected=country_rejected,
    )

    return {"validated_shortlist": validated}
