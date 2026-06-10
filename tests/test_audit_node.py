import asyncio

from graph.nodes.audit_node import audit_node


async def _run():
    state = {
        "scored_candidates": [
            {
                "id": "c1",
                "rank": 1,
                "supervisor": {"name": "Dr A", "institution": "mit.edu", "is_pi_verified": True},
                "confidence": 0.9,
                "evidence": [{"url": "https://arxiv.org/abs/1"}],
            },
            {
                "id": "c2",
                "rank": 2,
                "supervisor": {"name": "Dr B", "institution": "ox.ac.uk", "is_pi_verified": False},
                "confidence": 0.3,
                "evidence": [{"url": "https://someblog.com/post"}],
            },
            {
                "id": "c3",
                "rank": 3,
                "supervisor": {"name": "Dr B", "institution": "ox.ac.uk", "is_pi_verified": None},
                "confidence": 0.5,
                "evidence": [],
            },
        ]
    }

    res = await audit_node(state, top_n=3)
    summary = res.get("audit_summary")
    assert summary is not None
    assert summary["top_n"] == 3
    # Expect at least one flagged (c2 low_confidence + missing_pi_verified + evidence_domain_mismatch)
    assert summary["flagged_count"] >= 1


def test_audit_node():
    asyncio.run(_run())
