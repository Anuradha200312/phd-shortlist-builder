from __future__ import annotations
import io
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db.crud import upsert_outcome_signal, get_area_success_rates, get_institution_response_rates
from feedback.feedback_analysis_chain import feedback_analysis_chain

class FeedbackImprover:
    """Uses admission outcome signals and LLMs to refine future search / scoring weights."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def ingest_csv_content(self, csv_content: str) -> Dict[str, Any]:
        """Ingests raw CSV text, updates DB outcome signals, and returns structured analysis."""
        df = pd.read_csv(io.StringIO(csv_content))
        return await self._process_dataframe(df)

    async def ingest_csv_file(self, csv_path: Path) -> Dict[str, Any]:
        """Ingests CSV file, updates DB outcome signals, and returns structured analysis."""
        df = pd.read_csv(csv_path)
        return await self._process_dataframe(df)

    async def _process_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        # Validate columns
        required_cols = {"student_id", "supervisor_id", "outcome"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        # Ingest outcome signals in DB
        for _, row in df.iterrows():
            details = str(row.get("details")) if "details" in row and not pd.isna(row.get("details")) else None
            await upsert_outcome_signal(
                session=self.db,
                supervisor_id=str(row["supervisor_id"]),
                student_id=str(row["student_id"]),
                outcome=str(row["outcome"]),
                details=details,
            )

        # Retrieve aggregated stats
        area_rates = await get_area_success_rates(self.db)
        inst_rates = await get_institution_response_rates(self.db)

        # Run LLM analysis on outcomes
        outcomes_sample = df.head(50).to_dict(orient="records")

        analysis = await feedback_analysis_chain.ainvoke({
            "outcomes_sample": str(outcomes_sample),
            "area_rates": str(area_rates),
            "institution_rates": str(inst_rates),
        })

        return {
            "status": "success",
            "records_processed": len(df),
            "analysis": analysis,
        }
