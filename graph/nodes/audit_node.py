import logging
from typing import Dict, Any, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _domain_from_url(url: str) -> str:
    try:
        p = urlparse(url)
        return p.hostname or ""
    except Exception:
        return ""


async def audit_node(state: Dict[str, Any], top_n: int = 60) -> Dict[str, Any]:
    """Perform a lightweight contamination self-audit on the top-N candidates.

    Signals checked (basic heuristics):
    - evidence_domain_mismatch: evidence source domains do not match supervisor institution domain
    - duplicate_name: multiple candidates with same supervisor name in top-N
    - low_confidence: candidate confidence < 0.4
    - missing_pi_verified: supervisor.is_pi_verified is False or None

    Adds `contamination_risk` list to each flagged candidate and writes `audit_summary`.

    NOTE: candidates are flat dicts at this stage — `supervisor` sub-object only exists
    in the final JSON built by output_node. Fields like `name`, `institution`, `country`
    are top-level keys.
    """
    scored = state.get("scored_candidates") or state.get("validated_shortlist") or []
    if not scored:
        state.setdefault("audit_summary", {})
        return state

    # consider top_n by rank if present, else first N
    sorted_candidates = sorted(scored, key=lambda x: x.get("rank", 9999))
    top = sorted_candidates[:top_n]

    # build name frequency map (using flat-dict `name` field)
    name_counts: Dict[str, int] = {}
    for c in top:
        sup = c.get("supervisor") or {}
        name = c.get("name") or sup.get("name") or ""
        name_counts[name] = name_counts.get(name, 0) + 1

    flagged: List[Dict[str, Any]] = []
    for c in top:
        reasons: List[str] = []
        # Candidates in the real pipeline are flat dicts; test fixtures may use nested `supervisor`.
        sup = c.get("supervisor") or {}
        name = c.get("name") or sup.get("name") or ""
        inst = (c.get("institution") or sup.get("institution") or "").lower()
        is_pi_verified = c.get("is_pi_verified", sup.get("is_pi_verified"))

        # duplicate name
        if name and name_counts.get(name, 0) > 1:
            reasons.append("duplicate_name")

        # low confidence
        conf = c.get("confidence") or c.get("confidence_score") or 0.0
        if conf < 0.4:
            reasons.append("low_confidence")

        # missing PI verification
        if is_pi_verified is not True:
            reasons.append("missing_pi_verified")

        # evidence domain mismatch heuristic
        evidence = c.get("evidence") or c.get("papers") or []
        mismatch_found = False
        for e in evidence:
            url = e.get("url") or e.get("doi") or ""
            domain = _domain_from_url(url).lower()
            if domain and inst and (inst.replace(' ', '') not in domain):
                mismatch_found = True
        if mismatch_found:
            reasons.append("evidence_domain_mismatch")

        if reasons:
            c["contamination_risk"] = reasons
            flagged.append({"id": c.get("id") or name, "reasons": reasons})

    state["audit_summary"] = {
        "top_n": len(top),
        "flagged_count": len(flagged),
        "flagged": flagged,
    }
    logger.info("audit_node_complete", **state["audit_summary"]) if logger else None
    return {
        "audited_shortlist": top,
        "audit_summary": state["audit_summary"]
    }
