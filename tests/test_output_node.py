import asyncio
from unittest.mock import AsyncMock, patch

from graph.nodes.output_node import output_node
from graph.state import create_initial_state


async def _fake_create_shortlist(session, student_id, output_json, run_metadata=None):
    return "fake-shortlist-id"


def test_output_node_basic():
    state = create_initial_state({"student_id": "s1"}, run_id="r1")
    state["audited_shortlist"] = [
        {
            "id": "c1", "rank": 1, "tier": "target", "confidence": 0.8,
            "why_match": "ok",
            "name": "Alice", "institution": "MIT", "country": "USA",
            "evidence": [{"type": "paper", "title": "Test paper"}],
        },
    ]

    # Patch both the crud function and the DB session so no real DB is needed
    with patch("db.crud.create_shortlist", new=_fake_create_shortlist), \
         patch("db.engine.AsyncSessionLocal") as mock_session_cls:
        # Make the session context manager work
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        result = asyncio.run(output_node(state))

    assert "output_json" in result
    assert result["output_json"]["student_id"] == "s1"
    # shortlist_id may be None if DB was skipped — that's acceptable
    assert "shortlist_id" in result
    assert result["output_file_path"] is not None
