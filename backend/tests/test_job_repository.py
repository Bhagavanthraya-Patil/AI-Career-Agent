from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.models import (
    CompanyData,
    JobData,
    JobMetadata,
    LocationData,
    SalaryData,
)
from app.db.models import (
    Company,
    Job,
    JobDescription,
    JobSource,
)
from app.db.repositories import (
    JobNotFoundError,
    JobRepository,
)


def _make_job_data(
    source_job_id: str = "101",
    title: str = "Software Engineer",
    company_name: str = "Acme Corp",
    source: str = "greenhouse",
    remote_type: str = "onsite",
    include_salary: bool = False,
    include_location: bool = True,
) -> JobData:
    metadata = JobMetadata(
        source=source,
        source_job_id=source_job_id,
        job_url=f"https://boards.greenhouse.io/acme/jobs/{source_job_id}",
        apply_url=f"https://boards.greenhouse.io/acme/jobs/{source_job_id}",
        posted_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )

    company = CompanyData(name=company_name)

    location = LocationData()
    if include_location:
        location = LocationData(
            city="San Francisco",
            state="CA",
            country="USA",
            remote_type=remote_type,
            full_address="San Francisco, CA, USA",
        )
    else:
        location = LocationData(remote_type=remote_type)

    salary = None
    if include_salary:
        salary = SalaryData(min=100000, max=150000, currency="USD")

    return JobData(
        title=title,
        company=company,
        location=location,
        salary=salary,
        metadata=metadata,
        description_raw="Job description text here",
        description_html="<div>Job description text here</div>",
        employment_type="full-time",
        experience_level="senior",
        skills=["Python", "FastAPI"],
        raw_data={"id": int(source_job_id), "title": title},
    )


