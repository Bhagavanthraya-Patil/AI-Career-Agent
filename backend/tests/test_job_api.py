from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_db_session
from app.api.routers import jobs_router
from app.collectors.models import CollectorQuery
from app.db.models import Base, Company, Job, JobSource
from app.schemas.job import PaginatedResponse


@pytest_asyncio.fixture(scope="module")
async def in_memory_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    in_memory_engine,
) -> AsyncGenerator[AsyncSession, Any]:
    session_factory = async_sessionmaker(
        in_memory_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def app(
    db_session: AsyncSession,
) -> FastAPI:
    app = FastAPI()
    app.include_router(jobs_router)

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, Any]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, Any]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seed_data(db_session: AsyncSession) -> dict[str, Any]:
    company1 = Company(name="Acme Corp", website="https://acme.com", industry="tech")
    company2 = Company(name="Globex Inc", website="https://globex.com", industry="finance")
    db_session.add_all([company1, company2])
    await db_session.flush()

    source1 = JobSource(name="greenhouse", is_active=True)
    source2 = JobSource(name="linkedin", is_active=True)
    db_session.add_all([source1, source2])
    await db_session.flush()

    now = datetime.now(timezone.utc)
    jobs = [
        Job(
            company_id=company1.id,
            source_id=source1.id,
            source_job_id="101",
            title="Software Engineer",
            location="San Francisco, CA",
            remote_type="hybrid",
            salary_min=120000,
            salary_max=160000,
            salary_currency="USD",
            employment_type="full-time",
            experience_level="mid",
            job_url="https://acme.com/jobs/101",
            status="discovered",
            is_active=True,
            posted_at=now,
            scraped_at=now,
        ),
        Job(
            company_id=company1.id,
            source_id=source1.id,
            source_job_id="102",
            title="Senior Engineer",
            location="Remote",
            remote_type="remote",
            salary_min=150000,
            salary_max=200000,
            salary_currency="USD",
            employment_type="full-time",
            experience_level="senior",
            job_url="https://acme.com/jobs/102",
            status="discovered",
            is_active=True,
            posted_at=now,
            scraped_at=now,
        ),
        Job(
            company_id=company2.id,
            source_id=source2.id,
            source_job_id="201",
            title="Data Analyst",
            location="New York, NY",
            remote_type="onsite",
            salary_min=80000,
            salary_max=110000,
            salary_currency="USD",
            employment_type="full-time",
            experience_level="entry",
            job_url="https://globex.com/jobs/201",
            status="analyzed",
            is_active=True,
            posted_at=now,
            scraped_at=now,
        ),
        Job(
            company_id=company2.id,
            source_id=source2.id,
            source_job_id="202",
            title="Contract Developer",
            location="Chicago, IL",
            remote_type="onsite",
            salary_min=100,
            salary_max=150,
            salary_currency="USD",
            employment_type="contract",
            experience_level="mid",
            job_url="https://globex.com/jobs/202",
            status="discovered",
            is_active=False,
            posted_at=now,
            scraped_at=now,
        ),
        Job(
            company_id=company1.id,
            source_id=source2.id,
            source_job_id="103",
            title="DevOps Engineer",
            location="Austin, TX",
            remote_type="remote",
            employment_type="full-time",
            experience_level="senior",
            job_url="https://acme.com/jobs/103",
            status="discovered",
            is_active=True,
            posted_at=now,
            scraped_at=now,
        ),
    ]
    db_session.add_all(jobs)
    await db_session.flush()

    return {
        "company1": company1,
        "company2": company2,
        "source1": source1,
        "source2": source2,
        "jobs": jobs,
    }


