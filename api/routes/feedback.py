from __future__ import annotations
import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from db.engine import get_db
from feedback.improver import FeedbackImprover

logger = structlog.get_logger()
router = APIRouter()


@router.post("/api/v1/feedback")
async def ingest_feedback_endpoint(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Ingest PhD outcomes CSV to train/refine scoring models and analyze patterns."""
    logger.info("api_ingest_feedback_start", filename=file.filename)

    try:
        content = await file.read()
        csv_text = content.decode("utf-8")
    except Exception as exc:
        logger.error("api_ingest_feedback_read_error", error=str(exc))
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(exc)}")

    improver = FeedbackImprover(db)

    try:
        result = await improver.ingest_csv_content(csv_text)
    except Exception as exc:
        logger.error("api_ingest_feedback_processing_error", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info("api_ingest_feedback_success", records=result.get("records_processed"))
    return result