class TestJobRepository:
    async def test_save_job_creates_job(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        job_data = _make_job_data(source_job_id="101")

        job = await repo.save_job(job_data)

        assert job.id is not None
        assert isinstance(job.id, UUID)
        assert job.title == "Software Engineer"
        assert job.source_job_id == "101"
        assert job.status == "discovered"
        assert job.job_url == job_data.metadata.job_url

    async def test_save_job_creates_company(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        job_data = _make_job_data(company_name="NewCo Inc")

        job = await repo.save_job(job_data)

        result = await db_session.execute(
            select(Company).where(Company.name == "NewCo Inc")
        )
        company = result.scalar_one()
        assert company is not None
        assert company.name == "NewCo Inc"
        assert job.company_id == company.id

    async def test_save_job_creates_job_source(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        job_data = _make_job_data(source="lever")

        job = await repo.save_job(job_data)

        result = await db_session.execute(
            select(JobSource).where(JobSource.name == "lever")
        )
        source = result.scalar_one()
        assert source is not None
        assert source.name == "lever"
        assert source.is_active is True
        assert job.source_id == source.id

    async def test_save_job_creates_job_description(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        job_data = _make_job_data(source_job_id="102")

        job = await repo.save_job(job_data)

        result = await db_session.execute(
            select(JobDescription).where(JobDescription.job_id == job.id)
        )
        desc = result.scalar_one()
        assert desc is not None
        assert desc.raw_text == "Job description text here"
        assert desc.raw_html == "<div>Job description text here</div>"
        assert desc.is_current is True
        assert desc.version == 1

    async def test_save_job_reuses_existing_company(
        self,
        db_session: AsyncSession,
    ) -> None:
        existing = Company(name="Acme Corp")
        db_session.add(existing)
        await db_session.flush()
        existing_id = existing.id

        repo = JobRepository(db_session)
        job_data = _make_job_data(company_name="Acme Corp")

        job = await repo.save_job(job_data)

        assert job.company_id == existing_id

        result = await db_session.execute(
            select(Company).where(Company.name == "Acme Corp")
        )
        companies = result.scalars().all()
        assert len(companies) == 1

    async def test_save_job_reuses_existing_job_source(
        self,
        db_session: AsyncSession,
    ) -> None:
        existing = JobSource(name="greenhouse", is_active=True)
        db_session.add(existing)
        await db_session.flush()
        existing_id = existing.id

        repo = JobRepository(db_session)
        job_data = _make_job_data(source="greenhouse")

        job = await repo.save_job(job_data)

        assert job.source_id == existing_id

        result = await db_session.execute(
            select(JobSource).where(JobSource.name == "greenhouse")
        )
        sources = result.scalars().all()
        assert len(sources) == 1

    async def test_save_job_updates_existing_on_duplicate(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)

        original = _make_job_data(
            source_job_id="200",
            title="Original Title",
        )
        job1 = await repo.save_job(original)
        original_id = job1.id

        updated = _make_job_data(
            source_job_id="200",
            title="Updated Title",
        )
        job2 = await repo.save_job(updated)

        assert job2.id == original_id
        assert job2.title == "Updated Title"

        result = await db_session.execute(select(Job))
        all_jobs = result.scalars().all()
        assert len(all_jobs) == 1

    async def test_update_job_modifies_fields(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        job_data = _make_job_data(source_job_id="300")
        job = await repo.save_job(job_data)

        updated = await repo.update_job(
            job.id,
            {"title": "Senior Engineer", "status": "analyzed"},
        )

        assert updated.title == "Senior Engineer"
        assert updated.status == "analyzed"
        assert updated.updated_at is not None

    async def test_update_job_raises_on_not_found(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        fake_id = uuid4()

        with pytest.raises(JobNotFoundError) as exc_info:
            await repo.update_job(fake_id, {"title": "Ghost"})
        assert str(fake_id) in str(exc_info.value)

    async def test_find_existing_job_returns_job(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        await repo.save_job(
            _make_job_data(source_job_id="400", source="greenhouse")
        )

        found = await repo.find_existing_job("greenhouse", "400")
        assert found is not None
        assert found.source_job_id == "400"
        assert found.source.name == "greenhouse"

    async def test_find_existing_job_returns_none(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        found = await repo.find_existing_job("greenhouse", "nonexistent")
        assert found is None

    async def test_find_existing_job_respects_source(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        await repo.save_job(
            _make_job_data(source_job_id="500", source="greenhouse")
        )

        found_greenhouse = await repo.find_existing_job("greenhouse", "500")
        assert found_greenhouse is not None

        found_linkedin = await repo.find_existing_job("linkedin", "500")
        assert found_linkedin is None

    async def test_bulk_save_jobs_creates_multiple(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        jobs = [
            _make_job_data(source_job_id="601", title="Job A"),
            _make_job_data(source_job_id="602", title="Job B"),
            _make_job_data(source_job_id="603", title="Job C"),
        ]

        saved = await repo.bulk_save_jobs(jobs)

        assert len(saved) == 3
        assert saved[0].title == "Job A"
        assert saved[1].title == "Job B"
        assert saved[2].title == "Job C"

    async def test_bulk_save_jobs_deduplicates(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        jobs = [
            _make_job_data(source_job_id="701", title="Original"),
            _make_job_data(source_job_id="701", title="Duplicate"),
            _make_job_data(source_job_id="702", title="Unique"),
        ]

        saved = await repo.bulk_save_jobs(jobs)

        assert len(saved) == 3
        assert saved[0].title == "Duplicate"
        assert saved[1].title == "Duplicate"
        assert saved[2].title == "Unique"

        result = await db_session.execute(select(Job))
        all_jobs = result.scalars().all()
        assert len(all_jobs) == 2

    async def test_save_job_with_salary(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        job_data = _make_job_data(
            source_job_id="800",
            include_salary=True,
        )

        job = await repo.save_job(job_data)

        assert job.salary_min == 100000
        assert job.salary_max == 150000
        assert job.salary_currency == "USD"

    async def test_save_job_without_location(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        job_data = _make_job_data(
            source_job_id="900",
            include_location=False,
            remote_type="remote",
        )

        job = await repo.save_job(job_data)

        assert job.remote_type == "remote"
        assert job.location == "Remote"

    async def test_save_job_sets_timestamps(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        job_data = _make_job_data(source_job_id="1001")

        job = await repo.save_job(job_data)

        assert job.created_at is not None
        assert job.updated_at is not None
        assert job.scraped_at is not None
        assert job.posted_at == datetime(
            2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc
        )

    async def test_company_get_or_create_does_not_duplicate(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)

        c1_data = CompanyData(name="UniqueCorp")
        c1 = await repo._get_or_create_company(c1_data)
        c2 = await repo._get_or_create_company(c1_data)

        assert c1.id == c2.id

        result = await db_session.execute(
            select(Company).where(Company.name == "UniqueCorp")
        )
        companies = result.scalars().all()
        assert len(companies) == 1

    async def test_job_source_get_or_create_does_not_duplicate(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)

        s1 = await repo._get_or_create_job_source("myboard")
        s2 = await repo._get_or_create_job_source("myboard")

        assert s1.id == s2.id

        result = await db_session.execute(
            select(JobSource).where(JobSource.name == "myboard")
        )
        sources = result.scalars().all()
        assert len(sources) == 1

    async def test_job_source_name_normalized_to_lowercase(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)

        source = await repo._get_or_create_job_source("GreenHouse")

        assert source.name == "greenhouse"

    async def test_upsert_job_description_creates_new(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        job = await repo.save_job(
            _make_job_data(source_job_id="1101")
        )

        desc = await repo._upsert_job_description(
            job.id, _make_job_data(source_job_id="1101")
        )

        assert desc is not None
        assert desc.job_id == job.id
        assert desc.raw_text == "Job description text here"

    async def test_upsert_job_description_updates_existing(
        self,
        db_session: AsyncSession,
    ) -> None:
        repo = JobRepository(db_session)
        job = await repo.save_job(
            _make_job_data(source_job_id="1201")
        )

        modified_data = _make_job_data(
            source_job_id="1201",
            title="Modified",
        )
        modified_data.description_raw = "Updated description"

        desc = await repo._upsert_job_description(job.id, modified_data)

        assert desc.raw_text == "Updated description"

        result = await db_session.execute(
            select(JobDescription).where(
                JobDescription.job_id == job.id
            )
        )
        all_descs = result.scalars().all()
        assert len(all_descs) == 1

    async def test_build_location_string_uses_full_address(
        self,
        db_session: AsyncSession,
    ) -> None:
        from app.collectors.models import LocationData

        location = LocationData(
            city="New York",
            state="NY",
            country="USA",
            full_address="New York, NY, USA",
        )
        job = _make_job_data(source_job_id="1301")
        job.location = location

        result = JobRepository._build_location_string(job)
        assert result == "New York, NY, USA"

    async def test_build_location_string_without_full_address(
        self,
        db_session: AsyncSession,
    ) -> None:
        from app.collectors.models import LocationData

        location = LocationData(
            city="Chicago",
            state="IL",
            country="USA",
            full_address=None,
        )
        job = _make_job_data(source_job_id="1302")
        job.location = location

        result = JobRepository._build_location_string(job)
        assert result == "Chicago, IL, USA"

    async def test_build_location_string_remote_no_location(
        self,
        db_session: AsyncSession,
    ) -> None:
        from app.collectors.models import LocationData

        location = LocationData(
            city=None,
            state=None,
            country=None,
            remote_type="remote",
            full_address=None,
        )
        job = _make_job_data(source_job_id="1303")
        job.location = location

        result = JobRepository._build_location_string(job)
        assert result == "Remote"
