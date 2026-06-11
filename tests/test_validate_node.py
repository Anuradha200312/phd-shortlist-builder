import asyncio

from graph.nodes.validate_node import validate_node


async def _run():
    state = {
        "target_countries": ["USA", "UK", "Canada"],
        "enriched_candidates": [
            # 1. Explicit country in target — passes
            {"rank": 1, "country": "USA", "institution": "MIT",
             "evidence": [{"type": "paper", "title": "X"}]},

            # 2. No country but UK institution — inferred UK, passes
            {"rank": 2, "country": None, "institution": "University of Oxford",
             "evidence": [{"type": "paper", "title": "Y"}]},

            # 3. NIH source with no country — defaults to USA, passes
            {"rank": 3, "source": "nih_reporter", "country": None, "institution": "Unknown",
             "evidence": [{"type": "paper", "title": "Z"}]},

            # 4. Unresolvable country (FR) — blocked
            {"rank": 4, "country": "FR", "institution": "Sorbonne",
             "evidence": [{"type": "paper", "title": "W"}]},

            # 5. Valid UK country but no evidence — blocked by evidence
            {"rank": 5, "country": "UK", "institution": "Edinburgh",
             "evidence": []},
        ],
    }

    res = await validate_node(state)
    summary = res["validation_summary"]
    assert summary["input_count"] == 5
    assert summary["validated_count"] == 3   # ranks 1, 2, 3 pass
    assert summary["blocked_by_country"] == 1  # rank 4 (FR)
    assert summary["blocked_by_evidence"] == 1  # rank 5 (no evidence)

    # Check inferred countries were written back
    names = [c.get("country") for c in res["validated_shortlist"]]
    assert "USA" in names
    assert "UK" in names


def test_validate_node():
    asyncio.run(_run())
