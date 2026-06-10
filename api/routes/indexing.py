from __future__ import annotations
import asyncio
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException

from vectorstore.chroma_store import get_chroma_store
from api.index_tasks import create_task, set_running, set_done, set_failed, get_task

router = APIRouter()


@router.post("/api/v1/index_chroma")
async def index_chroma(candidates: List[Dict[str, Any]]):
    """Trigger best-effort indexing of candidates into Chroma.

    Returns a `task_id` which can be polled at `/api/v1/index_status/{task_id}`.
    """
    task_id = create_task(len(candidates))

    async def _run_index():
        store = get_chroma_store()
        try:
            set_running(task_id)
            await store.index_candidates(candidates)
            set_done(task_id)
        except Exception as exc:
            set_failed(task_id, str(exc))

    try:
        asyncio.create_task(_run_index())
    except Exception as exc:
        set_failed(task_id, str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    return {"status": "accepted", "task_id": task_id}


@router.get("/api/v1/index_status/{task_id}")
async def index_status(task_id: str):
    t = get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    return t


@router.get("/api/v1/index_status")
async def index_status_list(limit: int = 50):
    """List recent indexing tasks (most recent first)."""
    from api.index_tasks import list_tasks

    return list_tasks(limit=limit)
