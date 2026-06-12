"""retrieve_node: Fetches candidates from data source APIs in parallel.

Phase 2 implementation: call external data source tools (semantic_scholar,
openalex, nih_reporter, ukri, findaphd), aggregate and deduplicate results,
and return updated state fields used by downstream nodes.
"""
from __future__ import annotations
import asyncio
import structlog
from typing import List

from graph.state import ShortlistState
from config.settings import get_settings
from tools import (
    search_semantic_scholar,
    search_openalex,
    search_nih_reporter,
    search_ukri,
    search_findaphd,
)

logger = structlog.get_logger()


async def _call_all_tools(query: str, limit: int) -> List[dict]:
    """Call all data-source tools for a single query in parallel."""
    tasks = [
        search_semantic_scholar.arun(query, limit=limit),
        search_openalex.arun(query, limit=limit),
        search_nih_reporter.arun(query, limit=limit),
        search_ukri.arun(query, limit=limit),
        search_findaphd.arun(query, limit=limit),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out: List[dict] = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("tool_call_failed", error=str(r), query=query)
            continue
        if not r:
            continue
        out.extend(r)
    return out


def _supervisor_key(c: dict) -> str:
    """Build a stable identity key from supervisor name + institution + orcid.

    Falls back to paper id/url so we never lose a record entirely.
    """
    name = (c.get("name") or "").strip().lower()
    institution = (c.get("institution") or "").strip().lower()
    orcid = (c.get("orcid") or "").strip()
    if name and institution:
        return f"{name}|{institution}"
    if orcid:
        return orcid
    # last resort — paper-level key
    return c.get("id") or c.get("url") or (str(c.get("title")) + str(c.get("year")))


def _dedupe_candidates(candidates: List[dict]) -> List[dict]:
    """Deduplicate by supervisor identity, merging evidence from duplicates."""
    seen: dict = {}
    for c in candidates:
        key = _supervisor_key(c)
        if not key:
            continue
        if key in seen:
            existing = seen[key]
            # Merge scalar fields: prefer non-null values
            for k, v in c.items():
                if k in ("papers", "grants", "evidence"):
                    continue  # handle lists separately
                if not existing.get(k) and v:
                    existing[k] = v
            # Merge list evidence fields (dedupe by title)
            for list_key in ("papers", "grants", "evidence"):
                new_items = c.get(list_key) or []
                old_items = existing.get(list_key) or []
                old_titles = {(i.get("title") or "").lower() for i in old_items}
                for item in new_items:
                    t = (item.get("title") or "").lower()
                    if t and t not in old_titles:
                        old_items.append(item)
                        old_titles.add(t)
                existing[list_key] = old_items
        else:
            seen[key] = dict(c)
    return list(seen.values())


async def retrieve_node(state: ShortlistState) -> dict:
    """Fetch supervisor candidates from all configured data sources.

    Behavior:
    - Limits queries to a safe max
    - Calls all tools for each query concurrently
    - Deduplicates candidates by id/url
    - Updates `raw_candidates`, `retrieval_attempts`, and `data_sources_used`
    """
    queries = state["search_queries"] or []
    countries = state["target_countries"]
    attempt = state.get("retrieval_attempts", 0)

    settings = get_settings()
    per_tool_limit = 25   # increased from 15 — more raw candidates per source
    max_queries = min(len(queries), 20)  # increased from 12 — use more query variants

    logger.info(
        "retrieve_node_start",
        queries=len(queries),
        capped=max_queries,
        countries=countries,
        attempt=attempt + 1,
    )

    # Call tools for top queries concurrently with a semaphore to avoid bursts
    semaphore = asyncio.Semaphore(5)

    async def _worker(q: str):
        async with semaphore:
            return await _call_all_tools(q, limit=per_tool_limit)

    workers = [
        asyncio.create_task(_worker(q)) for q in queries[:max_queries]
    ]

    all_results = []
    if workers:
        gathered = await asyncio.gather(*workers)
        for res in gathered:
            all_results.extend(res or [])

    deduped = _dedupe_candidates(all_results)

    sources_used = list({c.get("source") for c in deduped if c.get("source")})

    logger.info("retrieve_node_complete", candidates_fetched=len(deduped), sources=sources_used)

    return {
        "raw_candidates": state.get("raw_candidates", []) + deduped,
        "retrieval_attempts": attempt + 1,
        "data_sources_used": list(set(state.get("data_sources_used", []) + sources_used)),
    }
