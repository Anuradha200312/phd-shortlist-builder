import asyncio

from graph.nodes.enrich_node import enrich_node
from graph.state import create_initial_state

# Monkeypatch chains.generate_why_match_batch inside the module import path
import unittest.mock as mock


def test_enrich_node_basic():
    state = create_initial_state({"student_id": "s1", "research_interests": ["ml", "medical imaging"]}, run_id="r1")
    state["scored_candidates"] = [
        {"id": "c1", "name": "Dr Alice", "institution": "MIT", "research_areas": ["machine learning"], "title": "A paper about ML", "open_positions": []},
        {"id": "c2", "name": "Dr Bob", "institution": "Stanford", "research_areas": ["computer vision"], "title": "Other"},
    ]

    async def _fake_batch(candidates, profile, concurrency=10):
        out = {}
        for c in candidates:
            key = c.get("_enrich_key") or c.get("name") or c.get("id") or ""
            out[key] = f"Why match for {key}: strong alignment with student interests."
        return out

    with mock.patch("graph.nodes.enrich_node._build_fallback_why_match") as _fb:
        _fb.side_effect = lambda c, p: f"Fallback for {c.get('name')}"
        with mock.patch("chains.generate_why_match_batch", _fake_batch, create=True):
            result = asyncio.run(enrich_node(state))

    assert "enriched_candidates" in result
    assert len(result["enriched_candidates"]) == 2
    # why_match must be non-empty for all entries
    for entry in result["enriched_candidates"]:
        assert entry["why_match"] != "", f"why_match is blank for {entry.get('name')}"
