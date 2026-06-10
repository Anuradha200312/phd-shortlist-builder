import asyncio

from graph.nodes.enrich_node import enrich_node
from graph.state import create_initial_state

# Monkeypatch chains.generate_why_match_batch inside module
import graph.nodes.enrich_node as en


async def _fake_batch(candidates, profile, concurrency=10):
    out = {}
    for c in candidates:
        out[c.get("id")] = f"Why match for {c.get('id')}"
    return out


en._generate_why_match_batch = _fake_batch


def test_enrich_node_basic():
    state = create_initial_state({"student_id": "s1", "research_interests": ["ml"]}, run_id="r1")
    state["scored_candidates"] = [
        {"id": "c1", "title": "A paper about ML", "open_positions": []},
        {"id": "c2", "title": "Other"},
    ]

    result = asyncio.run(enrich_node(state))

    assert "enriched_candidates" in result
    assert len(result["enriched_candidates"]) == 2
    assert result["enriched_candidates"][0]["why_match"] == "Why match for c1"
