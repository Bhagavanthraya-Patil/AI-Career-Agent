from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ParsedEmploymentType(BaseModel):
    normalized: str = Field(
        default="full-time",
        description="Normalized employment type: full-time, part-time, contract, temporary, internship, freelance, volunteer",
    )
    original: str = Field(
        default="",
        description="Original raw input string",
    )
    is_remote_friendly: bool = Field(
        default=False,
        description="Whether this type commonly supports remote work",
    )


class ParsedExperience(BaseModel):
    level: Optional[str] = Field(
        default=None,
        description="Normalized experience level: entry, mid, senior, lead, principal",
    )
    years_min: Optional[int] = Field(
        default=None,
        description="Minimum years of experience required",
    )
    years_max: Optional[int] = Field(
        default=None,
        description="Maximum years of experience required",
    )
    original: str = Field(
        default="",
        description="Original raw input string",
    )


class ParsedCompany(BaseModel):
    name: str = Field(
        default="",
        description="Company name",
    )
    department: Optional[str] = Field(
        default=None,
        description="Department or division",
    )
    team: Optional[str] = Field(
        default=None,
        description="Team name",
    )
    business_unit: Optional[str] = Field(
        default=None,
        description="Business unit",
    )
    original: str = Field(
        default="",
        description="Original raw input string",
    )


class ParsedTitle(BaseModel):
    normalized: str = Field(
        default="",
        description="Normalized job title with seniority stripped",
    )
    seniority: Optional[str] = Field(
        default=None,
        description="Detected seniority level: senior, lead, principal, junior, etc.",
    )
    original: str = Field(
        default="",
        description="Original raw title string",
    )


class ParsedMetadata(BaseModel):
    job_id: Optional[str] = Field(
        default=None,
        description="Source-specific job identifier",
    )
    reference_id: Optional[str] = Field(
        default=None,
        description="External reference or requisition ID",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="Job category classifications",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Extracted tags or keywords",
    )
    posted_at: Optional[datetime] = Field(
        default=None,
        description="Job posting date",
    )
    closing_at: Optional[datetime] = Field(
        default=None,
        description="Application closing date",
    )
    language: Optional[str] = Field(
        default=None,
        description="Primary language of the job listing",
    )
    custom: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata fields not covered above",
    )
    original: dict[str, Any] = Field(
        default_factory=dict,
        description="Original raw metadata dictionary",
    )
