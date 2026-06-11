from __future__ import annotations
import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models import StudentProfile, ShortlistOutput
from db.engine import get_db
from graph.pipeline_graph import build_pipeline_graph
from graph.state import create_initial_state
from graph.nodes.output_node import build_shortlist_output

logger = structlog.get_logger()
router = APIRouter()


@router.post("/api/v1/shortlist", response_model=ShortlistOutput)
async def generate_shortlist_endpoint(
    profile: StudentProfile,
    db: AsyncSession = Depends(get_db),
):
    """Generate a supervisor shortlist for a given student profile using the LangGraph pipeline."""
    student_profile = profile.model_dump()
    student_id = student_profile.get("student_id", "unknown")
    run_id = str(uuid.uuid4())[:8]

    logger.info("api_generate_shortlist_start", student_id=student_id, run_id=run_id)

    # Initialize graph state
    graph = build_pipeline_graph()
    initial_state = create_initial_state(student_profile, run_id)

    config = {"configurable": {"thread_id": run_id}}

    try:
        final_state = await graph.ainvoke(initial_state, config=config)
    except Exception as exc:
        logger.error("api_generate_shortlist_failed", student_id=student_id, error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(exc)}",
        )

    # Format the final shortlist response
    output_data = build_shortlist_output(final_state)

    logger.info("api_generate_shortlist_success", student_id=student_id, run_id=run_id)
    return output_data
