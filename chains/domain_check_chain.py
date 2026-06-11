"""
domain_check_chain.py — Two-layer domain check (keyword blacklist → LLM).

Used by: resolve_node
Input: CandidateSupervisor (papers, research_areas)
Output: domain_confidence score (0.0-1.0) + contamination flags
"""
from __future__ import annotations
import structlog
from typing import Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from llm.providers import build_llm_chain, get_ollama_llm

logger = structlog.get_logger()


class DomainCheckOutput(BaseModel):
    """LLM output for domain check."""
    
    is_related: bool = Field(
        description="True if supervisor's work is related to student's domain"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score (0.0-1.0)"
    )
    reasoning: str = Field(
        description="Brief reasoning for decision"
    )


# ────────────────────────────────────────────────────────────────────────────
# Layer 1: Keyword Blacklist (fast, no LLM)
# ────────────────────────────────────────────────────────────────────────────

# Keywords that indicate wrong domain (case-insensitive)
DOMAIN_BLACKLIST_KEYWORDS = {
    "music": ["audio", "speech", "voice", "instrument", "composition"],
    "biology": ["cell", "gene", "protein", "organism", "dna"],
    "chemistry": ["molecule", "reaction", "compound", "bond", "catalyst"],
    "medicine": ["clinical", "patient", "treatment", "disease", "diagnosis"],
    "physics": ["particle", "quantum", "photon", "wave", "relativistic"],
    "philosophy": ["ethics", "metaphysics", "epistemology", "ontology"],
}

# Venues that indicate non-CS domains
NON_CS_VENUES = {
    "Nature", "Science", "JAMA", "Lancet", "Cell",  # Biology/Medicine
    "Nature Physics", "Physical Review", "Science Advances",  # Physics
    "Organic Letters", "Journal of Organic Chemistry",  # Chemistry
    "Philosophy of Science", "Journal of Philosophy",  # Philosophy
    "Music Perception", "Journal of Music Technology",  # Music
}


def check_keyword_blacklist(
    candidate: dict,
    student_interests: list[str],
    target_domain: str = "computer_science"
) -> tuple[bool, str]:
    """
    Layer 1: Quick keyword blacklist check (no LLM).
    Returns: (passed_check, reason)
    """
    candidate_papers = candidate.get("papers", [])
    candidate_areas = candidate.get("research_areas", [])
    
    # Check research areas
    for area in candidate_areas:
        area_lower = area.lower()
        for domain, keywords in DOMAIN_BLACKLIST_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in area_lower:
                    return False, f"Keyword match: '{area}' contains '{keyword}' (domain: {domain})"
    
    # Check paper venues (quick heuristic)
    for paper in candidate_papers[:5]:  # Check first 5 papers
        venue = paper.get("venue", "").lower()
        for non_cs_venue in NON_CS_VENUES:
            if non_cs_venue.lower() in venue:
                return False, f"Non-CS venue detected: {paper.get('venue')}"
    
    return True, "Passed keyword blacklist"


# ────────────────────────────────────────────────────────────────────────────
# Layer 2: LLM Domain Check (expensive, only for ambiguous cases)
# ────────────────────────────────────────────────────────────────────────────

def build_domain_check_chain():
    """
    Build LCEL chain for LLM domain check.
    
    Input: {supervisor_profile, student_interests}
    Output: {is_related: bool, confidence: float, reasoning: str}
    """
    prompt = PromptTemplate(
        input_variables=["supervisor_name", "supervisor_areas", "supervisor_recent_papers", "student_interests"],
        template="""You are evaluating whether a supervisor's research aligns with a student's interests.

Supervisor: {supervisor_name}
Research Areas: {supervisor_areas}
Recent Papers (titles):
{supervisor_recent_papers}

Student's Research Interests:
{student_interests}

Task: Determine if the supervisor's work is related to the student's domain.

Consider:
1. Topic alignment (are the research areas overlapping?)
2. Methodological alignment (are similar techniques used?)
3. Application domain alignment

Be strict: if there's no clear connection, mark as unrelated.

Return only valid JSON with no markdown:
{{"is_related": true/false, "confidence": 0.0-1.0, "reasoning": "..."}}
""",
    )
    
    # Use Ollama for bulk domain checks (saves Groq budget)
    llm_chain = get_ollama_llm(temperature=0.0)
    parser = PydanticOutputParser(pydantic_object=DomainCheckOutput)
    
    chain = prompt | llm_chain | parser
    return chain


async def check_domain_llm(
    candidate: dict,
    student_profile: dict
) -> tuple[bool, float]:
    """
    Layer 2: LLM domain check (only called if Layer 1 passes).
    Returns: (is_related, confidence_score)
    """
    logger.info("domain_check_llm_start", candidate=candidate.get("name"))
    
    try:
        chain = build_domain_check_chain()
        
        # Format input
        areas = ", ".join(candidate.get("research_areas", [])[:5])
        papers = "\n".join([
            f"- {p.get('title')}"
            for p in candidate.get("papers", [])[:3]
        ])
        interests = ", ".join(student_profile.get("research_interests", []))
        
        result = await chain.ainvoke({
            "supervisor_name": candidate.get("name"),
            "supervisor_areas": areas or "Not specified",
            "supervisor_recent_papers": papers or "Not specified",
            "student_interests": interests or "Not specified",
        })
        
        logger.info(
            "domain_check_llm_complete",
            is_related=result["is_related"],
            confidence=result["confidence"],
        )
        
        return result["is_related"], result["confidence"]
    
    except Exception as e:
        logger.error("domain_check_llm_failed", error=str(e))
        # Fallback: accept candidate if Layer 1 passed
        return True, 0.5


# ────────────────────────────────────────────────────────────────────────────
# Main two-layer check
# ────────────────────────────────────────────────────────────────────────────

async def check_domain_two_layer(
    candidate: dict,
    student_profile: dict
) -> dict:
    """
    Two-layer domain check:
    1. Keyword blacklist (fast, no cost)
    2. LLM verification (slow, if Layer 1 passes)
    
    Returns: {
        passed: bool,
        domain_confidence: float,
        layer: "blacklist" | "llm",
        reason: str
    }
    """
    # Layer 1: Keyword blacklist
    passed, reason = check_keyword_blacklist(
        candidate,
        student_profile.get("research_interests", [])
    )
    
    if not passed:
        logger.info("domain_check_blocked_by_blacklist", reason=reason)
        return {
            "passed": False,
            "domain_confidence": 0.0,
            "layer": "blacklist",
            "reason": reason,
            "contamination_risk": "domain_blacklist_blocked",
        }
    
    # Layer 2: LLM check (for ambiguous cases)
    is_related, confidence = await check_domain_llm(candidate, student_profile)
    
    return {
        "passed": is_related and confidence >= 0.5,
        "domain_confidence": confidence,
        "layer": "llm",
        "reason": "LLM domain check passed" if is_related else "LLM rejected candidate",
        "contamination_risk": None if is_related else "domain_llm_rejected",
    }
