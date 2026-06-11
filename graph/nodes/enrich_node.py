"""
enrich_node: Add `why_match` explanations and eligibility checks for top candidates.

Behavior:
- Operates on `scored_candidates` and processes top `max_candidates_to_enrich` from settings
- Calls `generate_why_match_batch` to produce `why_match` strings for each candidate
- Updates `enriched_candidates` with `why_match` and `eligibility` fields

Key fixes:
- Lazy import retried every call (not cached as None permanently on first failure)
- why_match is NEVER empty: LLM → fallback template → evidence-based summary
- _enrich_key uses supervisor name as stable lookup key
"""
from __future__ import annotations
import asyncio
import structlog
from typing import List

from config.settings import get_settings
from graph.state import ShortlistState

logger = structlog.get_logger()


def _candidate_lookup_key(c: dict) -> str:
    """Stable key used to match candidates to why_match results.

    Priority: name > openalex_id > semantic_scholar_id > id > url
    Using name as the primary key because it survives all pipeline node transitions.
    """
    name = (c.get("name") or "").strip()
    if name and name not in ("Unknown", ""):
        return name
    return (
        c.get("openalex_id")
        or c.get("semantic_scholar_id")
        or c.get("id")
        or c.get("url")
        or ""
    )


def _build_fallback_why_match(c: dict, student_profile: dict) -> str:
    """Generate a meaningful why_match without LLM when chain is unavailable."""
    name = c.get("name", "This supervisor")
    institution = c.get("institution", "their institution")
    areas = c.get("research_areas") or []
    interests = student_profile.get("research_interests", [])
    papers = c.get("papers") or c.get("evidence") or []
    h_index = c.get("h_index", 0)

    # Find overlapping areas
    overlap = [a for a in areas if any(i.lower() in a.lower() or a.lower() in i.lower()
                                        for i in interests)]

    # Pick top 2 evidence papers
    top_papers = [p.get("title") for p in papers[:2] if p.get("title")]

    parts = []
    if overlap:
        parts.append(
            f"{name} at {institution} actively researches {', '.join(overlap[:3])}, "
            f"which directly aligns with your stated interest in {', '.join(interests[:2])}."
        )
    elif areas:
        parts.append(
            f"{name} at {institution} works on {', '.join(areas[:3])}, "
            f"with potential overlap with your research in {', '.join(interests[:2])}."
        )
    else:
        parts.append(
            f"{name} at {institution} has an established research programme "
            f"relevant to {', '.join(interests[:2])}."
        )

    if top_papers:
        parts.append(
            f"Recent work includes: \"{top_papers[0]}\""
            + (f" and \"{top_papers[1]}\"" if len(top_papers) > 1 else "") + "."
        )

    if h_index and h_index > 10:
        parts.append(f"With an h-index of {h_index}, they are a productive and established PI.")

    return " ".join(parts)


async def enrich_node(state: ShortlistState) -> dict:
    scored = state.get("scored_candidates", []) or []
    settings = get_settings()
    max_enrich = settings.max_candidates_to_enrich or 120

    # Select top-K
    top = scored[:max_enrich]

    student_profile = state.get("student_profile", {})

    # Try to import the LLM chain — retry every call (don't cache None permanently)
    _generate_why_match_batch = None
    try:
        from chains import generate_why_match_batch as _gwb
        _generate_why_match_batch = _gwb
    except Exception as e:
        logger.warning("enrich_node_chain_import_failed", error=str(e))

    # If chain is not available, use meaningful fallback for every candidate
    if _generate_why_match_batch is None:
        out = []
        for c in top:
            c2 = dict(c)
            c2["why_match"] = _build_fallback_why_match(c, student_profile)
            c2["eligibility"] = {"open_positions": bool(c.get("open_positions"))}
            out.append(c2)

        logger.info("enrich_node_complete_fallback", enriched=len(out))
        return {"enriched_candidates": state.get("enriched_candidates", []) + out}

    # Call the LLM batch generator
    try:
        # Patch each candidate with a stable _key field
        keyed_top = []
        for c in top:
            c2 = dict(c)
            c2["_enrich_key"] = _candidate_lookup_key(c)
            keyed_top.append(c2)

        why_map = await _generate_why_match_batch(
            keyed_top, student_profile, concurrency=settings.why_match_concurrency
        )

        enriched = []
        for c in keyed_top:
            c2 = dict(c)
            key = c2.pop("_enrich_key", "")
            # Try multiple fallback keys in order
            why = (
                why_map.get(key)
                or why_map.get(c.get("name"))
                or why_map.get(c.get("id"))
                or why_map.get(c.get("openalex_id"))
                or why_map.get(c.get("semantic_scholar_id"))
                or why_map.get(c.get("url"))
                or ""
            )
            # NEVER leave why_match blank — use meaningful fallback if LLM returned nothing
            if not why or not why.strip():
                why = _build_fallback_why_match(c, student_profile)

            c2["why_match"] = why
            c2["eligibility"] = {"open_positions": bool(c.get("open_positions"))}
            enriched.append(c2)

        logger.info("enrich_node_complete", enriched=len(enriched))
        return {"enriched_candidates": state.get("enriched_candidates", []) + enriched}
    except Exception as e:
        logger.error("enrich_node_failed", error=str(e))
        # Full fallback — generate non-empty why_match for all
        out = []
        for c in top:
            c2 = dict(c)
            c2["why_match"] = _build_fallback_why_match(c, student_profile)
            c2["eligibility"] = {"open_positions": bool(c.get("open_positions"))}
            out.append(c2)
        return {"enriched_candidates": state.get("enriched_candidates", []) + out}
