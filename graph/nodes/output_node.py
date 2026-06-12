"""
output_node: Assemble final JSON output and persist to DB + file.

This module builds the final `ShortlistOutput` JSON structure, persists it to
the DB via `create_shortlist`, and writes a copy to `sample_output/` for debugging.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
import structlog
from typing import Dict, Any

from graph.state import ShortlistState

# DB imports are lazy (inside function body) so this module can be imported
# without asyncpg/postgres being available (e.g., CI unit tests).

logger = structlog.get_logger()


# Domain keyword vocabulary for research_focus extraction from text
_DOMAIN_KEYWORDS = [
    # AI / ML core
    "machine learning", "deep learning", "neural network", "artificial intelligence",
    "reinforcement learning", "federated learning", "transfer learning",
    "natural language processing", "NLP", "large language model", "LLM",
    "computer vision", "image recognition", "object detection",
    "generative model", "GAN", "diffusion model", "transformer",
    # Medical / Clinical AI
    "medical imaging", "clinical decision", "electronic health record",
    "precision medicine", "drug discovery", "bioinformatics",
    "genomics", "proteomics", "cancer", "radiology", "pathology",
    "brain", "neuroscience", "EHR", "clinical NLP",
    # Data science
    "data mining", "knowledge graph", "graph neural network",
    "anomaly detection", "time series", "explainable AI", "XAI",
    "fairness", "privacy", "differential privacy",
    # Systems
    "distributed systems", "cloud computing", "edge computing",
    "Internet of Things", "IoT", "cybersecurity",
]


def _extract_research_focus(c: dict) -> list:
    """Build a research_focus list from all available candidate signals."""
    focus = []

    # 1. Best source: pre-extracted research_areas / keywords / topics
    for field in ("research_areas", "keywords", "topics", "x_concepts"):
        val = c.get(field) or []
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.strip():
                    focus.append(item.strip())
                elif isinstance(item, dict):
                    name = item.get("display_name") or item.get("name") or ""
                    if name.strip():
                        focus.append(name.strip())

    # 2. Scan paper titles + abstract for domain keywords
    if len(focus) < 3:
        text_sources = []
        for paper in (c.get("papers") or c.get("evidence") or [])[:5]:
            if isinstance(paper, dict):
                text_sources.append(paper.get("title") or "")
                text_sources.append(paper.get("abstract") or "")
        text_sources.append(c.get("abstract") or "")
        combined = " ".join(text_sources).lower()

        for kw in _DOMAIN_KEYWORDS:
            if kw.lower() in combined and kw not in focus:
                focus.append(kw)
                if len(focus) >= 8:
                    break

    # Deduplicate, preserve order, cap at 10
    seen = set()
    result = []
    for f in focus:
        fl = f.lower()
        if fl not in seen:
            seen.add(fl)
            result.append(f)
    return result[:10]


def build_shortlist_output(state: ShortlistState, max_results: int = 100) -> dict:
    """Convert pipeline state into the final ShortlistOutput JSON."""
    profile = state.get("student_profile", {})
    candidates = state.get("audited_shortlist", [])[:max_results]

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
            "research_focus": _extract_research_focus(c),
            "evidence": (c.get("papers", []) or [])[:5] + (c.get("grants", []) or [])[:3],
            "why_match": c.get("why_match", ""),
            "tier": c.get("tier", "target"),
            "open_positions": c.get("open_positions", []),
            "eligibility_flags": c.get("eligibility_flags", []),
            "contamination_risk": c.get("contamination_risk", []),
            "confidence_score": c.get("confidence") or c.get("confidence_score", 0.0),
            "confidence_breakdown": c.get("confidence_breakdown"),
            "match_dimensions": {
                "research_overlap": c.get("embedding_similarity", 0.0),
                "recent_activity": (c.get("last_paper_year") or 0) >= (datetime.now().year - 3),
                "is_pi_verified": c.get("is_pi_verified", False),
                "h_index": c.get("h_index", 0),
                "country_match": c.get("country", "") in (state.get("target_countries") or []),
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
        "student_id": profile.get("student_id", profile.get("id", "unknown")),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "pipeline_version": state.get("pipeline_version", "1.0.0"),
        "shortlist": shortlist_entries,
        "metadata": {
            "total_candidates_considered": len(state.get("raw_candidates", []) or []),
            "data_sources": state.get("data_sources_used", []),
            "llm_provider_used": state.get("llm_provider_used", ""),
            "langgraph_run_id": state.get("run_id", ""),
            "run_duration_seconds": round(duration, 1),
            "audit_summary": state.get("audit_summary", {}),
        },
    }


async def output_node(state: ShortlistState) -> Dict[str, Any]:
    """Assemble final JSON, persist to DB, and write a local copy to disk."""
    logger.info("output_node_start", candidates_in=len(state.get("audited_shortlist", []) or []))

    output = build_shortlist_output(state)

    # Persist to DB if available (lazy import so module works without asyncpg)
    shortlist_id = None
    try:
        from db.crud import create_shortlist
        from db.engine import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            shortlist_id = await create_shortlist(
                session, output["student_id"], output,
                run_metadata={"run_id": state.get("run_id")}
            )
    except Exception as e:
        logger.warning("db_persist_skipped", error=str(e))
        shortlist_id = None

    # Write a local copy with auto-incrementing filename
    try:
        output_dir = Path("sample_output")
        output_dir.mkdir(exist_ok=True)

        base_name = output["student_id"]
        import re
        match = re.match(r"^(.*?)(_?)(\d+)$", base_name)
        if match:
            prefix, separator, num_str = match.groups()
            width = len(num_str)
            counter = int(num_str)
            while True:
                filename = f"{prefix}{separator}{str(counter).zfill(width)}.json"
                output_path = output_dir / filename
                if not output_path.exists():
                    break
                counter += 1
        else:
            output_path = output_dir / f"{base_name}.json"
            if output_path.exists():
                counter = 1
                while True:
                    filename = f"{base_name}_{counter:03d}.json"
                    output_path = output_dir / filename
                    if not output_path.exists():
                        break
                    counter += 1

        output_path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
        saved_path = str(output_path)
    except Exception as e:
        logger.warning("failed_write_output", error=str(e))
        saved_path = None

    logger.info(
        "output_node_complete",
        shortlist_id=shortlist_id,
        shortlist_count=len(output["shortlist"]),
        output_file_path=saved_path,
    )

    return {
        "shortlist_id": shortlist_id,
        "output_json": output,
        "output_file_path": saved_path,
    }

