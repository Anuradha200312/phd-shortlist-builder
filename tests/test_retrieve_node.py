import asyncio

from graph.nodes.retrieve_node import retrieve_node
from graph.state import create_initial_state

# Monkeypatch the tool references inside the retrieve_node module to avoid network calls
import graph.nodes.retrieve_node as rn


async def _fake_tool_return(query, limit=10):
    return [{
        "id": f"paper:{query}:1",
        "source": "test_source",
        "title": f"Result for {query}",
        "url": f"https://example.org/{query}",
        "year": 2024,
    }]


class _DummyTool:
    def __init__(self, coro):
        self.arun = coro


# Patch the tool references inside the retrieve_node module
rn.search_semantic_scholar = _DummyTool(_fake_tool_return)
rn.search_openalex = _DummyTool(_fake_tool_return)
rn.search_nih_reporter = _DummyTool(_fake_tool_return)
rn.search_ukri = _DummyTool(_fake_tool_return)
rn.search_findaphd = _DummyTool(_fake_tool_return)


def test_retrieve_node_minimal():
    state = create_initial_state({"student_id": "s1", "target_countries": []}, run_id="r1")
    state["search_queries"] = ["machine learning", "graph neural networks"]

    result = asyncio.run(retrieve_node(state))

    assert result["retrieval_attempts"] == 1
    assert len(result["raw_candidates"]) >= 2
    # Ensure deduplication produced unique ids
    ids = {c["id"] for c in result["raw_candidates"]}
    assert len(ids) == len(result["raw_candidates"])
