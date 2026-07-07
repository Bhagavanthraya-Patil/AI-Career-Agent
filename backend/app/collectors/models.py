from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class CollectorQuery(BaseModel):
    """Parameters for a job collection request."""

    keywords: list[str] = Field(
        default_factory=list,
        description="Search keywords (e.g., ['Python', 'FastAPI'])",
    )
    locations: list[str] = Field(
        default_factory=list,
        description="Location filters (e.g., ['Remote', 'New York'])",
    )
    remote_only: bool = Field(
        default=False,
        description="Only return remote positions",
    )
    salary_min: Optional[int] = Field(
        default=None,
        description="Minimum salary filter",
    )
    salary_max: Optional[int] = Field(
        default=None,
        description="Maximum salary filter",
    )
    experience_level: Optional[str] = Field(
        default=None,
        description="Experience level filter (entry, mid, senior, lead)",
    )
    employment_type: Optional[str] = Field(
        default=None,
        description="Employment type filter (full-time, part-time, contract)",
    )
    max_results: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of jobs to collect",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number for paginated collection",
    )
    additional_filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Source-specific filter parameters",
    )


class SalaryData(BaseModel):
    """Salary information for a job listing."""

    min: Optional[int] = Field(default=None, description="Minimum salary")
    max: Optional[int] = Field(default=None, description="Maximum salary")
    currency: str = Field(default="USD", description="Currency code (ISO 4217)")
    interval: str = Field(
        default="yearly",
        description="Payment interval (yearly, monthly, hourly)",
    )


class LocationData(BaseModel):
    """Location information for a job listing."""

    city: Optional[str] = Field(default=None, description="City name")
    state: Optional[str] = Field(default=None, description="State or province")
    country: Optional[str] = Field(default=None, description="Country name")
    postal_code: Optional[str] = Field(default=None, description="Postal/ZIP code")
    remote_type: str = Field(
        default="onsite",
        description="Remote work type (remote, hybrid, onsite)",
    )
    full_address: Optional[str] = Field(
        default=None,
        description="Full location string as displayed on the listing",
    )


class CompanyData(BaseModel):
    """Company information extracted from a job listing."""

    name: str = Field(..., description="Company name")
    website: Optional[str] = Field(default=None, description="Company website URL")
    industry: Optional[str] = Field(default=None, description="Primary industry")
    size: Optional[str] = Field(
        default=None,
        description="Company size range (e.g., '51-200')",
    )
    location: Optional[str] = Field(default=None, description="HQ location")
    description: Optional[str] = Field(default=None, description="Company description")
    logo_url: Optional[str] = Field(default=None, description="Company logo URL")
    linkedin_url: Optional[str] = Field(
        default=None,
        description="Company LinkedIn URL",
    )


class JobMetadata(BaseModel):
    """Metadata about a collected job listing."""

    source: str = Field(..., description="Source platform name")
    source_job_id: str = Field(
        ...,
        description="Unique identifier from the source platform",
    )
    job_url: str = Field(..., description="Direct URL to the job listing")
    apply_url: Optional[str] = Field(
        default=None,
        description="Direct application URL (may differ from listing URL)",
    )
    posted_at: Optional[datetime] = Field(
        default=None,
        description="When the job was posted on the source",
    )
    scraped_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the job was collected",
    )
    is_actively_hiring: bool = Field(
        default=True,
        description="Whether the listing is still accepting applications",
    )


class JobData(BaseModel):
    """Normalized representation of a single job listing."""

    title: str = Field(..., description="Job title")
    company: CompanyData = Field(..., description="Employer information")
    location: LocationData = Field(
        default_factory=LocationData,
        description="Job location",
    )
    salary: Optional[SalaryData] = Field(
        default=None,
        description="Salary information",
    )
    metadata: JobMetadata = Field(..., description="Job listing metadata")
    description_raw: Optional[str] = Field(
        default=None,
        description="Raw job description text",
    )
    description_html: Optional[str] = Field(
        default=None,
        description="Raw job description HTML",
    )
    employment_type: Optional[str] = Field(
        default=None,
        description="Employment type (full-time, part-time, contract)",
    )
    experience_level: Optional[str] = Field(
        default=None,
        description="Required experience level",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Extracted or tagged skills",
    )
    raw_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Original source data for debugging",
    )


class CollectionStats(BaseModel):
    """Statistics for a single collection run."""

    total_discovered: int = Field(
        default=0,
        description="Total jobs discovered from the source",
    )
    total_normalized: int = Field(
        default=0,
        description="Jobs successfully normalized",
    )
    total_valid: int = Field(
        default=0,
        description="Jobs that passed validation",
    )
    total_duplicates_removed: int = Field(
        default=0,
        description="Jobs removed as duplicates",
    )
    total_saved: int = Field(
        default=0,
        description="Jobs persisted to storage",
    )
    total_failed: int = Field(
        default=0,
        description="Jobs that failed processing",
    )
    pages_collected: int = Field(
        default=0,
        description="Number of pages scraped",
    )
    duration_seconds: float = Field(
        default=0.0,
        description="Total collection duration in seconds",
    )


class ErrorReport(BaseModel):
    """Detailed error information for a failed collection item."""

    item_index: int = Field(
        default=0,
        description="Index of the item that failed (if applicable)",
    )
    error_type: str = Field(
        default="",
        description="Exception class name",
    )
    error_message: str = Field(
        default="",
        description="Human-readable error description",
    )
    source_field: Optional[str] = Field(
        default=None,
        description="Field that caused the error (if applicable)",
    )
    raw_value: Optional[object] = Field(
        default=None,
        description="Original value that caused the error",
    )
    recoverable: bool = Field(
        default=True,
        description="Whether the error can be retried",
    )


class CollectorResult(BaseModel):
    """Result of a complete collection run."""

    source: str = Field(..., description="Source platform name")
    query: CollectorQuery = Field(..., description="The query that was executed")
    jobs: list[JobData] = Field(
        default_factory=list,
        description="Collected job data",
    )
    stats: CollectionStats = Field(
        default_factory=CollectionStats,
        description="Collection statistics",
    )
    errors: list[ErrorReport] = Field(
        default_factory=list,
        description="Errors encountered during collection",
    )
    raw_data: Any = Field(
        default=None,
        description="Raw source data (used internally by pipeline)",
    )
    existing_source_ids: list[str] = Field(
        default_factory=list,
        description="Source IDs already in the database for dedup",
    )
    success: bool = Field(
        default=True,
        description="Whether the collection completed successfully",
    )
