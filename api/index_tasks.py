"""In-memory task registry for background indexing jobs.

This is intentionally simple and process-local. For production use a durable
store (Redis, Postgres, etc.) and a proper background worker queue.
"""
import time
import uuid
from typing import Dict, Any, Optional, List

_TASKS: Dict[str, Dict[str, Any]] = {}


def create_task(candidate_count: int) -> str:
    tid = str(uuid.uuid4())
    _TASKS[tid] = {
        "task_id": tid,
        "status": "pending",
        "candidates": candidate_count,
        "created_at": time.time(),
        "started_at": None,
        "finished_at": None,
        "error": None,
    }
    return tid


def set_running(task_id: str) -> None:
    t = _TASKS.get(task_id)
    if not t:
        return
    t["status"] = "running"
    t["started_at"] = time.time()


def set_done(task_id: str) -> None:
    t = _TASKS.get(task_id)
    if not t:
        return
    t["status"] = "done"
    t["finished_at"] = time.time()


def set_failed(task_id: str, error: str) -> None:
    t = _TASKS.get(task_id)
    if not t:
        return
    t["status"] = "failed"
    t["error"] = error
    t["finished_at"] = time.time()


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    return _TASKS.get(task_id)


def list_tasks(limit: int = 50) -> List[Dict[str, Any]]:
    """Return a list of recent tasks ordered by created_at desc."""
    tasks = list(_TASKS.values())
    tasks_sorted = sorted(tasks, key=lambda t: t.get("created_at", 0), reverse=True)
    return tasks_sorted[:limit]
