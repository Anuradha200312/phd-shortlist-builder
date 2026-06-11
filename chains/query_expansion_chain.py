"""
query_expansion_chain.py — Expand student research interests into search queries.

Used by: ingest_node
Input: StudentProfile (research_interests, education, publications)
Output: Expanded list of search queries for data source APIs
"""
from __future__ import annotations
import json
import structlog
from typing import Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from llm.providers import build_llm_chain

logger = structlog.get_logger()


class QueryExpansionOutput(BaseModel):
    """LLM output for query expansion."""
    
    queries: list[str] = Field(
        description="Expanded search queries (10-20 queries)"
    )
    reasoning: Optional[str] = Field(
        description="Brief reasoning for query selection",
        default=None
    )


def build_query_expansion_chain():
    """
    Build LCEL chain for query expansion.
    
    Input: {research_interests, education, publications_text}
    Output: {queries: [...], reasoning: "..."}
    """
    prompt = PromptTemplate(
        input_variables=["research_interests", "education_text", "publications_text"],
        template="""You are an expert research librarian helping a PhD student find suitable advisors.

The student's research interests are: {research_interests}

Their educational background includes:
{education_text}

Sample publications/projects:
{publications_text}

Based on this profile, generate 15-20 search queries that will help find relevant PhD supervisors in academic databases.

Requirements:
1. Queries should cover the student's main research topics
2. Include specific keywords from papers and thesis titles
3. Add related/adjacent research areas
4. Include both broad and specific queries
5. Use terminology common in academic databases

Return ONLY valid JSON with no markdown formatting:
{{"queries": ["query1", "query2", ...], "reasoning": "brief explanation"}}
""",
    )
    
    llm_chain = build_llm_chain(temperature=0.3, max_tokens=1024)
    parser = JsonOutputParser(pydantic_object=QueryExpansionOutput)
    
    chain = prompt | llm_chain | parser
    return chain


async def expand_queries(profile: dict) -> list[str]:
    """Expand student profile into search queries."""
    logger.info("query_expansion_start")
    
    try:
        chain = build_query_expansion_chain()
        
        # Format input
        interests = ", ".join(profile.get("research_interests", []))
        education = "\n".join([
            f"- {e.get('degree')} in {e.get('institution')} ({e.get('thesis_title', 'N/A')})"
            for e in profile.get("education", [])
        ])
        publications = "\n".join([
            f"- {p.get('title')} ({p.get('venue', 'N/A')} {p.get('year', '')})"
            for p in profile.get("publications", [])[:5]  # Top 5
        ])
        
        result = await chain.ainvoke({
            "research_interests": interests or "Not specified",
            "education_text": education or "Not specified",
            "publications_text": publications or "Not specified",
        })
        
        queries = result["queries"]
        logger.info(
            "query_expansion_complete",
            queries_count=len(queries),
            reasoning=result.get("reasoning")
        )
        
        return queries
    
    except Exception as e:
        logger.error("query_expansion_failed", error=str(e))
        # Fallback: use raw interests as queries
        return profile.get("research_interests", [])[:10]
