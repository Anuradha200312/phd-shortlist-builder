"""Build a Chroma index from a JSON file of candidates.

Usage:
    python scripts/build_chroma_index.py path/to/candidates.json

The JSON file should contain a list of candidate objects compatible with the pipeline.
This script is best-effort: if `chromadb` or `sentence-transformers` are not installed,
the function will silently fall back and exit without error.
"""
import json
import sys
from pathlib import Path

from vectorstore.chroma_store import get_chroma_store


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python scripts/build_chroma_index.py path/to/candidates.json")
        return 2

    path = Path(argv[0])
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        print(f"Failed to read JSON: {exc}")
        return 1

    if not isinstance(data, list):
        print("JSON must be a list of candidate objects")
        return 1

    store = get_chroma_store()
    try:
        # index_candidates is async; run synchronously here
        import asyncio

        asyncio.run(store.index_candidates(data))
        print(f"Indexed {len(data)} candidates (best-effort)")
    except Exception as exc:
        print(f"Indexing failed (non-fatal): {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
