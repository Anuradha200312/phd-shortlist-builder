import asyncio

from graph.nodes.resolve_node import resolve_node
from graph.state import create_initial_state

# Monkeypatch the domain check inside the resolve_node module to avoid LLM calls
import graph.nodes.resolve_node as rn


async def _fake_domain_check(candidate, profile):
    return {"passed": True, "layer": "llm", "reason": "ok"}


rn.check_domain_two_layer = _fake_domain_check


def test_resolve_node_basic():
    state = create_initial_state({"student_id": "s1", "target_countries": []}, run_id="r1")
    # Raw candidates: one with ORCID + faculty page confirmed, one with none
    state["raw_candidates"] = [
        {"id": "a1", "name": "Alice", "orcid": "0000-0001-2345-6789", "faculty_page_confirmed": True},
        {"id": "b1", "name": "Bob", "orcid": None, "faculty_page_confirmed": False, "embedding_similarity": 0.2},
    ]

    result = asyncio.run(resolve_node(state))

    assert "resolved_candidates" in result
    assert len(result["resolved_candidates"]) == 1
    assert result["disambiguation_results"]["a1"]["passed_lock"] is True
    assert result["disambiguation_results"]["b1"]["passed_lock"] is False
