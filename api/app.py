"""FastAPI application — PhD Shortlist Builder API."""
from __future__ import annotations
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.indexing import router as indexing_router

app = FastAPI(
    title="PhD Shortlist Builder API",
    description="AI-powered PhD supervisor shortlist generation using LangChain + LangGraph",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(indexing_router)


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "components": {
            "api": "up",
            "pipeline": "ready",
        },
    }
