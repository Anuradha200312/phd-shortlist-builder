"""
pi_verify_chain.py — Verify supervisor is faculty PI (not student/postdoc).

Used by: verify_pi_node
Input: CandidateSupervisor
Output: is_pi_verified (bool), contamination_risk (optional str)
"""
from __future__ import annotations
import structlog
from datetime import datetime
from typing import Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from llm.providers import get_ollama_llm

logger = structlog.get_logger()


class PIVerifyOutput(BaseModel):
    """LLM output for PI verification."""
    
    is_faculty: bool = Field(
        description="True if person is faculty/PI (not student/postdoc)"
    )
    career_stage: str = Field(
        description="Career stage: faculty | postdoc | student | unknown"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence of assessment"
    )
    reasoning: str = Field(
        description="Reasoning for assessment"
    )


# ────────────────────────────────────────────────────────────────────────────
# Hard Gate 1: Staleness Check (no LLM needed)
# ────────────────────────────────────────────────────────────────────────────

def check_staleness(candidate: dict) -> tuple[bool, Optional[str]]:
    """
    Check if candidate's data is fresh (last paper < 5 years old).
    Returns: (fresh, reason)
    """
    last_paper_year = candidate.get("last_paper_year")
    
    if not last_paper_year:
        return False, "No publication history found (possibly inactive)"
    
    years_since_last_paper = datetime.now().year - last_paper_year
    
    if years_since_last_paper > 5:
        return False, f"Last paper {years_since_last_paper} years ago (staleness)"
    
    return True, None


# ────────────────────────────────────────────────────────────────────────────
# Hard Gate 2: H-Index Heuristic (no LLM needed)
# ────────────────────────────────────────────────────────────────────────────

def check_heuristic_pi_status(candidate: dict) -> tuple[bool, Optional[str]]:
    """
    Heuristic check using h-index and paper count.
    Intuition: Professors typically have h-index ≥ 10 and ≥ 20 papers
    """
    h_index = candidate.get("h_index", 0)
    paper_count = candidate.get("paper_count", 0)
    
    if h_index < 5 and paper_count < 10:
        return False, f"Likely junior/student (h-index={h_index}, papers={paper_count})"
    
    return True, None


# ────────────────────────────────────────────────────────────────────────────
# Hard Gate 3: Faculty Page Confirmation (would call faculty_directory_tool)
# ────────────────────────────────────────────────────────────────────────────

def check_faculty_page(candidate: dict) -> tuple[bool, Optional[str]]:
    """
    Check if faculty page was confirmed (set by faculty_directory_tool).
    Phase 2: would scrape faculty page to confirm PI status
    """
    faculty_confirmed = candidate.get("faculty_page_confirmed")
    
    if faculty_confirmed is None:
        return True, None  # Not checked yet (assume true for now)
    
    if not faculty_confirmed:
        return False, "Faculty page lookup failed (not found in directory)"
    
    return True, None


# ────────────────────────────────────────────────────────────────────────────
# LLM Fallback: Full Career-Stage Verification
# ────────────────────────────────────────────────────────────────────────────

def build_pi_verify_chain():
    """
    Build LCEL chain for PI career-stage verification.
    
    Input: {supervisor_name, research_summary, recent_papers}
    Output: {is_faculty, career_stage, confidence, reasoning}
    """
    prompt = PromptTemplate(
        input_variables=["supervisor_name", "institution", "h_index", "paper_count", "research_summary", "recent_papers"],
        template="""Assess whether this person is likely a faculty PI or PI-track researcher.

Name: {supervisor_name}
Institution: {institution}
H-Index: {h_index}
Total Papers: {paper_count}

Research Summary:
{research_summary}

Recent Paper Titles:
{recent_papers}

Task: Determine career stage.

Indicators of faculty/PI status:
- Independent research program (multiple areas)
- Mentorship of students (implied by paper count/h-index)
- H-index ≥ 10 typically means established researcher
- Active publications over many years

Indicators of postdoc/student:
- Limited paper count < 10
- Very recent work only (no history)
- Single research area focus

Return only JSON:
{{"is_faculty": true/false, "career_stage": "faculty|postdoc|student|unknown", "confidence": 0.0-1.0, "reasoning": "..."}}
""",
    )
    
    llm_chain = get_ollama_llm(temperature=0.0)
    parser = PydanticOutputParser(pydantic_object=PIVerifyOutput)
    
    chain = prompt | llm_chain | parser
    return chain


