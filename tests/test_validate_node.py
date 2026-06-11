import asyncio

from graph.nodes.validate_node import validate_node


async def _run():
    state = {
        "target_countries": ["USA", "UK"],
        "enriched_candidates": [
            {
                "rank": 1,
                "country": "USA",  # flat dict — real pipeline format
                "evidence": [{"type": "paper", "title": "X"}],
            },
            {
                "rank": 2,
                "country": "India",  # not in target list → blocked
                "evidence": [{"type": "paper", "title": "Y"}],
            },
            {
                "rank": 3,
                "country": "UK",
                "evidence": [],  # no evidence → blocked
            },
            {
                "rank": 4,
                "country": "Unknown",  # Unknown → blocked (hard constraint)
                "evidence": [{"type": "paper", "title": "Z"}],
            },
        ],
    }

    res = await validate_node(state)
    assert res["validation_summary"]["input_count"] == 4
    # Only rank 1 (USA with evidence) should pass
    assert res["validation_summary"]["validated_count"] == 1
    assert res["validation_summary"]["blocked_by_country"] == 2  # India + Unknown
    assert res["validation_summary"]["blocked_by_evidence"] == 1  # UK (valid country but no evidence)


def test_validate_node():
    asyncio.run(_run())
