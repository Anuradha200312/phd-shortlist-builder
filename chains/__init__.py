"""
chains — LangChain LCEL chain definitions for the pipeline.

Each chain is a reusable, composable component that can be invoked independently
or as part of a larger pipeline.
"""

from .query_expansion_chain import expand_queries, build_query_expansion_chain
from .domain_check_chain import check_domain_two_layer, build_domain_check_chain
from .pi_verify_chain import verify_pi_status, build_pi_verify_chain
from .why_match_chain import generate_why_match, generate_why_match_batch, build_why_match_chain
from .confidence_breakdown_chain import build_confidence_breakdown

__all__ = [
    # Query Expansion
    "expand_queries",
    "build_query_expansion_chain",
    
    # Domain Check
    "check_domain_two_layer",
    "build_domain_check_chain",
    
    # PI Verification
    "verify_pi_status",
    "build_pi_verify_chain",
    
    # Why Match
    "generate_why_match",
    "generate_why_match_batch",
    "build_why_match_chain",
    
    # Confidence Breakdown
    "build_confidence_breakdown",
]
