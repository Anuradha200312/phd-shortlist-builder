"""
enrich_node: Add `why_match` explanations and eligibility checks for top candidates.

Behavior:
- Operates on `scored_candidates` and processes top `max_candidates_to_enrich` from settings
- Calls `generate_why_match_batch` to produce `why_match` strings for each candidate
- Updates `enriched_candidates` with `why_match` and `eligibility` fields
"""
from __future__ import annotations
import asyncio
import structlog
from typing import List

from config.settings import get_settings
from graph.state import ShortlistState

logger = structlog.get_logger()

# Lazy import of chains to avoid heavy imports during test runs
_generate_why_match_batch = None


async def enrich_node(state: ShortlistState) -> dict:
    scored = state.get("scored_candidates", []) or []
    settings = get_settings()
    max_enrich = settings.max_candidates_to_enrich or 120

    # Select top-K
    top = scored[:max_enrich]

    # Lazy import
    global _generate_why_match_batch
    if _generate_why_match_batch is None:
        try:
            from chains import generate_why_match_batch as _gwb

            _generate_why_match_batch = _gwb
        except Exception:
            _generate_why_match_batch = None

    # If chain isn't available (tests), synthesize simple why_match strings
    if _generate_why_match_batch is None:
        out = []
        for c in top:
            c2 = dict(c)
            c2["why_match"] = f"Candidate {c.get('id')} is a match based on title '{c.get('title')}'."
            c2["eligibility"] = {"open_positions": False}
            out.append(c2)

        logger.info("enrich_node_complete_stub", enriched=len(out))
        return {"enriched_candidates": state.get("enriched_candidates", []) + out}

    # Otherwise call the chain batch generator
    try:
        student_profile = state.get("student_profile", {})
        why_map = await _generate_why_match_batch(top, student_profile, concurrency=settings.why_match_concurrency)

        enriched = []
        for c in top:
            c2 = dict(c)
            c2["why_match"] = why_map.get(c.get("id")) or why_map.get(c.get("url")) or ""
            c2["eligibility"] = {"open_positions": bool(c.get("open_positions"))}
            enriched.append(c2)

        logger.info("enrich_node_complete", enriched=len(enriched))
        return {"enriched_candidates": state.get("enriched_candidates", []) + enriched}
    except Exception as e:
        logger.error("enrich_node_failed", error=str(e))
        # Fall back to stub behaviour
        return await enrich_node({**state, "scored_candidates": top})
