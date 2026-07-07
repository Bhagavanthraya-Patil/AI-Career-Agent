from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from . import BaseConfig


class LoggingSettings(BaseConfig):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Root logger level",
    )
    format: Literal["json", "text"] = Field(
        default="json",
        description="Log output format",
    )
    output: Literal["console", "file", "both"] = Field(
        default="both",
        description="Log output destination",
    )
    file_path: str = Field(
        default="storage/logs/runtime.log",
        description="Path to log file when output is file or both",
    )
    json_ensure_ascii: bool = Field(
        default=False,
        description="Ensure ASCII in JSON log output",
    )
    include_traceback: bool = Field(
        default=True,
        description="Include traceback in ERROR/CRITICAL logs",
    )
    agent_activity_path: str = Field(
        default="storage/logs/agent_activity.json",
        description="Path for structured agent activity trace log",
    )
