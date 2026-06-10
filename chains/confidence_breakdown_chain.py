"""
confidence_breakdown_chain.py — Build 6-signal confidence breakdown.

Used by: score_node
Input: CandidateSupervisor + StudentProfile
Output: ConfidenceBreakdown (6 signals with total score)
"""
from __future__ import annotations
import structlog
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class ConfidenceBreakdown(BaseModel):
    """6-signal confidence breakdown."""
    
    orcid_verified: bool
    orcid_score: float = Field(ge=0.0, le=1.0)
    
    faculty_page_confirmed: Optional[bool]
    faculty_score: float = Field(ge=0.0, le=1.0)
    
    paper_topic_overlap: float = Field(ge=0.0, le=1.0)
    overlap_score: float = Field(ge=0.0, le=1.0)
    
    recent_activity: bool
    recency_score: float = Field(ge=0.0, le=1.0)
    
    eligibility_clear: bool
    eligibility_score: float = Field(ge=0.0, le=1.0)
    
    h_index: int
    hindex_score: float = Field(ge=0.0, le=1.0)
    
    total_score: float = Field(ge=0.0, le=1.0)


# ────────────────────────────────────────────────────────────────────────────
# Signal 1: ORCID Verification (20% weight)
# ────────────────────────────────────────────────────────────────────────────

def compute_orcid_score(candidate: dict) -> tuple[bool, float]:
    """
    Signal 1: ORCID verified (gold standard for identity).
    Returns: (orcid_verified, orcid_score)
    """
    orcid = candidate.get("orcid")
    
    if orcid and len(orcid) >= 15:  # ORCID format: XXXX-XXXX-XXXX-XXXC
        return True, 1.0
    else:
        return False, 0.0


# ────────────────────────────────────────────────────────────────────────────
# Signal 2: Faculty Page Confirmation (15% weight)
# ────────────────────────────────────────────────────────────────────────────

def compute_faculty_score(candidate: dict) -> tuple[Optional[bool], float]:
    """
    Signal 2: Faculty page confirmation (PI status).
    Returns: (faculty_page_confirmed, faculty_score)
    """
    faculty_confirmed = candidate.get("faculty_page_confirmed")
    
    if faculty_confirmed is None:
        # Not checked yet (assume partial credit)
        return None, 0.5
    elif faculty_confirmed:
        return True, 1.0
    else:
        return False, 0.0


# ────────────────────────────────────────────────────────────────────────────
# Signal 3: Topic Overlap (30% weight) — PRIMARY SIGNAL
# ────────────────────────────────────────────────────────────────────────────

def compute_overlap_score(candidate: dict, student_interests: list[str]) -> float:
    """
    Signal 3: Research topic overlap (embedding similarity).
    Returns: overlap_score (0.0-1.0)
    """
    # Typically set by score_node using ChromaDB/embeddings
    # For now, use paper count as proxy
    overlap = candidate.get("embedding_similarity", 0.0)
    
    if overlap > 0:
        return overlap
    
    # Fallback heuristic: if candidate has papers + student has interests
    papers = len(candidate.get("papers", []))
    interests = len(student_interests)
    
    if papers > 0 and interests > 0:
        # Rough heuristic: assume 40% overlap if fields exist
        return 0.4
    
    return 0.0


# ────────────────────────────────────────────────────────────────────────────
# Signal 4: Recency (15% weight)
# ────────────────────────────────────────────────────────────────────────────

def compute_recency_score(candidate: dict) -> tuple[bool, float]:
    """
    Signal 4: Recent activity (last paper < 5 years old).
    Returns: (recent_activity, recency_score)
    """
    last_paper_year = candidate.get("last_paper_year")
    current_year = datetime.now().year
    
    if not last_paper_year:
        return False, 0.0
    
    years_ago = current_year - last_paper_year
    
    if years_ago <= 2:
        return True, 1.0
    elif years_ago <= 5:
        return True, 0.5
    else:
        return False, 0.2  # Stale, but give slight credit


