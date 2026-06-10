"""output_node: Assembles final JSON output and writes to file."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
import structlog
from graph.state import ShortlistState

logger = structlog.get_logger()


def build_shortlist_output(state: ShortlistState, max_results: int = 100) -> dict:
    """Convert pipeline state into the final ShortlistOutput JSON."""
    profile = state["student_profile"]
    candidates = state["audited_shortlist"][:max_results]

    shortlist_entries = []
    for i, c in enumerate(candidates, start=1):
        entry = {
            "rank": i,
            "supervisor": {
                "name": c.get("name", "Unknown"),
                "institution": c.get("institution", "Unknown"),
                "department": c.get("department"),
                "country": c.get("country", "Unknown"),
                "profile_url": c.get("profile_url"),
                "email": c.get("email"),
                "semantic_scholar_id": c.get("semantic_scholar_id"),
                "openalex_id": c.get("openalex_id"),
                "google_scholar_id": c.get("google_scholar_id"),
                "orcid": c.get("orcid"),
            },
            "research_focus": c.get("research_areas", []),
            "evidence": c.get("papers", [])[:5] + c.get("grants", [])[:3],
            "why_match": c.get("why_match", ""),
            "tier": c.get("tier", "target"),
            "open_positions": c.get("open_positions", []),
            "eligibility_flags": c.get("eligibility_flags", []),
            "contamination_risk": c.get("contamination_risk", []),
            "confidence_score": c.get("confidence_score", 0.0),
            "confidence_breakdown": c.get("confidence_breakdown"),
            "match_dimensions": {
                "research_overlap": c.get("embedding_similarity", 0.0),
                "recent_activity": c.get("last_paper_year", 0) >= (datetime.now().year - 3),
                "is_pi_verified": c.get("is_pi_verified", False),
                "h_index": c.get("h_index", 0),
                "country_match": c.get("country", "") in state["target_countries"],
                "domain_confidence": c.get("domain_confidence", 0.0),
                "last_paper_year": c.get("last_paper_year"),
            },
        }
        shortlist_entries.append(entry)

    # Calculate run duration
    start = state.get("run_start_time", "")
    duration = 0.0
    if start:
        try:
            dt_start = datetime.fromisoformat(start)
            duration = (datetime.utcnow() - dt_start).total_seconds()
        except (ValueError, TypeError):
            pass

    return {
        "student_id": profile.get("student_id", "unknown"),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "pipeline_version": state.get("pipeline_version", "1.0.0"),
        "shortlist": shortlist_entries,
        "metadata": {
            "total_candidates_considered": len(state.get("raw_candidates", [])),
            "data_sources": state.get("data_sources_used", []),
            "llm_provider_used": state.get("llm_provider_used", ""),
            "langgraph_run_id": state.get("run_id", ""),
            "run_duration_seconds": round(duration, 1),
            "audit_summary": state.get("audit_summary", {}),
        },
    }


async def output_node(state: ShortlistState) -> dict:
    """Assemble final JSON and optionally write to file."""
    logger.info("output_node_start", candidates_in=len(state["audited_shortlist"]))

    output = build_shortlist_output(state)

    # Write to sample_output/ directory
    output_dir = Path("sample_output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{output['student_id']}.json"
    output_path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")

    logger.info(
        "output_node_complete",
        shortlist_count=len(output["shortlist"]),
        output_path=str(output_path),
        duration_s=output["metadata"]["run_duration_seconds"],
    )

    return {}  # terminal node — no state changes
