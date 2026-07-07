from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models import Base

_DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./data/ai_career_agent.db"

_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def configure(
    url: str = _DEFAULT_DATABASE_URL,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_pre_ping: bool = True,
    pool_recycle: int = 3600,
) -> None:
    global _engine, _async_session_maker
    async_url = _ensure_async_driver(url)
    _engine = create_async_engine(
        async_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=pool_recycle,
    )
    _async_session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def _ensure_async_driver(url: str) -> str:
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _ensure_configured() -> None:
    if _engine is None:
        try:
            from app.core.settings import settings

            _s = settings
            configure(
                url=_s.database.url,
                echo=_s.database.echo,
                pool_size=_s.database.pool_size,
                max_overflow=_s.database.max_overflow,
                pool_pre_ping=_s.database.pool_pre_ping,
                pool_recycle=_s.database.pool_recycle,
            )
        except (ImportError, AttributeError, Exception):
            configure()


async def create_tables() -> None:
    _ensure_configured()
    async with _engine.begin() as conn:  # type: ignore[union-attr]
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    _ensure_configured()
    async with _engine.begin() as conn:  # type: ignore[union-attr]
        await conn.run_sync(Base.metadata.drop_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    _ensure_configured()
    session = _async_session_maker()  # type: ignore[misc]
    async with session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_engine_url() -> str:
    _ensure_configured()
    return str(_engine.url)  # type: ignore[union-attr]
