import asyncio

from graph.nodes.output_node import output_node
from graph.state import create_initial_state

# Monkeypatch db.crud.create_shortlist to avoid DB access
import graph.nodes.output_node as on


async def _fake_create_shortlist(session, student_id, output_json, run_metadata=None):
    return "fake-shortlist-id"


on.create_shortlist = _fake_create_shortlist


def test_output_node_basic():
    state = create_initial_state({"student_id": "s1"}, run_id="r1")
    state["validated_shortlist"] = [
        {"id": "c1", "rank": 1, "tier": "target", "confidence": 0.8, "why_match": "ok", "supervisor": {"id": "c1", "name": "Alice"}},
    ]

    result = asyncio.run(output_node(state))

    assert "shortlist_id" in result
    assert result["shortlist_id"] == "fake-shortlist-id"
    assert result["output_json"]["student_id"] == "s1"
