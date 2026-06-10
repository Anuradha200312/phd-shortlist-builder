"""LangGraph pipeline definition — 9-node StateGraph with conditional routing."""
from __future__ import annotations
from langgraph.graph import StateGraph, END
from graph.state import ShortlistState
from graph.nodes.ingest_node import ingest_node
from graph.nodes.retrieve_node import retrieve_node
from graph.nodes.resolve_node import resolve_node
from graph.nodes.verify_pi_node import verify_pi_node
from graph.nodes.score_node import score_node
from graph.nodes.enrich_node import enrich_node
from graph.nodes.validate_node import validate_node
from graph.nodes.audit_node import audit_node
from graph.nodes.output_node import output_node
from graph.edges import should_retry_retrieval


def build_pipeline_graph(checkpointer=None):
    """
    Build the 9-node LangGraph pipeline.

    Node flow:
        ingest → retrieve → resolve → verify_pi
                                         │
                    ┌────────────────────┤ (conditional edge)
                    │                    │
               retrieve (retry)    score → enrich → validate → audit → output → END
    """
    builder = StateGraph(ShortlistState)

    # Register all 9 nodes
    builder.add_node("ingest_node", ingest_node)
    builder.add_node("retrieve_node", retrieve_node)
    builder.add_node("resolve_node", resolve_node)
    builder.add_node("verify_pi_node", verify_pi_node)
    builder.add_node("score_node", score_node)
    builder.add_node("enrich_node", enrich_node)
    builder.add_node("validate_node", validate_node)
    builder.add_node("audit_node", audit_node)
    builder.add_node("output_node", output_node)

    # Linear edges
    builder.set_entry_point("ingest_node")
    builder.add_edge("ingest_node", "retrieve_node")
    builder.add_edge("retrieve_node", "resolve_node")
    builder.add_edge("resolve_node", "verify_pi_node")

    # Conditional edge: retry retrieval if < 50 candidates
    builder.add_conditional_edges(
        "verify_pi_node",
        should_retry_retrieval,
        {
            "retrieve_node": "retrieve_node",
            "score_node": "score_node",
        },
    )

    # Continue linear flow after score
    builder.add_edge("score_node", "enrich_node")
    builder.add_edge("enrich_node", "validate_node")
    builder.add_edge("validate_node", "audit_node")
    builder.add_edge("audit_node", "output_node")
    builder.add_edge("output_node", END)

    # Compile
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer

    return builder.compile(**compile_kwargs)
