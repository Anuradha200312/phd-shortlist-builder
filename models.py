"""Pydantic models for the PhD Shortlist Builder."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


# ─────────────────────────────────────────────
# Input Models
# ─────────────────────────────────────────────

class Education(BaseModel):
    degree: str
    institution: str
    gpa: Optional[str] = None
    thesis_title: Optional[str] = None
    graduation_year: Optional[int] = None


class Publication(BaseModel):
    title: str
    venue: Optional[str] = None
    year: Optional[int] = None
    url: Optional[str] = None
    doi: Optional[str] = None


class Project(BaseModel):
    title: str
    description: str


class TargetIntake(BaseModel):
    semester: str = "Fall"
    year: int


class StudentProfile(BaseModel):
    student_id: str
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    publications: list[Publication] = Field(default_factory=list)
    research_interests: list[str] = Field(default_factory=list)
    target_countries: list[str] = Field(default_factory=list)
    target_intake: Optional[TargetIntake] = None
    intro_call_summary: Optional[str] = None
    resume_text: Optional[str] = None


# ─────────────────────────────────────────────
# Pipeline Internal Models
# ─────────────────────────────────────────────

class Evidence(BaseModel):
    type: str  # "paper" | "grant"
    title: str
    venue: Optional[str] = None
    year: Optional[int] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    funder: Optional[str] = None


class OpenPosition(BaseModel):
    title: str
    url: Optional[str] = None
    deadline: Optional[str] = None
    eligibility_flags: list[str] = Field(default_factory=list)
    source: str = "unknown"


class DisambiguationSignals(BaseModel):
    orcid_verified: bool = False
    faculty_page_confirmed: Optional[bool] = None
    embedding_match: bool = False
    signals_passed: int = 0
    passes_lock: bool = False


class ConfidenceBreakdown(BaseModel):
    orcid_verified: bool = False
    orcid_score: float = 0.0
    faculty_page_confirmed: Optional[bool] = None
    faculty_score: float = 0.0
    paper_topic_overlap: float = 0.0
    overlap_score: float = 0.0
    recent_activity: bool = False
    recency_score: float = 0.0
    eligibility_clear: bool = False
    eligibility_score: float = 0.0
    h_index: int = 0
    hindex_score: float = 0.0
    total_score: float = 0.0


class MatchDimensions(BaseModel):
    research_overlap: float = 0.0
    recent_activity: bool = False
    is_pi_verified: bool = False
    h_index: int = 0
    country_match: bool = True
    domain_confidence: float = 0.0
    last_paper_year: Optional[int] = None


class SupervisorInfo(BaseModel):
    name: str
    institution: str
    department: Optional[str] = None
    country: str
    profile_url: Optional[str] = None
    email: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    openalex_id: Optional[str] = None
    google_scholar_id: Optional[str] = None
    orcid: Optional[str] = None


class CandidateSupervisor(BaseModel):
    """Internal pipeline representation of a supervisor candidate."""
    id: str                                      # openalex:A123 or ss:456
    name: str
    institution: str
    department: Optional[str] = None
    country: str
    email: Optional[str] = None
    profile_url: Optional[str] = None
    orcid: Optional[str] = None
    openalex_id: Optional[str] = None
    google_scholar_id: Optional[str] = None
    h_index: int = 0
    paper_count: int = 0
    last_paper_year: Optional[int] = None
    is_pi_verified: Optional[bool] = None
    career_stage: str = "unknown"
    faculty_page_confirmed: Optional[bool] = None
    research_areas: list[str] = Field(default_factory=list)
    research_summary: Optional[str] = None      # used for embedding
    top_venues: list[str] = Field(default_factory=list)
    papers: list[Evidence] = Field(default_factory=list)
    grants: list[Evidence] = Field(default_factory=list)
    open_positions: list[OpenPosition] = Field(default_factory=list)

    # Quality signals (populated during pipeline)
    embedding_similarity: float = 0.0
    domain_confidence: float = 0.0
    disambiguation_signals: Optional[DisambiguationSignals] = None
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    eligibility_flags: list[str] = Field(default_factory=list)
    contamination_risk: list[str] = Field(default_factory=list)

    # Scoring outputs
    confidence_score: float = 0.0
    tier: str = "target"                         # reach | target | safety | review_needed
    why_match: Optional[str] = None
    rank: Optional[int] = None

    # Data provenance
    source: str = "unknown"                      # semantic_scholar | openalex | nih | ukri
    raw_api_payload: Optional[dict] = None
    fetched_at: Optional[datetime] = None


# ─────────────────────────────────────────────
# Output Models
# ─────────────────────────────────────────────

class ShortlistEntry(BaseModel):
    rank: int
    supervisor: SupervisorInfo
    research_focus: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    why_match: str = ""
    tier: str = "target"
    open_positions: list[OpenPosition] = Field(default_factory=list)
    eligibility_flags: list[str] = Field(default_factory=list)
    contamination_risk: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    match_dimensions: Optional[MatchDimensions] = None


class PipelineMetadata(BaseModel):
    total_candidates_considered: int = 0
    data_sources: list[str] = Field(default_factory=list)
    llm_provider_used: str = ""
    langgraph_run_id: str = ""
    langsmith_trace_url: Optional[str] = None
    run_duration_seconds: float = 0.0
    audit_summary: Optional[dict] = None


class ShortlistOutput(BaseModel):
    student_id: str
    generated_at: str
    pipeline_version: str = "1.0.0"
    shortlist: list[ShortlistEntry] = Field(default_factory=list)
    metadata: PipelineMetadata = Field(default_factory=PipelineMetadata)
