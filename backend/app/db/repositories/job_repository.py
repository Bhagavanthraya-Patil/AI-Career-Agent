from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.collectors.models import CompanyData, JobData
from app.db.models import Company, Job, JobDescription, JobSource


class CompanyNotFoundError(Exception):
    def __init__(self, company_id: UUID) -> None:
        self.company_id = company_id
        super().__init__(f"Company not found: {company_id}")


class JobSourceNotFoundError(Exception):
    def __init__(self, source_name: str) -> None:
        self.source_name = source_name
        super().__init__(f"Job source not found: {source_name}")


class JobNotFoundError(Exception):
    def __init__(self, job_id: UUID) -> None:
        self.job_id = job_id
        super().__init__(f"Job not found: {job_id}")


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_job(self, job_data: JobData) -> Job:
        existing = await self.find_existing_job(
            job_data.metadata.source,
            job_data.metadata.source_job_id,
        )
        if existing is not None:
            return await self._update_from_job_data(existing, job_data)

        return await self._create_from_job_data(job_data)

    async def update_job(
        self,
        job_id: UUID,
        updates: dict[str, Any],
    ) -> Job:
        job = await self._session.get(Job, job_id)
        if job is None:
            raise JobNotFoundError(job_id)

        safe_updates = {k: v for k, v in updates.items() if hasattr(Job, k)}
        if not safe_updates:
            return job

        safe_updates["updated_at"] = datetime.now(timezone.utc)

        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(**safe_updates)
            .returning(Job)
        )
        result = await self._session.execute(stmt)
        updated = result.scalar_one()
        return updated

    async def find_existing_job(
        self,
        source_name: str,
        source_job_id: str,
    ) -> Optional[Job]:
        stmt = (
            select(Job)
            .join(Job.source)
            .options(selectinload(Job.source))
            .where(
                JobSource.name == source_name,
                Job.source_job_id == source_job_id,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def bulk_save_jobs(
        self,
        jobs_data: list[JobData],
    ) -> list[Job]:
        saved: list[Job] = []
        for job_data in jobs_data:
            job = await self.save_job(job_data)
            saved.append(job)
        return saved

    async def _create_from_job_data(self, job_data: JobData) -> Job:
        company = await self._get_or_create_company(job_data.company)
        source = await self._get_or_create_job_source(
            job_data.metadata.source,
        )

        job = Job(
            company_id=company.id,
            source_id=source.id,
            source_job_id=job_data.metadata.source_job_id,
            title=job_data.title,
            location=self._build_location_string(job_data),
            remote_type=job_data.location.remote_type,
            salary_min=job_data.salary.min if job_data.salary else None,
            salary_max=job_data.salary.max if job_data.salary else None,
            salary_currency=(
                job_data.salary.currency if job_data.salary else "USD"
            ),
            employment_type=job_data.employment_type,
            experience_level=job_data.experience_level,
            job_url=job_data.metadata.job_url,
            apply_url=job_data.metadata.apply_url,
            posted_at=job_data.metadata.posted_at,
            scraped_at=job_data.metadata.scraped_at,
        )
        self._session.add(job)
        await self._session.flush()

        job_desc = JobDescription(
            job_id=job.id,
            raw_html=job_data.description_html,
            raw_text=job_data.description_raw,
        )
        self._session.add(job_desc)
        await self._session.flush()

        return job

    async def _update_from_job_data(
        self,
        job: Job,
        job_data: JobData,
    ) -> Job:
        company = await self._get_or_create_company(job_data.company)
        source = await self._get_or_create_job_source(
            job_data.metadata.source,
        )

        job.company_id = company.id
        job.source_id = source.id
        job.title = job_data.title
        job.location = self._build_location_string(job_data)
        job.remote_type = job_data.location.remote_type
        job.salary_min = job_data.salary.min if job_data.salary else None
        job.salary_max = job_data.salary.max if job_data.salary else None
        job.salary_currency = (
            job_data.salary.currency if job_data.salary else "USD"
        )
        job.employment_type = job_data.employment_type
        job.experience_level = job_data.experience_level
        job.job_url = job_data.metadata.job_url
        job.apply_url = job_data.metadata.apply_url
        job.posted_at = job_data.metadata.posted_at
        job.scraped_at = job_data.metadata.scraped_at
        job.updated_at = datetime.now(timezone.utc)

        await self._session.flush()

        await self._upsert_job_description(job.id, job_data)

        return job

    async def _get_or_create_company(
        self,
        company_data: CompanyData,
    ) -> Company:
        name = company_data.name.strip()
        result = await self._session.execute(
            select(Company).where(Company.name == name),
        )
        company = result.scalar_one_or_none()
        if company is not None:
            return company

        company = Company(
            name=name,
            website=company_data.website,
            industry=company_data.industry,
            size=company_data.size,
            location=company_data.location,
            description=company_data.description,
            logo_url=company_data.logo_url,
            linkedin_url=company_data.linkedin_url,
        )
        self._session.add(company)
        await self._session.flush()
        return company

    async def _get_or_create_job_source(
        self,
        source_name: str,
    ) -> JobSource:
        name = source_name.strip().lower()
        result = await self._session.execute(
            select(JobSource).where(JobSource.name == name),
        )
        source = result.scalar_one_or_none()
        if source is not None:
            return source

        source = JobSource(name=name, is_active=True)
        self._session.add(source)
        await self._session.flush()
        return source

    async def _upsert_job_description(
        self,
        job_id: UUID,
        job_data: JobData,
    ) -> JobDescription:
        result = await self._session.execute(
            select(JobDescription).where(
                JobDescription.job_id == job_id,
                JobDescription.is_current == True,  # noqa: E712
            )
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.raw_html = job_data.description_html
            existing.raw_text = job_data.description_raw
            existing.parsed_json = job_data.raw_data if job_data.raw_data else None
            await self._session.flush()
            return existing

        job_desc = JobDescription(
            job_id=job_id,
            raw_html=job_data.description_html,
            raw_text=job_data.description_raw,
            parsed_json=job_data.raw_data if job_data.raw_data else None,
            is_current=True,
        )
        self._session.add(job_desc)
        await self._session.flush()
        return job_desc

    @staticmethod
    def _build_location_string(job_data: JobData) -> str:
        parts: list[str] = []
        loc = job_data.location
        if loc.full_address:
            return loc.full_address
        if loc.city:
            parts.append(loc.city)
        if loc.state:
            parts.append(loc.state)
        if loc.country:
            if loc.state:
                parts.append(loc.country)
            else:
                parts.append(loc.country)
        if not parts:
            if loc.remote_type == "remote":
                return "Remote"
            return ""
        return ", ".join(parts)
