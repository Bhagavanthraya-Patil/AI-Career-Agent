from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models import Base, Company, JobSource


@pytest_asyncio.fixture(scope="session")
async def in_memory_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    in_memory_engine,
) -> AsyncGenerator[AsyncSession, Any]:
    session_factory = async_sessionmaker(
        in_memory_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seed_job_source(db_session: AsyncSession) -> JobSource:
    source = JobSource(name="greenhouse", is_active=True)
    db_session.add(source)
    await db_session.flush()
    return source


@pytest_asyncio.fixture
async def seed_company(db_session: AsyncSession) -> Company:
    company = Company(name="TestCorp")
    db_session.add(company)
    await db_session.flush()
    return company