async def verify_pi_llm(candidate: dict) -> tuple[bool, str, float]:
    """
    LLM verification of PI status (fallback if heuristics uncertain).
    Returns: (is_faculty, career_stage, confidence)
    """
    logger.info("pi_verify_llm_start", candidate=candidate.get("name"))
    
    try:
        chain = build_pi_verify_chain()
        
        papers = "\n".join([
            f"- {p.get('title')}"
            for p in candidate.get("papers", [])[:5]
        ])
        
        result = await chain.ainvoke({
            "supervisor_name": candidate.get("name"),
            "institution": candidate.get("institution", "Unknown"),
            "h_index": candidate.get("h_index", 0),
            "paper_count": candidate.get("paper_count", 0),
            "research_summary": candidate.get("research_summary", "Not available"),
            "recent_papers": papers or "Not available",
        })
        
        logger.info(
            "pi_verify_llm_complete",
            is_faculty=result["is_faculty"],
            career_stage=result["career_stage"],
        )
        
        return result["is_faculty"], result["career_stage"], result["confidence"]
    
    except Exception as e:
        logger.error("pi_verify_llm_failed", error=str(e))
        # Fallback: assume faculty if heuristics passed
        return True, "unknown", 0.5


# ────────────────────────────────────────────────────────────────────────────
# Main PI verification (multi-gate)
# ────────────────────────────────────────────────────────────────────────────

async def verify_pi_status(candidate: dict) -> dict:
    """
    Multi-gate PI verification:
    1. Staleness check (hard gate)
    2. H-index heuristic (hard gate)
    3. Faculty page confirmation (hard gate)
    4. LLM verification (soft gate, used if uncertain)
    
    Returns: {
        is_pi_verified: bool,
        career_stage: str,
        confidence: float,
        contamination_risk: str or None,
    }
    """
    # Gate 1: Staleness
    fresh, staleness_reason = check_staleness(candidate)
    if not fresh:
        logger.info("pi_verify_rejected_staleness", reason=staleness_reason)
        return {
            "is_pi_verified": False,
            "career_stage": "unknown",
            "confidence": 1.0,
            "contamination_risk": f"staleness_check: {staleness_reason}",
        }
    
    # Gate 2: Heuristic
    heuristic_ok, heuristic_reason = check_heuristic_pi_status(candidate)
    if not heuristic_ok:
        logger.info("pi_verify_rejected_heuristic", reason=heuristic_reason)
        return {
            "is_pi_verified": False,
            "career_stage": "likely_junior",
            "confidence": 0.8,
            "contamination_risk": f"heuristic_check: {heuristic_reason}",
        }
    
    # Gate 3: Faculty page
    faculty_ok, faculty_reason = check_faculty_page(candidate)
    if not faculty_ok:
        logger.info("pi_verify_rejected_faculty_page", reason=faculty_reason)
        return {
            "is_pi_verified": False,
            "career_stage": "unknown",
            "confidence": 1.0,
            "contamination_risk": f"faculty_page_check: {faculty_reason}",
        }
    
    # Gate 4: LLM verification (if heuristics uncertain, or just to confirm)
    is_faculty, career_stage, llm_confidence = await verify_pi_llm(candidate)
    
    return {
        "is_pi_verified": is_faculty,
        "career_stage": career_stage,
        "confidence": llm_confidence,
        "contamination_risk": None if is_faculty else "career_stage_concern",
    }
