#!/usr/bin/env python3
"""PhD Shortlist Builder — CLI entry point (LangGraph-powered pipeline)."""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path

import typer
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

app = typer.Typer(
    name="phd-shortlist-builder",
    help="Generate PhD supervisor shortlists using LangChain + LangGraph.",
)


async def _run_pipeline(profile_path: Path, output_dir: Path, max_results: int):
    """Internal async pipeline runner."""
    from graph.pipeline_graph import build_pipeline_graph
    from graph.state import create_initial_state

    # Load student profile
    profile_text = profile_path.read_text(encoding="utf-8")
    student_profile = json.loads(profile_text)
    logger.info(
        "profile_loaded",
        student_id=student_profile.get("student_id"),
        interests=student_profile.get("research_interests"),
        countries=student_profile.get("target_countries"),
    )

    # Create pipeline
    run_id = str(uuid.uuid4())[:8]
    graph = build_pipeline_graph()
    initial_state = create_initial_state(student_profile, run_id)

    logger.info("pipeline_starting", run_id=run_id, nodes=9)

    # Run
    config = {"configurable": {"thread_id": run_id}}
    final_state = await graph.ainvoke(initial_state, config=config)

    # Ensure output dir exists
    output_dir.mkdir(parents=True, exist_ok=True)

    shortlist_count = len(final_state.get("audited_shortlist", []))
    logger.info(
        "pipeline_complete",
        run_id=run_id,
        shortlist_count=shortlist_count,
        output_dir=str(output_dir),
    )

    return final_state


@app.command()
def run(
    profile: Path = typer.Option(
        ...,
        "--profile",
        "-p",
        help="Path to student profile JSON file",
        exists=True,
        readable=True,
    ),
    output: Path = typer.Option(
        "sample_output/",
        "--output",
        "-o",
        help="Output directory for shortlist JSON",
    ),
    max_results: int = typer.Option(
        100,
        "--max-results",
        "-n",
        help="Maximum number of supervisors in shortlist",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable debug logging",
    ),
):
    """Generate a PhD supervisor shortlist for a student profile."""
    typer.echo("=" * 60)
    typer.echo("  PhD Shortlist Builder v1.0.0")
    typer.echo("  Powered by LangChain + LangGraph")
    typer.echo("=" * 60)
    typer.echo()

    start = datetime.now()
    final_state = asyncio.run(_run_pipeline(profile, output, max_results))
    elapsed = (datetime.now() - start).total_seconds()

    shortlist_count = len(final_state.get("audited_shortlist", []))
    student_id = final_state["student_profile"].get("student_id", "unknown")

    typer.echo(f"[*] Shortlist generated: {shortlist_count} supervisors")
    typer.echo(f"[*] Output saved:        sample_output/{student_id}.json")
    typer.echo(f"[*] Duration:            {elapsed:.1f}s")
    typer.echo()


@app.command()
def health():
    """Check system health (LLM providers, database, etc.)."""
    typer.echo("Checking system health...")

    checks = {"python": "OK"}

    # Check Groq API key
    try:
        from config.settings import get_settings
        settings = get_settings()
        if settings.groq_api_key and settings.groq_api_key != "gsk_your_groq_api_key_here":
            checks["groq_api_key"] = "Configured"
        else:
            checks["groq_api_key"] = "Not set (check .env GROQ_API_KEY)"
    except Exception as e:
        checks["groq_api_key"] = f"Error: {e}"

    for name, status in checks.items():
        typer.echo(f"  {name}: {status}")


if __name__ == "__main__":
    app()
