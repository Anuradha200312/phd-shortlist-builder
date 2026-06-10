"""
Database CRUD helpers for persisting supervisors, shortlists and entries.

These helpers use SQLAlchemy AsyncSession and the ORM models in `db.models`.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import uuid
import structlog

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import ORM models lazily inside functions to avoid heavy/optional DB dialect imports at module import time

logger = structlog.get_logger()


async def upsert_supervisor(session: AsyncSession, sup: Dict[str, Any]) -> str:
    """Insert or update a supervisor record. Returns supervisor id."""
    sup_id = sup.get("id")
    if not sup_id:
        # generate a synthetic id when not provided
        sup_id = str(uuid.uuid4())
        sup["id"] = sup_id

    from db.models import SupervisorModel

    stmt = select(SupervisorModel).where(SupervisorModel.id == sup_id)
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        # update fields minimally
        for k, v in sup.items():
            if hasattr(existing, k) and v is not None:
                setattr(existing, k, v)
        session.add(existing)
        await session.flush()
        logger.debug("supervisor_updated", id=sup_id)
        return existing.id

    new = SupervisorModel(
        id=sup_id,
        name=sup.get("name") or "",
        institution=sup.get("institution"),
        department=sup.get("department"),
        country=sup.get("country"),
        email=sup.get("email"),
        profile_url=sup.get("url") or sup.get("profile_url"),
        orcid=sup.get("orcid"),
        raw_api_payload=sup,
    )
    session.add(new)
    await session.flush()
    logger.debug("supervisor_inserted", id=new.id)
    return new.id


async def create_shortlist(
    session: AsyncSession,
    student_id: str,
    output_json: Dict[str, Any],
    run_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a Shortlist and associated entries. Returns shortlist id."""
    from db.models import ShortlistModel, ShortlistEntryModel

    shortlist = ShortlistModel(student_id=student_id, output_json=output_json, run_metadata=run_metadata or {})
    session.add(shortlist)
    await session.flush()

    entries = output_json.get("shortlist", [])
    for e in entries:
        sup = e.get("supervisor") or {}
        sup_id = await upsert_supervisor(session, sup)

        entry = ShortlistEntryModel(
            shortlist_id=shortlist.id,
            supervisor_id=sup_id,
            rank=e.get("rank", 0),
            tier=e.get("tier"),
            confidence_score=e.get("confidence_score") or e.get("confidence"),
            confidence_breakdown=e.get("confidence_breakdown"),
            why_match=e.get("why_match"),
            match_dimensions=e.get("match_dimensions"),
            evidence_snapshot=e.get("evidence"),
            eligibility_flags=e.get("eligibility_flags") or [],
            contamination_risk=e.get("contamination_risk") or [],
            disambiguation_signals=e.get("disambiguation_signals") or {},
            faculty_page_confirmed=sup.get("faculty_page_confirmed"),
            last_paper_year=sup.get("last_paper_year"),
        )
        session.add(entry)

    await session.commit()
    logger.info("shortlist_created", shortlist_id=str(shortlist.id), student_id=student_id)
    return str(shortlist.id)
