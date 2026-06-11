"""
why_match_chain.py — Generate personalized why_match explanations.

Used by: enrich_node
Input: CandidateSupervisor + StudentProfile
Output: why_match (str, 200-400 words with grounded evidence)
"""
from __future__ import annotations
import structlog
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm.providers import build_llm_chain

logger = structlog.get_logger()


def build_why_match_chain():
    """
    Build LCEL chain for why_match generation.
    
    Input: {supervisor_name, supervisor_papers, supervisor_grants, supervisor_areas,
            student_interests, student_education, student_publications}
    Output: why_match (str)
    """
    prompt = PromptTemplate(
        input_variables=[
            "supervisor_name",
            "supervisor_institution",
            "supervisor_papers",
            "supervisor_grants",
            "supervisor_areas",
            "student_interests",
            "student_education",
            "student_publications",
        ],
        template="""Generate a personalized explanation of why this supervisor is a good match for this PhD student.

SUPERVISOR:
Name: {supervisor_name}
Institution: {supervisor_institution}
Research Areas: {supervisor_areas}

Recent Papers (top 5):
{supervisor_papers}

Grants & Funding:
{supervisor_grants}

STUDENT:
Research Interests: {student_interests}

Education:
{student_education}

Publications/Projects:
{student_publications}

TASK:
Write a 200-400 word personalized explanation of why this supervisor is a good match for this student.

Requirements:
1. Be specific: reference actual papers, grants, shared interests
2. Show alignment between supervisor's work and student's interests
3. Mention relevant metrics (h-index, citation count) where available
4. Highlight collaborative opportunities or shared expertise
5. Consider the institution and research environment
6. Be honest: if match is weak, explain why anyway
7. Tone: professional, encouraging, but realistic

Start with the strongest connection and build from there.
Do not use phrases like "This supervisor would be a good fit because..." Be direct.
Do not mention tier, rank, or scoring.
Do not include claims about the student's future success.

Generate only the why_match text, no JSON formatting:
""",
    )
    
    llm_chain = build_llm_chain(temperature=0.5, max_tokens=1024)
    parser = StrOutputParser()
    
    chain = prompt | llm_chain | parser
    return chain


async def generate_why_match(
    candidate: dict,
    student_profile: dict
) -> str:
    """
    Generate why_match explanation for a candidate-student pair.
    """
    logger.info(
        "why_match_generation_start",
        candidate=candidate.get("name")
    )
    
    try:
        chain = build_why_match_chain()
        
        # Format candidate papers
        papers_text = "\n".join([
            f"- {p.get('title')} ({p.get('venue', 'N/A')} {p.get('year', '')})"
            for p in candidate.get("papers", [])[:5]
        ])
        
        # Format candidate grants
        grants_text = "\n".join([
            f"- {g.get('title')} ({g.get('funder', 'Unknown')} {g.get('start_year', '')}-{g.get('end_year', '')})"
            for g in candidate.get("grants", [])[:3]
        ])
        
        # Format student education
        education_text = "\n".join([
            f"- {e.get('degree')} from {e.get('institution')} "
            f"(thesis: {e.get('thesis_title', 'N/A')})"
            for e in student_profile.get("education", [])
        ])
        
        # Format student publications
        publications_text = "\n".join([
            f"- {p.get('title')} ({p.get('venue', 'N/A')} {p.get('year', '')})"
            for p in student_profile.get("publications", [])[:3]
        ])
        
        why_match = await chain.ainvoke({
            "supervisor_name": candidate.get("name"),
            "supervisor_institution": candidate.get("institution"),
            "supervisor_papers": papers_text or "No papers available",
            "supervisor_grants": grants_text or "No grants available",
            "supervisor_areas": ", ".join(candidate.get("research_areas", [])) or "Not specified",
            "student_interests": ", ".join(student_profile.get("research_interests", [])) or "Not specified",
            "student_education": education_text or "Not specified",
            "student_publications": publications_text or "Not specified",
        })
        
        logger.info(
            "why_match_generation_complete",
            length=len(why_match),
            candidate=candidate.get("name")
        )
        
        return why_match
    
    except Exception as e:
        logger.error("why_match_generation_failed", error=str(e))
        # Fallback: simple match explanation
        areas = ", ".join(candidate.get("research_areas", [])[:3])
        return f"{candidate.get('name')} has expertise in {areas}, which aligns with your research interests."


async def generate_why_match_batch(
    candidates: list[dict],
    student_profile: dict,
    concurrency: int = 10
) -> dict[str, str]:
    """
    Generate why_match for multiple candidates concurrently.
    
    Args:
        candidates: List of candidate supervisor dicts
        student_profile: Student profile dict
        concurrency: Max concurrent LLM calls (default 10 to manage rate limits)
    
    Returns:
        {candidate_id: why_match_text}
    """
    import asyncio
    
    logger.info(
        "why_match_batch_start",
        count=len(candidates),
        concurrency=concurrency
    )
    
    results = {}
    semaphore = asyncio.Semaphore(concurrency)
    
    async def generate_with_semaphore(candidate):
        async with semaphore:
            why_match = await generate_why_match(candidate, student_profile)
            return candidate.get("id"), why_match
    
    tasks = [generate_with_semaphore(c) for c in candidates]
    
    try:
        batch_results = await asyncio.gather(*tasks)
        results = dict(batch_results)
        logger.info("why_match_batch_complete", success=len(results))
    except Exception as e:
        logger.error("why_match_batch_failed", error=str(e))
    
    return results
