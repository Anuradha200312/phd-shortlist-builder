import asyncio

from graph.nodes.validate_node import validate_node


async def _run():
    state = {
        "target_countries": ["USA", "UK"],
        "enriched_candidates": [
            {
                "rank": 1,
                "supervisor": {"name": "A", "country": "USA"},
                "evidence": [{"type": "paper", "title": "X"}],
            },
            {
                "rank": 2,
                "supervisor": {"name": "B", "country": "India"},
                "evidence": [{"type": "paper", "title": "Y"}],
            },
            {
                "rank": 3,
                "supervisor": {"name": "C", "country": "UK"},
                "evidence": [],
            },
        ],
    }

    res = await validate_node(state)
    assert res["validation_summary"]["input_count"] == 3
    assert res["validation_summary"]["validated_count"] == 1


def test_validate_node():
    asyncio.run(_run())
