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

    name = sup.get("name")
    if not name or name == "Unknown":
        name = f"Unknown ({sup_id[:8]})"
        
    inst = sup.get("institution")
    if not inst or inst == "Unknown":
        inst = "Unknown"

    from db.models import SupervisorModel

    # Check by ID first
    stmt = select(SupervisorModel).where(SupervisorModel.id == sup_id)
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()

    # Check by ORCID to prevent supervisors_orcid_key violation
    orcid = sup.get("orcid")
    if orcid and orcid.startswith("https://orcid.org/"):
        orcid = orcid.replace("https://orcid.org/", "")
    if not existing and orcid:
        stmt = select(SupervisorModel).where(SupervisorModel.orcid == orcid)
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()

    # Check by OpenAlex ID to prevent unique openalex_id violation
    openalex_id = sup.get("openalex_id")
    if not existing and openalex_id:
        stmt = select(SupervisorModel).where(SupervisorModel.openalex_id == openalex_id)
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()

    # If not found, check by (name, institution) to prevent unique constraint violations
    if not existing and name and inst and not name.startswith("Unknown"):
        stmt = select(SupervisorModel).where(
            SupervisorModel.name == name,
            SupervisorModel.institution == inst
        )
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()

    if existing:
        # update fields minimally
        for k, v in sup.items():
            if k == "id":
                continue
            if hasattr(existing, k) and v is not None:
                setattr(existing, k, v)
        # Also ensure name and institution are set to normalized versions if updated
        existing.name = name
        existing.institution = inst
        session.add(existing)
        await session.flush()
        logger.debug("supervisor_updated", id=existing.id)
        return existing.id

    new = SupervisorModel(
        id=sup_id,
        name=name,
        institution=inst,
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


async def upsert_outcome_signal(
    session: AsyncSession,
    supervisor_id: str,
    student_id: str,
    outcome: str,
    details: Optional[str] = None,
) -> None:
    """Insert or update an outcome signal for a supervisor."""
    from db.models import OutcomeSignalModel
    stmt = select(OutcomeSignalModel).where(
        OutcomeSignalModel.supervisor_id == supervisor_id,
        OutcomeSignalModel.student_id == student_id,
    )
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        existing.outcome = outcome
        existing.details = details
        session.add(existing)
    else:
        new = OutcomeSignalModel(
            supervisor_id=supervisor_id,
            student_id=student_id,
            outcome=outcome,
            details=details,
        )
        session.add(new)
    await session.commit()


async def get_area_success_rates(session: AsyncSession) -> Dict[str, Dict[str, Any]]:
    """Calculate ADMIT/INTERVIEW rates grouped by research area."""
    from db.models import OutcomeSignalModel, SupervisorModel
    stmt = select(OutcomeSignalModel.outcome, SupervisorModel.research_areas).join(
        SupervisorModel, OutcomeSignalModel.supervisor_id == SupervisorModel.id
    )
    res = await session.execute(stmt)
    rows = res.all()

    stats: Dict[str, Dict[str, int]] = {}
    for outcome, areas in rows:
        if not areas:
            continue
        is_success = outcome.upper() in ("ADMIT", "INTERVIEW")
        for area in areas:
            if area not in stats:
                stats[area] = {"total": 0, "success": 0}
            stats[area]["total"] += 1
            if is_success:
                stats[area]["success"] += 1

    rates: Dict[str, Dict[str, Any]] = {}
    for area, s in stats.items():
        rates[area] = {
            "total": s["total"],
            "success": s["success"],
            "rate": s["success"] / s["total"] if s["total"] > 0 else 0.0,
        }
    return rates


async def get_institution_response_rates(session: AsyncSession) -> Dict[str, Dict[str, Any]]:
    """Calculate response rates grouped by institution."""
    from db.models import OutcomeSignalModel, SupervisorModel
    stmt = select(OutcomeSignalModel.outcome, SupervisorModel.institution).join(
        SupervisorModel, OutcomeSignalModel.supervisor_id == SupervisorModel.id
    )
    res = await session.execute(stmt)
    rows = res.all()

    stats: Dict[str, Dict[str, int]] = {}
    for outcome, inst in rows:
        if not inst:
            continue
        is_success = outcome.upper() in ("ADMIT", "INTERVIEW")
        if inst not in stats:
            stats[inst] = {"total": 0, "success": 0}
            stats[inst]["total"] += 1
            if is_success:
                stats[inst]["success"] += 1

    rates: Dict[str, Dict[str, Any]] = {}
    for inst, s in stats.items():
        rates[inst] = {
            "total": s["total"],
            "success": s["success"],
            "rate": s["success"] / s["total"] if s["total"] > 0 else 0.0,
        }
    return rates

