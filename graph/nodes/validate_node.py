import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


async def validate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate enriched candidates against hard constraints.

    - Enforces country hard constraint (must be in `target_countries`).
    - Ensures each candidate has at least one piece of `evidence`.
    - Produces `validated_shortlist` in state.
    """
    enriched: List[Dict[str, Any]] = state.get("enriched_candidates", []) or []
    target_countries = state.get("target_countries") or []

    validated = []
    blocked_by_country = 0
    blocked_by_evidence = 0

    for c in enriched:
        sup = c.get("supervisor", {})
        country = sup.get("country")

        if target_countries and country and country not in target_countries:
            blocked_by_country += 1
            continue

        evidence = c.get("evidence") or []
        if not evidence:
            blocked_by_evidence += 1
            continue

        validated.append(c)

    state["validated_shortlist"] = validated
    state["validation_summary"] = {
        "input_count": len(enriched),
        "validated_count": len(validated),
        "blocked_by_country": blocked_by_country,
        "blocked_by_evidence": blocked_by_evidence,
    }

    logger.info("validate_node_complete", **state["validation_summary"]) if logger else None
    return state

"""validate_node: Quality gates — country filter, evidence check, schema validation.
Phase 1 stub: Passes all candidates. Phase 2: Hard constraint enforcement."""

async def validate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate enriched candidates against hard constraints.

    - Enforces country hard constraint (must be in `target_countries`).
    - Ensures each candidate has at least one piece of `evidence`.
    - Produces `validated_shortlist` in state.
    """
    enriched: List[Dict[str, Any]] = state.get("enriched_candidates", []) or []
    target_countries = state.get("target_countries") or []

    validated = []
    blocked_by_country = 0
    blocked_by_evidence = 0

    for c in enriched:
        sup = c.get("supervisor", {})
        country = sup.get("country")

        if target_countries and country and country not in target_countries:
            blocked_by_country += 1
            continue

        evidence = c.get("evidence") or []
        if not evidence:
            blocked_by_evidence += 1
            continue

        validated.append(c)

    state["validated_shortlist"] = validated
    state["validation_summary"] = {
        "input_count": len(enriched),
        "validated_count": len(validated),
        "blocked_by_country": blocked_by_country,
        "blocked_by_evidence": blocked_by_evidence,
    }

    logger.info("validate_node_complete", **state["validation_summary"]) if logger else None
    return state