class TestListJobs:
    async def test_list_all_jobs(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5
        assert data["page"] == 1
        assert data["page_size"] == 20

    async def test_pagination(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3

    async def test_page_beyond_range(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs?page=10&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 0
        assert data["page"] == 10

    async def test_filter_by_status(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs?status=analyzed")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "analyzed"

    async def test_filter_by_remote_type(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs?remote_type=remote")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["remote_type"] == "remote"

    async def test_filter_by_employment_type(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs?employment_type=contract")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["employment_type"] == "contract"

    async def test_filter_by_experience_level(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs?experience_level=senior")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["experience_level"] == "senior"

    async def test_filter_by_is_active(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs?is_active=false")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["is_active"] is False

    async def test_filter_by_salary_min(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs?salary_min=150000")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert (item["salary_min"] is not None and item["salary_min"] >= 150000) or (
                item["salary_max"] is not None and item["salary_max"] >= 150000
            )

    async def test_filter_by_salary_max(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs?salary_max=110000")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert (item["salary_min"] is not None and item["salary_min"] <= 110000) or (
                item["salary_max"] is not None and item["salary_max"] <= 110000
            )

    async def test_search_by_title(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs?q=engineer")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3

    async def test_sort_by_title_asc(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs?sort_by=title&sort_order=asc")
        assert response.status_code == 200
        data = response.json()
        titles = [item["title"] for item in data["items"]]
        assert titles == sorted(titles)

    async def test_sort_by_company(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs?sort_by=company&sort_order=asc")
        assert response.status_code == 200
        data = response.json()
        companies = [item["company"]["name"] for item in data["items"]]
        assert companies == sorted(companies)

    async def test_response_includes_company(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert "company" in item
        assert "name" in item["company"]
        assert "id" in item["company"]

    async def test_response_includes_source(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert "source" in item
        assert "name" in item["source"]
        assert "id" in item["source"]


class TestGetJob:
    async def test_get_job_by_id(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        job = seed_data["jobs"][0]
        response = await client.get(f"/api/v1/jobs/{job.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == job.title
        assert data["id"] == str(job.id)
        assert "company" in data
        assert "source" in data
        assert "descriptions" in data

    async def test_get_job_not_found(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        fake_id = uuid4()
        response = await client.get(f"/api/v1/jobs/{fake_id}")
        assert response.status_code == 404
        assert "detail" in response.json()

    async def test_get_job_invalid_uuid(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/not-a-uuid")
        assert response.status_code == 422


class TestSearchJobs:
    async def test_search_by_keyword(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/search?q=engineer")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        for item in data["items"]:
            assert "engineer" in item["title"].lower()

    async def test_search_with_pagination(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/search?q=e&page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2

    async def test_search_no_results(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/search?q=xyznonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    async def test_search_missing_query(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/search")
        assert response.status_code == 422


class TestJobsByCompany:
    async def test_by_company_name(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/company/Acme")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        for item in data["items"]:
            assert "acme" in item["company"]["name"].lower()

    async def test_by_company_no_results(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/company/NonExistentCorp")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestJobsByLocation:
    async def test_by_location(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/location/San%20Francisco")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_by_location_no_results(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/location/Atlantis")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestJobsBySource:
    async def test_by_source_name(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/source/greenhouse")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        for item in data["items"]:
            assert item["source"]["name"] == "greenhouse"

    async def test_by_source_no_results(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/source/nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestRecentJobs:
    async def test_recent_jobs(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/recent")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    async def test_recent_jobs_with_limit(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs/recent?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestRefreshJobs:
    async def test_refresh_returns_accepted(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.post("/api/v1/jobs/refresh")
        assert response.status_code == 202
        data = response.json()
        assert "message" in data
        assert "query" in data

    async def test_refresh_with_params(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.post(
            "/api/v1/jobs/refresh?keywords=python&locations=remote&max_results=10"
        )
        assert response.status_code == 202
        data = response.json()
        assert data["query"]["keywords"] == ["python"]
        assert data["query"]["locations"] == ["remote"]
        assert data["query"]["max_results"] == 10


class TestResponseModels:
    async def test_job_response_shape(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert set(item.keys()) == {
            "id",
            "title",
            "location",
            "remote_type",
            "salary_min",
            "salary_max",
            "salary_currency",
            "employment_type",
            "experience_level",
            "job_url",
            "apply_url",
            "status",
            "is_active",
            "posted_at",
            "scraped_at",
            "created_at",
            "updated_at",
            "company",
            "source",
        }

    async def test_paginated_response_shape(
        self,
        client: AsyncClient,
        seed_data: dict[str, Any],
    ) -> None:
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"items", "total", "page", "page_size", "total_pages"}
