from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    linkedin_url: Optional[str] = None

    model_config = {"from_attributes": True}


class JobSourceResponse(BaseModel):
    id: UUID
    name: str
    base_url: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class JobDescriptionResponse(BaseModel):
    id: UUID
    version: int
    raw_html: Optional[str] = None
    raw_text: Optional[str] = None
    parsed_json: Optional[dict] = None
    is_current: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    id: UUID
    title: str
    location: Optional[str] = None
    remote_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    job_url: Optional[str] = None
    apply_url: Optional[str] = None
    status: str = "discovered"
    is_active: bool = True
    posted_at: Optional[datetime] = None
    scraped_at: datetime
    created_at: datetime
    updated_at: datetime
    company: CompanyResponse
    source: JobSourceResponse

    model_config = {"from_attributes": True}


class JobDetailResponse(JobResponse):
    descriptions: list[JobDescriptionResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RefreshResponse(BaseModel):
    message: str
    query: dict


class ErrorResponse(BaseModel):
    detail: str