# ────────────────────────────────────────────────────────────────────────────
# Signal 5: Eligibility (10% weight)
# ────────────────────────────────────────────────────────────────────────────

def compute_eligibility_score(
    candidate: dict,
    target_countries: list[str]
) -> tuple[bool, float]:
    """
    Signal 5: Eligibility (country match, funding availability).
    Returns: (eligibility_clear, eligibility_score)
    """
    country = candidate.get("country", "")
    
    # Country match is hard constraint (must match if specified)
    if target_countries and country not in target_countries:
        return False, 0.0
    
    # Check if open positions exist
    positions = candidate.get("open_positions", [])
    if positions:
        # Check if any have international openness
        has_intl = any(
            "open_to_international" in p.get("eligibility_flags", [])
            for p in positions
        )
        if has_intl:
            return True, 1.0
        else:
            return True, 0.7  # Positions exist but not explicitly international
    
    # No explicit positions, but country matches
    return True if not target_countries else (country in target_countries), 0.6


# ────────────────────────────────────────────────────────────────────────────
# Signal 6: H-Index (10% weight)
# ────────────────────────────────────────────────────────────────────────────

def compute_hindex_score(candidate: dict) -> tuple[int, float]:
    """
    Signal 6: H-index (research impact).
    Returns: (h_index, hindex_score normalized to 0-1)
    """
    h_index = candidate.get("h_index", 0)
    
    # Normalize: 0 → 0.0 | 10 → 0.5 | 50+ → 1.0
    if h_index >= 50:
        return h_index, 1.0
    elif h_index >= 10:
        return h_index, min(h_index / 50, 1.0)
    else:
        return h_index, max(h_index / 10, 0.0)


# ────────────────────────────────────────────────────────────────────────────
# Main computation
# ────────────────────────────────────────────────────────────────────────────

def build_confidence_breakdown(
    candidate: dict,
    student_profile: dict
) -> ConfidenceBreakdown:
    """
    Build 6-signal confidence breakdown.
    
    Weights:
    - ORCID: 20%
    - Faculty: 15%
    - Topic Overlap: 30% (PRIMARY)
    - Recency: 15%
    - Eligibility: 10%
    - H-Index: 10%
    """
    logger.info(
        "confidence_breakdown_start",
        candidate=candidate.get("name")
    )
    
    # Signal 1: ORCID
    orcid_verified, orcid_score = compute_orcid_score(candidate)
    
    # Signal 2: Faculty page
    faculty_confirmed, faculty_score = compute_faculty_score(candidate)
    
    # Signal 3: Topic overlap
    overlap_score = compute_overlap_score(
        candidate,
        student_profile.get("research_interests", [])
    )
    
    # Signal 4: Recency
    recent_activity, recency_score = compute_recency_score(candidate)
    
    # Signal 5: Eligibility
    eligibility_clear, eligibility_score = compute_eligibility_score(
        candidate,
        student_profile.get("target_countries", [])
    )
    
    # Signal 6: H-Index
    h_index, hindex_score = compute_hindex_score(candidate)
    
    # Weighted total
    total_score = (
        orcid_score * 0.20 +
        faculty_score * 0.15 +
        overlap_score * 0.30 +
        recency_score * 0.15 +
        eligibility_score * 0.10 +
        hindex_score * 0.10
    )
    
    breakdown = ConfidenceBreakdown(
        orcid_verified=orcid_verified,
        orcid_score=orcid_score,
        faculty_page_confirmed=faculty_confirmed,
        faculty_score=faculty_score,
        paper_topic_overlap=overlap_score,
        overlap_score=overlap_score,
        recent_activity=recent_activity,
        recency_score=recency_score,
        eligibility_clear=eligibility_clear,
        eligibility_score=eligibility_score,
        h_index=h_index,
        hindex_score=hindex_score,
        total_score=total_score,
    )
    
    logger.info(
        "confidence_breakdown_complete",
        candidate=candidate.get("name"),
        total_score=total_score,
    )
    
    return breakdown
