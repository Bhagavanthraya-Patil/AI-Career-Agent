from __future__ import annotations

from typing import Optional

from pydantic import Field

from . import BaseConfig


class AppSettings(BaseConfig):
    project_name: str = Field(
        default="AI Career Agent",
        description="Application display name",
    )
    version: str = Field(
        default="0.1.0",
        description="Application version (semver)",
    )
    environment: str = Field(
        default="development",
        description="Runtime environment: development, staging, production",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode (verbose error pages, hot reload)",
    )
    secret_key: str = Field(
        default="",
        description="Secret key for session signing, JWT, etc. Must be set in production",
    )
    frontend_url: str = Field(
        default="http://localhost:5173",
        description="Frontend URL for CORS and redirects",
    )
    api_host: str = Field(
        default="0.0.0.0",
        description="Backend API bind host",
    )
    api_port: int = Field(
        default=8000,
        description="Backend API bind port",
    )
    api_root_path: str = Field(
        default="/api",
        description="Root path prefix for all API routes",
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:5173"],
        description="Allowed CORS origins (comma-separated in env var)",
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"
