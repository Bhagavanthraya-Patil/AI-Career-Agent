from __future__ import annotations

from math import ceil
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Company, Job, JobDescription, JobSource


class JobQueryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    SORT_MAP: dict[str, Any] = {
        "title": Job.title,
        "posted_at": Job.posted_at,
        "scraped_at": Job.scraped_at,
        "created_at": Job.created_at,
        "updated_at": Job.updated_at,
        "salary_min": Job.salary_min,
    }

    async def list_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "scraped_at",
        sort_order: str = "desc",
        status: Optional[str] = None,
        remote_type: Optional[str] = None,
        employment_type: Optional[str] = None,
        experience_level: Optional[str] = None,
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
        is_active: Optional[bool] = None,
        q: Optional[str] = None,
    ) -> tuple[list[Job], int]:
        base_q = select(Job).options(
            selectinload(Job.company),
            selectinload(Job.source),
        )

        count_q = select(func.count(Job.id))

        if q:
            pattern = f"%{q}%"
            base_q = base_q.where(Job.title.ilike(pattern))
            count_q = count_q.where(Job.title.ilike(pattern))

        if status is not None:
            base_q = base_q.where(Job.status == status)
            count_q = count_q.where(Job.status == status)

        if remote_type is not None:
            base_q = base_q.where(Job.remote_type == remote_type)
            count_q = count_q.where(Job.remote_type == remote_type)

        if employment_type is not None:
            base_q = base_q.where(Job.employment_type == employment_type)
            count_q = count_q.where(Job.employment_type == employment_type)

        if experience_level is not None:
            base_q = base_q.where(Job.experience_level == experience_level)
            count_q = count_q.where(Job.experience_level == experience_level)

        if salary_min is not None:
            base_q = base_q.where(
                (Job.salary_min >= salary_min) | (Job.salary_max >= salary_min)
            )
            count_q = count_q.where(
                (Job.salary_min >= salary_min) | (Job.salary_max >= salary_min)
            )

        if salary_max is not None:
            base_q = base_q.where(
                (Job.salary_min <= salary_max) | (Job.salary_max <= salary_max)
            )
            count_q = count_q.where(
                (Job.salary_min <= salary_max) | (Job.salary_max <= salary_max)
            )

        if is_active is not None:
            base_q = base_q.where(Job.is_active == is_active)
            count_q = count_q.where(Job.is_active == is_active)

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        if sort_by == "company":
            base_q = base_q.join(Company)
            if sort_order == "asc":
                base_q = base_q.order_by(Company.name.asc())
            else:
                base_q = base_q.order_by(Company.name.desc())
        else:
            column = self.SORT_MAP.get(sort_by, Job.scraped_at)
            if sort_order == "asc":
                base_q = base_q.order_by(column.asc())
            else:
                base_q = base_q.order_by(column.desc())

        offset = (page - 1) * page_size
        base_q = base_q.offset(offset).limit(page_size)

        result = await self._session.execute(base_q)
        jobs = list(result.scalars().all())

        return jobs, total

    async def get_job_by_id(self, job_id: UUID) -> Optional[Job]:
        stmt = (
            select(Job)
            .options(
                selectinload(Job.company),
                selectinload(Job.source),
                selectinload(Job.descriptions),
            )
            .where(Job.id == job_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_jobs(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        pattern = f"%{query}%"
        base_q = (
            select(Job)
            .options(
                selectinload(Job.company),
                selectinload(Job.source),
            )
            .where(
                Job.title.ilike(pattern)
                | Job.location.ilike(pattern)
                | Job.employment_type.ilike(pattern)
                | Job.experience_level.ilike(pattern)
            )
        )
        count_q = select(func.count(Job.id)).where(
            Job.title.ilike(pattern)
            | Job.location.ilike(pattern)
            | Job.employment_type.ilike(pattern)
            | Job.experience_level.ilike(pattern)
        )

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        base_q = base_q.order_by(Job.scraped_at.desc()).offset(offset).limit(page_size)

        result = await self._session.execute(base_q)
        jobs = list(result.scalars().all())

        return jobs, total

    async def list_by_company(
        self,
        company_name: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        base_q = (
            select(Job)
            .options(
                selectinload(Job.company),
                selectinload(Job.source),
            )
            .join(Company)
            .where(Company.name.ilike(f"%{company_name}%"))
        )
        count_q = (
            select(func.count(Job.id))
            .join(Company)
            .where(Company.name.ilike(f"%{company_name}%"))
        )

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        base_q = base_q.order_by(Job.scraped_at.desc()).offset(offset).limit(page_size)

        result = await self._session.execute(base_q)
        jobs = list(result.scalars().all())

        return jobs, total

    async def list_by_location(
        self,
        location: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        pattern = f"%{location}%"
        base_q = (
            select(Job)
            .options(
                selectinload(Job.company),
                selectinload(Job.source),
            )
            .where(Job.location.ilike(pattern))
        )
        count_q = select(func.count(Job.id)).where(Job.location.ilike(pattern))

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        base_q = base_q.order_by(Job.scraped_at.desc()).offset(offset).limit(page_size)

        result = await self._session.execute(base_q)
        jobs = list(result.scalars().all())

        return jobs, total

    async def list_by_source(
        self,
        source_name: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        base_q = (
            select(Job)
            .options(
                selectinload(Job.company),
                selectinload(Job.source),
            )
            .join(JobSource)
            .where(JobSource.name.ilike(f"%{source_name}%"))
        )
        count_q = (
            select(func.count(Job.id))
            .join(JobSource)
            .where(JobSource.name.ilike(f"%{source_name}%"))
        )

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        base_q = base_q.order_by(Job.scraped_at.desc()).offset(offset).limit(page_size)

        result = await self._session.execute(base_q)
        jobs = list(result.scalars().all())

        return jobs, total

    async def list_recent(self, limit: int = 20) -> list[Job]:
        stmt = (
            select(Job)
            .options(
                selectinload(Job.company),
                selectinload(Job.source),
            )
            .order_by(Job.scraped_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def calculate_total_pages(total: int, page_size: int) -> int:
        return max(1, ceil(total / page_size)) if total > 0 else 1
