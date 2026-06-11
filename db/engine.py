"""Async database engine and session factory (PostgreSQL + asyncpg)."""
from __future__ import annotations
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import get_settings

# Lazy singletons — created on first use to avoid import-time crashes
# when asyncpg is not installed or DATABASE_URL is not configured.
_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_pre_ping=True,
            echo=settings.debug,
        )
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


def AsyncSessionLocal():
    """Return a new async session (lazy engine init)."""
    return _get_session_factory()()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async session and auto-closes."""
    async with _get_session_factory()() as session:
        yield session
