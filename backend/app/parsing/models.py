from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ParsedSalary(BaseModel):
    min: Optional[int] = Field(default=None, description="Minimum salary in normalized units")
    max: Optional[int] = Field(default=None, description="Maximum salary in normalized units")
    currency: str = Field(default="USD", description="ISO 4217 currency code")
    interval: str = Field(default="yearly", description="Payment interval (yearly, monthly, hourly, one_time)")
    original: str = Field(default="", description="Original raw salary string")


class ParsedLocation(BaseModel):
    city: Optional[str] = Field(default=None, description="City name")
    state: Optional[str] = Field(default=None, description="State or province")
    country: Optional[str] = Field(default=None, description="Country name")
    postal_code: Optional[str] = Field(default=None, description="Postal or ZIP code")
    remote_type: str = Field(default="onsite", description="remote, hybrid, or onsite")
    full_address: Optional[str] = Field(default=None, description="Original location string")


class ParsedCompany(BaseModel):
    name: str = Field(default="", description="Company or organization name")
    department: Optional[str] = Field(default=None, description="Department name")
    team: Optional[str] = Field(default=None, description="Team name")
    division: Optional[str] = Field(default=None, description="Division or business unit")


class ParsedMetadata(BaseModel):
    source_job_id: Optional[str] = Field(default=None, description="Platform-specific job ID")
    job_url: Optional[str] = Field(default=None, description="Direct URL to job listing")
    apply_url: Optional[str] = Field(default=None, description="Direct application URL")
    posted_at: Optional[datetime] = Field(default=None, description="Job posting date")
    closing_at: Optional[datetime] = Field(default=None, description="Application closing date")
    categories: list[str] = Field(default_factory=list, description="Job categories")
    tags: list[str] = Field(default_factory=list, description="Tags or keywords")
    benefits: list[str] = Field(default_factory=list, description="Benefits listed")
    languages: list[str] = Field(default_factory=list, description="Required languages")
    custom: dict[str, Any] = Field(default_factory=dict, description="Custom metadata fields")


class ParsedJob(BaseModel):
    title: str = Field(default="", description="Normalized job title")
    company: ParsedCompany = Field(default_factory=ParsedCompany, description="Parsed company info")
    location: ParsedLocation = Field(default_factory=ParsedLocation, description="Parsed location")
    salary: Optional[ParsedSalary] = Field(default=None, description="Parsed salary")
    employment_type: Optional[str] = Field(default=None, description="Normalized employment type")
    experience_level: Optional[str] = Field(default=None, description="Normalized experience level")
    description_raw: Optional[str] = Field(default=None, description="Cleaned description text")
    metadata: ParsedMetadata = Field(default_factory=ParsedMetadata, description="Parsed metadata")


class ParseResult(BaseModel):
    success: bool = Field(default=True, description="Whether parsing completed without errors")
    job: ParsedJob = Field(default_factory=ParsedJob, description="The parsed job data")
    errors: list[str] = Field(default_factory=list, description="Non-fatal parsing warnings or errors")
    warnings: list[str] = Field(default_factory=list, description="Parsing warnings")
