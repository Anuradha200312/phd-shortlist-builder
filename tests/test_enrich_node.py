import asyncio

from graph.nodes.enrich_node import enrich_node
from graph.state import create_initial_state

# Monkeypatch chains.generate_why_match_batch inside module
import graph.nodes.enrich_node as en


async def _fake_batch(candidates, profile, concurrency=10):
    out = {}
    for c in candidates:
        # The real batch returns by _enrich_key (name > id > url)
        key = c.get("_enrich_key") or c.get("name") or c.get("id") or ""
        out[key] = f"Why match for {key}"
    return out


en._generate_why_match_batch = _fake_batch


def test_enrich_node_basic():
    state = create_initial_state({"student_id": "s1", "research_interests": ["ml"]}, run_id="r1")
    state["scored_candidates"] = [
        {"id": "c1", "name": "Dr Alice", "title": "A paper about ML", "open_positions": []},
        {"id": "c2", "name": "Dr Bob", "title": "Other"},
    ]

    result = asyncio.run(enrich_node(state))

    assert "enriched_candidates" in result
    assert len(result["enriched_candidates"]) == 2
    # why_match should be non-empty (keyed by name now)
    assert result["enriched_candidates"][0]["why_match"] != ""
    assert result["enriched_candidates"][1]["why_match"] != ""
