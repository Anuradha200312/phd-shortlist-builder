"""SQLAlchemy ORM models for PostgreSQL — async-compatible."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, Boolean, Numeric, Text, ForeignKey, UniqueConstraint, CheckConstraint, TIMESTAMP
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

TIMESTAMPTZ = TIMESTAMP(timezone=True)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class SupervisorModel(Base):
    __tablename__ = "supervisors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    institution: Mapped[Optional[str]] = mapped_column(String)
    department: Mapped[Optional[str]] = mapped_column(String)
    country: Mapped[Optional[str]] = mapped_column(String)
    email: Mapped[Optional[str]] = mapped_column(String)
    profile_url: Mapped[Optional[str]] = mapped_column(String)
    orcid: Mapped[Optional[str]] = mapped_column(String, unique=True)
    openalex_id: Mapped[Optional[str]] = mapped_column(String, unique=True)
    google_scholar_id: Mapped[Optional[str]] = mapped_column(String)
    h_index: Mapped[Optional[int]] = mapped_column(Integer)
    paper_count: Mapped[Optional[int]] = mapped_column(Integer)
    is_pi_verified: Mapped[Optional[bool]] = mapped_column(Boolean)
    career_stage: Mapped[Optional[str]] = mapped_column(
        String,
        CheckConstraint("career_stage IN ('faculty','postdoc','student','unknown')")
    )
    faculty_page_confirmed: Mapped[Optional[bool]] = mapped_column(Boolean)
    last_paper_year: Mapped[Optional[int]] = mapped_column(Integer)
    research_areas: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), default=[])
    raw_api_payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    fetched_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow)

    # Relationships
    papers: Mapped[list["PaperModel"]] = relationship(
        back_populates="supervisor", cascade="all, delete-orphan"
    )
    grants: Mapped[list["GrantModel"]] = relationship(
        back_populates="supervisor", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("name", "institution", name="uq_supervisor_name_institution"),
    )


class PaperModel(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supervisor_id: Mapped[str] = mapped_column(ForeignKey("supervisors.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    venue: Mapped[Optional[str]] = mapped_column(String)
    year: Mapped[Optional[int]] = mapped_column(Integer)
    doi: Mapped[Optional[str]] = mapped_column(String)
    url: Mapped[Optional[str]] = mapped_column(String)
    citation_count: Mapped[Optional[int]] = mapped_column(Integer)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    fetched_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow)

    supervisor: Mapped["SupervisorModel"] = relationship(back_populates="papers")


class GrantModel(Base):
    __tablename__ = "grants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supervisor_id: Mapped[str] = mapped_column(ForeignKey("supervisors.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    funder: Mapped[Optional[str]] = mapped_column(String)
    amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    start_year: Mapped[Optional[int]] = mapped_column(Integer)
    end_year: Mapped[Optional[int]] = mapped_column(Integer)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    fetched_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow)

    supervisor: Mapped["SupervisorModel"] = relationship(back_populates="grants")


class ShortlistModel(Base):
    __tablename__ = "shortlists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[str] = mapped_column(String, nullable=False)
    output_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    run_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    langgraph_thread_id: Mapped[Optional[str]] = mapped_column(String)
    generated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMPTZ, default=datetime.utcnow
    )

    entries: Mapped[list["ShortlistEntryModel"]] = relationship(
        back_populates="shortlist", cascade="all, delete-orphan"
    )


class ShortlistEntryModel(Base):
    __tablename__ = "shortlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shortlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shortlists.id", ondelete="CASCADE")
    )
    supervisor_id: Mapped[Optional[str]] = mapped_column(ForeignKey("supervisors.id"))
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    tier: Mapped[Optional[str]] = mapped_column(
        String,
        CheckConstraint("tier IN ('reach','target','safety','review_needed')")
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 3))
    confidence_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB)
    why_match: Mapped[Optional[str]] = mapped_column(Text)
    match_dimensions: Mapped[Optional[dict]] = mapped_column(JSONB)
    evidence_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB)
    eligibility_flags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), default=[])
    contamination_risk: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), default=[])
    disambiguation_signals: Mapped[Optional[dict]] = mapped_column(JSONB)
    faculty_page_confirmed: Mapped[Optional[bool]] = mapped_column(Boolean)
    last_paper_year: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow)

    shortlist: Mapped["ShortlistModel"] = relationship(back_populates="entries")


class ContaminationAuditModel(Base):
    __tablename__ = "contamination_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shortlist_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("shortlists.id", ondelete="CASCADE")
    )
    supervisor_id: Mapped[Optional[str]] = mapped_column(String)
    rank: Mapped[Optional[int]] = mapped_column(Integer)
    risk_flags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    stage_caught: Mapped[Optional[str]] = mapped_column(String)
    action_taken: Mapped[Optional[str]] = mapped_column(String)
    logged_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow)


class ApiCacheModel(Base):
    __tablename__ = "api_cache"

    cache_key: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[Optional[str]] = mapped_column(String)
    response_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)


class OutcomeSignalModel(Base):
    __tablename__ = "outcome_signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    supervisor_id: Mapped[str] = mapped_column(String, nullable=False)
    student_id: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)  # 'ADMIT', 'REJECT', 'INTERVIEW'
    details: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow)

