import asyncio
from types import SimpleNamespace

import graph.nodes.score_node as score_node


async def _run():
    # Prepare fake store that returns high similarity and records indexing
    class FakeStore:
        def __init__(self):
            self.queries = []
            self.indexed = False

        async def query_similarity(self, candidate, student_profile):
            self.queries.append((candidate, student_profile))
            return 0.9

        async def index_candidates(self, candidates):
            self.indexed = True

    fake_store = FakeStore()

    # Monkeypatch the module-level accessor to return the same fake instance
    score_node.get_chroma_store = lambda *args, **kwargs: fake_store

    # Monkeypatch confidence builder to deterministic value
    def fake_bcb(candidate, student_profile):
        return SimpleNamespace(total_score=0.8, dict=lambda: {"total_score": 0.8})

    score_node.build_confidence_breakdown = fake_bcb

    state = {
        "student_profile": {"research_interests": ["deep learning"]},
        "resolved_candidates": [
            {"id": "c1", "supervisor": {"name": "A"}, "title": "paper A"},
            {"id": "c2", "supervisor": {"name": "B"}, "title": "paper B"},
        ],
    }

    res = await score_node.score_node(state)
    scored = res.get("scored_candidates", [])
    assert len(scored) == 2
    # All candidates should have been assigned rank and tier
    assert all("rank" in c and "tier" in c for c in scored)
    # Our fake confidence was 0.8 so tier should be 'target'
    assert scored[0]["tier"] == "target"
    # Ensure the fake store recorded the index operation
    assert fake_store.indexed is True


def test_score_node_chroma():
    asyncio.run(_run())
