from __future__ import annotations

from typing import Optional

from pydantic import Field, model_validator

from . import BaseConfig


class DatabaseSettings(BaseConfig):
    url: str = Field(
        default="sqlite:///./data/ai_career_agent.db",
        description="Database connection URL (SQLite or PostgreSQL)",
    )
    pool_size: int = Field(
        default=5,
        description="Database connection pool size",
    )
    max_overflow: int = Field(
        default=10,
        description="Maximum overflow connections beyond pool_size",
    )
    echo: bool = Field(
        default=False,
        description="Log all SQL statements (development only)",
    )
    pool_pre_ping: bool = Field(
        default=True,
        description="Verify connections before using them from pool",
    )
    pool_recycle: int = Field(
        default=3600,
        description="Recycle connections after this many seconds",
    )
    migrate_on_start: bool = Field(
        default=False,
        description="Run Alembic migrations on application startup",
    )

    @property
    def is_sqlite(self) -> bool:
        return self.url.startswith("sqlite")

    @property
    def is_postgresql(self) -> bool:
        return self.url.startswith("postgresql")
