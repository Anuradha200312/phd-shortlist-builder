"""LangGraph State definition — shared across all 9 pipeline nodes."""
from __future__ import annotations
from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ShortlistState(TypedDict):
    """
    Shared state flowing through every LangGraph node.
    Each node receives this state, makes changes, and returns the updated state.
    """

    # ── Inputs ────────────────────────────────────────────────────────────────
    student_profile: dict               # Raw parsed StudentProfile JSON
    target_countries: list[str]         # Hard constraint — never violated
    search_queries: list[str]           # Expanded by ingest_node

    # ── Pipeline data ─────────────────────────────────────────────────────────
    raw_candidates: list[dict]          # After retrieve_node
    resolved_candidates: list[dict]     # After resolve_node (3-Signal Lock + domain check)
    scored_candidates: list[dict]       # After score_node (embeddings + confidence)
    enriched_candidates: list[dict]     # After enrich_node (why_match + eligibility)
    validated_shortlist: list[dict]     # After validate_node (quality gates)
    audited_shortlist: list[dict]       # After audit_node (contamination self-audit)

    # ── 3-Signal Lock tracking ────────────────────────────────────────────────
    disambiguation_results: dict        # supervisor_id → {orcid_ok, faculty_ok, embed_ok}

    # ── Domain check tracking ─────────────────────────────────────────────────
    domain_blacklist_blocked: int       # Count blocked by keyword blacklist (no LLM needed)
    domain_llm_checked: int             # Count sent to LLM for deep check

    # ── Eligibility tracking ──────────────────────────────────────────────────
    findhaphd_positions: list[dict]     # Structured positions from FindAPhD / jobs.ac.uk

    # ── Control flow ──────────────────────────────────────────────────────────
    retrieval_attempts: int             # For conditional retry edge
    messages: Annotated[list, add_messages]  # LangGraph agent messages

    # ── Metadata ──────────────────────────────────────────────────────────────
    run_id: str
    pipeline_version: str
    llm_provider_used: str
    data_sources_used: list[str]
    run_start_time: str
    audit_summary: dict                 # Contamination self-audit results


def create_initial_state(student_profile: dict, run_id: str) -> ShortlistState:
    """Create the initial empty state for a new pipeline run."""
    return ShortlistState(
        student_profile=student_profile,
        target_countries=student_profile.get("target_countries", []),
        search_queries=[],
        raw_candidates=[],
        resolved_candidates=[],
        scored_candidates=[],
        enriched_candidates=[],
        validated_shortlist=[],
        audited_shortlist=[],
        disambiguation_results={},
        domain_blacklist_blocked=0,
        domain_llm_checked=0,
        findhaphd_positions=[],
        retrieval_attempts=0,
        messages=[],
        run_id=run_id,
        pipeline_version="1.0.0",
        llm_provider_used="",
        data_sources_used=[],
        run_start_time="",
        audit_summary={},
    )
