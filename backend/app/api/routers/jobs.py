from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.collectors.models import CollectorQuery
from app.db.repositories.job_query_repository import JobQueryRepository
from app.schemas.job import (
    ErrorResponse,
    JobDetailResponse,
    JobResponse,
    PaginatedResponse,
    RefreshResponse,
)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _paginate(
    jobs: list,
    total: int,
    page: int,
    page_size: int,
) -> PaginatedResponse:
    return PaginatedResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=JobQueryRepository.calculate_total_pages(total, page_size),
    )


@router.get(
    "",
    summary="List jobs",
    description="Paginated list of jobs with sorting and filtering",
    response_model=PaginatedResponse,
)
async def list_jobs(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query(
        default="scraped_at",
        description="Sort field: title, company, posted_at, scraped_at, created_at, "
        "updated_at, salary_min",
    ),
    sort_order: str = Query(
        default="desc",
        description="Sort direction: asc or desc",
        pattern="^(asc|desc)$",
    ),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    remote_type: Optional[str] = Query(
        default=None,
        description="Filter by remote type: remote, hybrid, onsite",
    ),
    employment_type: Optional[str] = Query(
        default=None,
        description="Filter by employment type: full-time, part-time, contract",
    ),
    experience_level: Optional[str] = Query(
        default=None,
        description="Filter by experience level: entry, mid, senior, lead",
    ),
    salary_min: Optional[int] = Query(
        default=None,
        ge=0,
        description="Minimum salary filter",
    ),
    salary_max: Optional[int] = Query(
        default=None,
        ge=0,
        description="Maximum salary filter",
    ),
    is_active: Optional[bool] = Query(
        default=None,
        description="Filter by active status",
    ),
    q: Optional[str] = Query(
        default=None,
        min_length=1,
        description="Search query for job title",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse:
    repo = JobQueryRepository(db)
    jobs, total = await repo.list_jobs(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        status=status,
        remote_type=remote_type,
        employment_type=employment_type,
        experience_level=experience_level,
        salary_min=salary_min,
        salary_max=salary_max,
        is_active=is_active,
        q=q,
    )
    return _paginate(jobs, total, page, page_size)


@router.get(
    "/search",
    summary="Search jobs",
    description="Full-text search across job titles, locations, and fields",
    response_model=PaginatedResponse,
)
async def search_jobs(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse:
    repo = JobQueryRepository(db)
    jobs, total = await repo.search_jobs(query=q, page=page, page_size=page_size)
    return _paginate(jobs, total, page, page_size)


@router.get(
    "/recent",
    summary="Recent jobs",
    description="Get the most recently scraped job listings",
    response_model=list[JobResponse],
)
async def recent_jobs(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of recent jobs to return",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[JobResponse]:
    repo = JobQueryRepository(db)
    jobs = await repo.list_recent(limit=limit)
    return [JobResponse.model_validate(j) for j in jobs]


@router.get(
    "/company/{company}",
    summary="Jobs by company",
    description="Get all jobs for a specific company",
    response_model=PaginatedResponse,
)
async def jobs_by_company(
    company: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse:
    repo = JobQueryRepository(db)
    jobs, total = await repo.list_by_company(
        company_name=company,
        page=page,
        page_size=page_size,
    )
    return _paginate(jobs, total, page, page_size)


@router.get(
    "/location/{location}",
    summary="Jobs by location",
    description="Get all jobs matching a location string",
    response_model=PaginatedResponse,
)
async def jobs_by_location(
    location: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse:
    repo = JobQueryRepository(db)
    jobs, total = await repo.list_by_location(
        location=location,
        page=page,
        page_size=page_size,
    )
    return _paginate(jobs, total, page, page_size)


@router.get(
    "/source/{source}",
    summary="Jobs by source",
    description="Get all jobs from a specific source platform",
    response_model=PaginatedResponse,
)
async def jobs_by_source(
    source: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse:
    repo = JobQueryRepository(db)
    jobs, total = await repo.list_by_source(
        source_name=source,
        page=page,
        page_size=page_size,
    )
    return _paginate(jobs, total, page, page_size)


@router.get(
    "/{job_id}",
    summary="Get job by ID",
    description="Get full job details including descriptions",
    response_model=JobDetailResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> JobDetailResponse:
    repo = JobQueryRepository(db)
    job = await repo.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return JobDetailResponse.model_validate(job)


async def _run_collectors(query: CollectorQuery) -> None:
    try:
        from app.collectors.config import CollectorConfigProvider
        from app.collectors.registry import CollectorRegistry

        CollectorRegistry.discover("app.collectors.plugins")
        for name in CollectorRegistry.list_collectors():
            collector_cls = CollectorRegistry.get(name)
            if collector_cls is None:
                continue
            config = CollectorConfigProvider.get_source_config(name)
            collector = collector_cls(config)
            await collector.execute(query)
    except Exception:
        pass


@router.post(
    "/refresh",
    summary="Refresh jobs",
    description="Trigger all registered collectors to fetch new job listings",
    status_code=202,
    response_model=RefreshResponse,
)
async def refresh_jobs(
    background_tasks: BackgroundTasks,
    keywords: list[str] = Query(default=[], description="Search keywords"),
    locations: list[str] = Query(default=[], description="Location filters"),
    remote_only: bool = Query(default=False, description="Remote only"),
    salary_min: Optional[int] = Query(default=None, ge=0, description="Min salary"),
    salary_max: Optional[int] = Query(default=None, ge=0, description="Max salary"),
    experience_level: Optional[str] = Query(default=None, description="Experience level"),
    employment_type: Optional[str] = Query(default=None, description="Employment type"),
    max_results: int = Query(default=50, ge=1, le=500, description="Max results"),
) -> RefreshResponse:
    collector_query = CollectorQuery(
        keywords=keywords,
        locations=locations,
        remote_only=remote_only,
        salary_min=salary_min,
        salary_max=salary_max,
        experience_level=experience_level,
        employment_type=employment_type,
        max_results=max_results,
    )
    background_tasks.add_task(_run_collectors, collector_query)
    return RefreshResponse(
        message="Job collection started in background",
        query=collector_query.model_dump(),
    )
