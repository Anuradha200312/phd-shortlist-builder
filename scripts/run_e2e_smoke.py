"""End-to-end smoke run (no external APIs).

This script runs a minimalist pipeline: resolve -> score -> enrich -> validate -> audit -> build output.
It avoids DB persistence by calling `build_shortlist_output` directly.
"""
import asyncio
import json
from pathlib import Path

from graph.nodes.resolve_node import resolve_node
from graph.nodes.score_node import score_node
from graph.nodes.enrich_node import enrich_node
from graph.nodes.validate_node import validate_node
from graph.nodes.audit_node import audit_node
from graph.nodes.output_node import build_shortlist_output


async def main():
    # sample state
    state = {
        "student_profile": {"student_id": "test-student", "research_interests": ["deep learning", "medical imaging"]},
        "target_countries": ["USA", "UK"],
        "raw_candidates": [
            {"id": "c1", "title": "Deep learning for MRI", "orcid": "", "faculty_page_confirmed": True, "institution": "mit.edu", "country": "USA", "papers": [{"url": "https://arxiv.org/abs/1"}]},
            {"id": "c2", "title": "Federated learning in healthcare", "orcid": "0000-0000-0000-000X", "faculty_page_confirmed": False, "institution": "ox.ac.uk", "country": "UK", "papers": [{"url": "https://example.com/paper"}]},
            {"id": "c3", "title": "Graph methods for bioinformatics", "orcid": "", "faculty_page_confirmed": False, "institution": "someuni.edu", "country": "India", "papers": []},
        ],
        "run_start_time": "",
        "pipeline_version": "1.0.0",
        "data_sources_used": ["test_source"],
    }

    # Resolve
    r = await resolve_node(state)
    state.update(r)

    # Score
    r = await score_node(state)
    state.update(r)

    # Enrich
    r = await enrich_node(state)
    state.update(r)

    # Validate
    r = await validate_node(state)
    state.update(r)

    # Audit
    r = await audit_node(state, top_n=10)
    state.update(r)

    # Build final output (no DB persist)
    out = build_shortlist_output(state)

    # Write to sample_output for inspection
    out_path = Path("sample_output") / f"e2e_{out['student_id']}.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("E2E smoke run complete; output written to", out_path)


if __name__ == "__main__":
    asyncio.run(main())
