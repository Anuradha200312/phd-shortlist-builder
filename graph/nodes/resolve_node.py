"""
resolve_node: Entity disambiguation using 3-Signal Lock.

Signals:
 - ORCID presence/validity
 - Faculty page confirmation
 - Embedding similarity (if available)

A candidate is considered resolved (linked to a single PI) if at least 2/3
signals are positive. The node also calls the domain check chain to ensure
the candidate is in-scope for the student's interests.
"""
from __future__ import annotations
import re
import structlog
from typing import Dict, List

from graph.state import ShortlistState

# Import chains lazily inside the node to avoid heavy runtime imports during tests
check_domain_two_layer = None

logger = structlog.get_logger()


def _is_valid_orcid(orcid: str) -> bool:
    if not orcid or not isinstance(orcid, str):
        return False
    # Simple ORCID pattern: 0000-0000-0000-0000 (length >= 15 with dashes)
    return bool(re.match(r"^\d{4}-\d{4}-\d{4}-[\dX]{4}$", orcid))


def _embedding_pass(candidate: dict, threshold: float = 0.7) -> bool:
    sim = candidate.get("embedding_similarity")
    try:
        return float(sim) >= threshold
    except Exception:
        return False


async def resolve_node(state: ShortlistState) -> dict:
    """Run 3-Signal Lock across `raw_candidates` and produce `resolved_candidates`.

    Updates:
    - `resolved_candidates` appended with candidates that pass lock
    - `disambiguation_results` mapping candidate_id -> signal booleans
    - `domain_llm_checked` and `domain_blacklist_blocked` counters updated
    """
    raw = state.get("raw_candidates", []) or []
    student_profile = state.get("student_profile", {})

    resolved: List[dict] = []
    disambiguation: Dict[str, dict] = state.get("disambiguation_results", {}) or {}

    bb = state.get("domain_blacklist_blocked", 0)
    llm_checked = state.get("domain_llm_checked", 0)

    for c in raw:
        cid = c.get("id") or c.get("url") or c.get("title")
        orcid_ok = _is_valid_orcid(c.get("orcid"))
        faculty_ok = bool(c.get("faculty_page_confirmed") is True)
        embed_ok = _embedding_pass(c)

        # 3-Signal Lock: require >=2 True
        signals = [orcid_ok, faculty_ok, embed_ok]
        passed_lock = sum(1 for s in signals if s) >= 2

        # Run domain check (two-layer chain); import lazily and be permissive on failure
        try:
            global check_domain_two_layer
            if check_domain_two_layer is None:
                from chains import check_domain_two_layer as _check
                check_domain_two_layer = _check

            domain_result = await check_domain_two_layer(c, student_profile)
            domain_passed = bool(domain_result.get("passed"))
            # Update counters
            if domain_result.get("layer") == "blacklist":
                bb += 1
            else:
                llm_checked += 1
        except Exception as e:
            logger.warning("domain_check_failed", error=str(e), candidate=cid)
            domain_passed = True  # be permissive on error

        # Candidate is resolved only if lock passes AND domain check passed
        if passed_lock and domain_passed:
            resolved.append(c)

        disambiguation[cid or str(len(disambiguation))] = {
            "orcid_ok": orcid_ok,
            "faculty_ok": faculty_ok,
            "embed_ok": embed_ok,
            "passed_lock": passed_lock,
            "domain_passed": domain_passed,
        }

    logger.info("resolve_node_complete", resolved=len(resolved), raw_total=len(raw))

    return {
        "resolved_candidates": state.get("resolved_candidates", []) + resolved,
        "disambiguation_results": {**disambiguation, **disambiguation},
        "domain_blacklist_blocked": bb,
        "domain_llm_checked": llm_checked,
    }
