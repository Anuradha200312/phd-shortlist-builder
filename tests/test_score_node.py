import asyncio

from graph.nodes.score_node import score_node
from graph.state import create_initial_state

# Patch vectorstore and chains
import graph.nodes.score_node as sn


async def _fake_query_similarity(candidate, profile):
    # give higher similarity for candidate 'good'
    if candidate.get("id") == "good":
        return 0.9
    return 0.1


class _DummyStore:
    def __init__(self):
        self.query_similarity = _fake_query_similarity


sn.get_chroma_store = lambda *a, **k: _DummyStore()


# Patch build_confidence_breakdown to a simple deterministic function
class _SimpleCB:
    def __init__(self, total_score):
        self.total_score = total_score

    def dict(self):
        return {"total_score": self.total_score}


def _fake_build_confidence_breakdown(candidate, profile):
    sim = candidate.get("embedding_similarity", 0.0)
    # deterministic function for tests
    total = 0.3 * sim + 0.7 * 0.5
    return _SimpleCB(total)


sn.build_confidence_breakdown = _fake_build_confidence_breakdown


def test_score_node_basic():
    state = create_initial_state({"student_id": "s1", "research_interests": ["ml"], "target_countries": []}, run_id="r1")
    state["resolved_candidates"] = [
        {"id": "good", "title": "Good Paper", "abstract": "machine learning models"},
        {"id": "bad", "title": "Other", "abstract": "history of art"},
    ]

    result = asyncio.run(score_node(state))

    assert "scored_candidates" in result
    assert len(result["scored_candidates"]) == 2
    # Ensure highest rank is the 'good' candidate
    assert result["scored_candidates"][0]["id"] == "good"
