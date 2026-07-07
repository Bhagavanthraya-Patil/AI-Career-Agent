from __future__ import annotations

from typing import Optional

from pydantic import Field

from . import BaseConfig


class StorageSettings(BaseConfig):
    base_path: str = Field(
        default="storage",
        description="Root directory for all local file storage",
    )
    resumes_path: str = Field(
        default="storage/resumes",
        description="Directory for generated resume files",
    )
    jobs_path: str = Field(
        default="storage/jobs",
        description="Directory for cached job data",
    )
    logs_path: str = Field(
        default="storage/logs",
        description="Directory for runtime log files",
    )
    templates_path: str = Field(
        default="templates",
        description="Directory for document templates",
    )
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum upload file size in MB",
    )
    allowed_resume_formats: list[str] = Field(
        default=[".pdf", ".docx", ".md", ".txt"],
        description="Allowed file extensions for resume uploads",
    )
