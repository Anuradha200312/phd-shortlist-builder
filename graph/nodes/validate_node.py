import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


async def validate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate enriched candidates against hard constraints.

    - Enforces country hard constraint (must be in `target_countries`).
    - Ensures each candidate has at least one piece of `evidence`.
    - Produces `validated_shortlist` in state.

    NOTE: candidates are flat dicts at this stage; the nested `supervisor`
    sub-object only exists in the final output built by output_node.
    """
    enriched: List[Dict[str, Any]] = state.get("enriched_candidates", []) or []
    target_countries = state.get("target_countries") or []

    validated = []
    blocked_by_country = 0
    blocked_by_evidence = 0

    for c in enriched:
        # Candidates in the real pipeline are flat dicts; some test fixtures
        # use a nested `supervisor` sub-dict. Support both.
        sup = c.get("supervisor") or {}
        country = c.get("country") or sup.get("country")

        if target_countries:
            # Hard constraint: country must be explicitly in target list.
            # Unknown/missing country is treated as a fail — we can't confirm eligibility.
            if not country or country not in target_countries:
                blocked_by_country += 1
                continue

        evidence = c.get("evidence") or c.get("papers") or c.get("grants") or []
        if not evidence:
            blocked_by_evidence += 1
            continue
        c["evidence"] = evidence

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
