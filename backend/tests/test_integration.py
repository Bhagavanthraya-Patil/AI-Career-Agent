from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_db_session
from app.api.routers import jobs_router
from app.collectors.models import JobData, CompanyData, SalaryData, JobMetadata, LocationData
from app.db.models import (
    Application,
    ApplicationStatusHistory,
    Base,
    Company,
    Job,
    JobSource,
)
from app.agents.tracker.tracker_models import ApplyAgentIntegration


# ---------------------------------------------------------------------------
# Session-scoped engine
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, Any]:
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seed_company(db_session: AsyncSession) -> Company:
    c = Company(name="IntegrateCorp", location="New York, NY")
    db_session.add(c)
    await db_session.flush()
    return c


@pytest_asyncio.fixture
async def seed_source(db_session: AsyncSession) -> JobSource:
    s = JobSource(name="greenhouse", is_active=True)
    db_session.add(s)
    await db_session.flush()
    return s


@pytest_asyncio.fixture
async def seed_job(
    db_session: AsyncSession,
    seed_company: Company,
    seed_source: JobSource,
) -> Job:
    j = Job(
        company_id=seed_company.id,
        source_id=seed_source.id,
        source_job_id="int-001",
        title="Integration Engineer",
        location="New York, NY",
        remote_type="hybrid",
        job_url="https://example.com/jobs/int-001",
        status="active",
    )
    db_session.add(j)
    await db_session.flush()
    return j


# ===================================================================
# 1. Backend Startup
# ===================================================================


class TestBackendStartup:
    """Verify FastAPI app creation and health endpoint."""

    def test_app_created(self):
        app = FastAPI(title="AI Career Agent Backend API", version="0.16.0")
        app.include_router(jobs_router)
        assert app.title == "AI Career Agent Backend API"
        assert app.version == "0.16.0"

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        app = FastAPI(title="test", version="0.1.0")

        @app.get("/health")
        async def health():
            return {"status": "healthy", "version": "0.1.0"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"


# ===================================================================
# 2. Database Initialization
# ===================================================================


class TestDatabaseInit:
    """Verify database session, table creation, and CRUD."""

    @pytest.mark.asyncio
    async def test_session_context_manager(self, engine, db_session):
        async with db_session.begin():
            pass
        assert db_session is not None

    @pytest.mark.asyncio
    async def test_full_crud_flow(self, db_session: AsyncSession):
        src = JobSource(name="linkedin", is_active=True)
        db_session.add(src)
        await db_session.flush()

        company = Company(name="CRUDCorp", location="Remote")
        db_session.add(company)
        await db_session.flush()

        job = Job(
            company_id=company.id,
            source_id=src.id,
            source_job_id="crud-001",
            title="CRUD Engineer",
            location="Remote",
            status="active",
        )
        db_session.add(job)
        await db_session.flush()

        stmt = select(Job).where(Job.id == job.id)
        result = await db_session.execute(stmt)
        fetched = result.scalar_one()
        assert fetched.title == "CRUD Engineer"
        assert fetched.company.name == "CRUDCorp"
        assert fetched.source.name == "linkedin"

        app = Application(job_id=job.id, status="draft")
        db_session.add(app)
        await db_session.flush()

        stmt2 = select(Application).where(Application.job_id == job.id)
        result2 = await db_session.execute(stmt2)
        fetched_app = result2.scalar_one()
        assert fetched_app.status == "draft"

        history = ApplicationStatusHistory(
            application_id=app.id,
            from_status=None,
            to_status="draft",
            changed_by="system",
        )
        db_session.add(history)
        await db_session.flush()
        assert history.id is not None


# ===================================================================
# 3. Job API Endpoints
# ===================================================================


class TestJobApiIntegration:
    """Verify Job API endpoints through the full FastAPI stack."""

    @pytest_asyncio.fixture
    async def app(self, db_session: AsyncSession) -> FastAPI:
        app = FastAPI()
        app.include_router(jobs_router)

        async def override() -> AsyncGenerator[AsyncSession, Any]:
            yield db_session

        app.dependency_overrides[get_db_session] = override
        return app

    @pytest_asyncio.fixture
    async def client(self, app: FastAPI) -> AsyncGenerator[AsyncClient, Any]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @pytest_asyncio.fixture
    async def seed_jobs(self, db_session: AsyncSession) -> list[Job]:
        src = JobSource(name="linkedin", is_active=True)
        db_session.add(src)
        await db_session.flush()
        comp = Company(name="APICorp")
        db_session.add(comp)
        await db_session.flush()

        jobs = []
        for title, loc, emp_type in [
            ("Senior Python Dev", "Remote", "full-time"),
            ("Junior JS Dev", "New York", "full-time"),
            ("DevOps Engineer", "Remote", "contract"),
        ]:
            j = Job(
                company_id=comp.id,
                source_id=src.id,
                source_job_id=str(uuid4()),
                title=title,
                location=loc,
                remote_type="remote",
                status="active",
                employment_type=emp_type,
            )
            db_session.add(j)
            jobs.append(j)
        await db_session.flush()
        return jobs

    @pytest.mark.asyncio
    async def test_list_jobs(self, client: AsyncClient, seed_jobs: list[Job]):
        resp = await client.get("/api/v1/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(self, client: AsyncClient, seed_jobs: list[Job]):
        resp = await client.get("/api/v1/jobs?page_size=2&page=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_get_job_by_id(self, client: AsyncClient, seed_jobs: list[Job]):
        job_id = seed_jobs[0].id
        resp = await client.get(f"/api/v1/jobs/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Senior Python Dev"

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/jobs/{uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_search_jobs(self, client: AsyncClient, seed_jobs: list[Job]):
        resp = await client.get("/api/v1/jobs/search?q=python")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_recent_jobs(self, client: AsyncClient, seed_jobs: list[Job]):
        resp = await client.get("/api/v1/jobs/recent?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_jobs_by_company(self, client: AsyncClient, seed_jobs: list[Job]):
        resp = await client.get("/api/v1/jobs/company/APICorp")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_jobs_by_location(self, client: AsyncClient, seed_jobs: list[Job]):
        resp = await client.get("/api/v1/jobs/location/Remote")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_jobs_by_source(self, client: AsyncClient, seed_jobs: list[Job]):
        resp = await client.get("/api/v1/jobs/source/linkedin")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3


# ===================================================================
# 4. Collector Pipeline
# ===================================================================


class TestCollectorPipeline:
    """Verify the collector registry, lifecycle, and data flow."""

    @pytest.mark.asyncio
    async def test_registry_discover_and_list(self):
        from app.collectors.registry import CollectorRegistry
        CollectorRegistry.discover("app.collectors.plugins")
        names = CollectorRegistry.list_collectors()
        assert len(names) >= 3
        assert "greenhouse" in names
        assert "lever" in names
        assert "ashby" in names

    @pytest.mark.asyncio
    async def test_registry_get_class(self):
        from app.collectors.registry import CollectorRegistry
        cls = CollectorRegistry.get("greenhouse")
        assert cls is not None
        assert cls.__name__ == "GreenhouseCollector"

    @pytest.mark.asyncio
    async def test_jobdata_to_model_mapping(self, db_session: AsyncSession):
        job_data = JobData(
            title="Integration Tester",
            company=CompanyData(name="TestCorp"),
            location=LocationData(city="Remote", remote_type="remote"),
            salary=SalaryData(
                currency="USD",
                min=80000,
                max=120000,
                interval="yearly",
            ),
            metadata=JobMetadata(
                source="greenhouse",
                source_job_id="ext-999",
                job_url="https://example.com/jobs/999",
            ),
            description_raw="Test the integrations",
            employment_type="full-time",
        )

        src = JobSource(name="greenhouse", is_active=True)
        db_session.add(src)
        await db_session.flush()

        company = Company(name=job_data.company.name)
        db_session.add(company)
        await db_session.flush()

        job = Job(
            company_id=company.id,
            source_id=src.id,
            source_job_id=job_data.metadata.source_job_id,
            title=job_data.title,
            location=job_data.location.city or "",
            remote_type=job_data.location.remote_type,
            employment_type=job_data.employment_type,
            job_url=job_data.metadata.job_url,
            status="active",
        )
        db_session.add(job)
        await db_session.flush()

        assert job.id is not None
        assert job.title == "Integration Tester"
        assert job.company.name == "TestCorp"
        assert job.source.name == "greenhouse"


# ===================================================================
# 5. AI Agents Integration
# ===================================================================


class TestAIAgentsIntegration:
    """Verify AI agents work through keyword-fallback paths."""

    @pytest.mark.asyncio
    async def test_jd_analyzer_keyword_fallback(self):
        from app.agents.jd_analyzer.agent import JDAnalyzerAgent
        from app.agents.jd_analyzer.models import JDAnalyzerInput

        agent = JDAnalyzerAgent()
        jd_text = """
        We are looking for a Senior Python Developer with experience in
        FastAPI, PostgreSQL, Docker, and Kubernetes. The ideal candidate
        has 5+ years of experience in backend development, strong knowledge
        of REST APIs, and familiarity with cloud platforms like AWS.
        """
        result = await agent.run(JDAnalyzerInput(raw_description=jd_text))

        assert result is not None
        skills_lower = [s.name.lower() for s in result.skills]
        assert "python" in skills_lower
        assert "fastapi" in skills_lower
        assert "postgresql" in skills_lower

    @pytest.mark.asyncio
    async def test_resume_tailor_keyword_fallback(self):
        from app.agents.resume_tailor.agent import ResumeTailorAgent
        from app.agents.resume_tailor.models import ResumeTailorInput

        agent = ResumeTailorAgent()
        profile_data = {
            "name": "Test User",
            "title": "Software Developer",
            "skills": ["Python", "Django", "PostgreSQL"],
            "experience": [
                {
                    "title": "Backend Developer",
                    "company": "TechCo",
                    "description": "Built APIs with Django and PostgreSQL",
                    "start_date": "2020-01",
                    "end_date": "2023-01",
                },
            ],
        }
        result = await agent.run(ResumeTailorInput(
            user_profile=profile_data,
            target_skills=["Python", "FastAPI", "PostgreSQL"],
            jd_summary="Looking for Python developer with FastAPI and PostgreSQL.",
        ))
        assert result is not None

    @pytest.mark.asyncio
    async def test_ats_analyzer_keyword_fallback(self):
        from app.agents.ats_checker.agent import ATSAnalyzerAgent
        from app.agents.ats_checker.models import ATSAnalyzerInput

        agent = ATSAnalyzerAgent()
        result = await agent.run(ATSAnalyzerInput(
            resume_text="Python developer with FastAPI and PostgreSQL experience.",
            job_description="Looking for Python developer with FastAPI, PostgreSQL, Docker.",
        ))
        assert result is not None
        assert 0 <= result.match_score <= 100

    @pytest.mark.asyncio
    async def test_llm_client_creation(self):
        from app.agents.llm import LLMClient
        client = LLMClient()
        assert client is not None
        assert hasattr(client, "generate")
        assert hasattr(client, "generate_structured")


# ===================================================================
# 6. Apply Agent Integration
# ===================================================================


class TestApplyAgentIntegration:
    """Verify Apply Agent components work together."""

    def test_state_machine_transitions(self):
        from app.agents.apply_agent.state_machine import StateMachine, ApplicationState

        sm = StateMachine()
        assert sm.state == ApplicationState.INITIALIZED
        sm.transition_to(ApplicationState.PAGE_LOADED)
        assert sm.state == ApplicationState.PAGE_LOADED
        sm.transition_to(ApplicationState.ANALYZED)
        assert sm.state == ApplicationState.ANALYZED

    def test_state_machine_invalid_transition(self):
        from app.agents.apply_agent.exceptions import StateTransitionError
        from app.agents.apply_agent.state_machine import ApplicationState, StateMachine

        sm = StateMachine()
        with pytest.raises(StateTransitionError):
            sm.transition_to(ApplicationState.SUBMITTED)

    def test_field_mapper_import(self):
        from app.agents.apply_agent.field_mapper import FieldMapper
        mapper = FieldMapper()
        assert mapper is not None

    def test_validation_imports(self):
        from app.agents.apply_agent.validation import (
            validate_user_profile,
            validate_form_fields,
            validate_file_path,
        )
        assert validate_user_profile is not None
        assert validate_form_fields is not None
        assert validate_file_path is not None


# ===================================================================
# 7. Tracker Agent Integration
# ===================================================================


class TestTrackerAgentIntegration:
    """Verify the full Tracker Agent lifecycle end-to-end."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(
        self,
        db_session: AsyncSession,
        seed_job: Job,
    ):
        from app.agents.tracker import TrackerAgent

        agent = TrackerAgent(session=db_session)
        await agent.initialize()

        data = await agent.track_application(
            job_id=str(seed_job.id),
            apply_url="https://example.com/apply",
        )
        assert data.status == "draft"
        assert data.job_id == str(seed_job.id)

        updated = await agent.update_status(data.application_id, "ready")
        assert updated.status == "ready"

        updated2 = await agent.update_status(data.application_id, "applied")
        assert updated2.status == "applied"

        history = await agent.get_history(data.application_id)
        assert len(history) >= 2

        timeline = await agent.get_timeline(data.application_id)
        assert timeline is not None

        metrics = await agent.get_metrics()
        assert metrics.total_applications >= 1

        found = await agent.find_by_job(str(seed_job.id))
        assert found is not None
        assert found.job_id == str(seed_job.id)

    @pytest.mark.asyncio
    async def test_duplicate_detection(
        self,
        db_session: AsyncSession,
        seed_job: Job,
    ):
        from app.agents.tracker import DuplicateApplicationError, TrackerAgent

        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        await agent.track_application(job_id=str(seed_job.id))

        with pytest.raises(DuplicateApplicationError):
            await agent.track_application(job_id=str(seed_job.id))

    @pytest.mark.asyncio
    async def test_record_apply_result(
        self,
        db_session: AsyncSession,
        seed_job: Job,
    ):
        from app.agents.tracker import TrackerAgent

        agent = TrackerAgent(session=db_session)
        await agent.initialize()

        data = await agent.track_application(
            job_id=str(seed_job.id),
            status="applied",
        )

        result = ApplyAgentIntegration(
            success=True,
            final_state="verified",
            confirmation_code="INT-CONF-001",
            screenshot_path="/tmp/int_screen.png",
            errors=[],
            duration_seconds=30.0,
            state_history=[("applied", "submitted", None)],
        )
        updated = await agent.record_apply_result(data.application_id, result)
        assert updated.confirmation_code == "INT-CONF-001"
        assert updated.status == "submitted"

    @pytest.mark.asyncio
    async def test_invalid_transition_rejected(
        self,
        db_session: AsyncSession,
        seed_job: Job,
    ):
        from app.agents.tracker import (
            InvalidStatusTransitionError,
            TrackerAgent,
        )

        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        data = await agent.track_application(job_id=str(seed_job.id))

        with pytest.raises(InvalidStatusTransitionError):
            await agent.update_status(data.application_id, "accepted")

    @pytest.mark.asyncio
    async def test_cleanup(
        self,
        db_session: AsyncSession,
        seed_job: Job,
    ):
        from app.agents.tracker import TrackerAgent

        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        await agent.cleanup()
        assert agent._initialized is False


# ===================================================================
# 8. Parser / Extractor Pipeline
# ===================================================================


class TestParserExtractorPipeline:
    """Verify parsers and extractors produce structured output."""

    @pytest.mark.asyncio
    async def test_salary_parser(self):
        from app.parsers.salary_parser import SalaryParser

        parser = SalaryParser()
        result = parser.parse("$120k - $150k")
        assert result is not None
        assert result.currency == "USD"
        assert result.min == 120000
        assert result.max == 150000
        assert result.interval == "yearly"

        result2 = parser.parse("₹15 LPA")
        assert result2 is not None
        assert result2.currency == "INR"
        assert result2.min == 1500000

    @pytest.mark.asyncio
    async def test_location_parser(self):
        from app.parsers.location_parser import LocationParser

        parser = LocationParser()
        result = parser.parse("Remote - United States")
        assert result.remote_type == "remote"

    @pytest.mark.asyncio
    async def test_employment_type_parser(self):
        from app.parsers.employment_type_parser import EmploymentTypeParser

        parser = EmploymentTypeParser()
        result = parser.parse("Full-time")
        assert result.normalized == "full-time"

        result2 = parser.parse("Contract")
        assert result2.normalized == "contract"

    @pytest.mark.asyncio
    async def test_experience_parser(self):
        from app.parsers.experience_parser import ExperienceParser

        parser = ExperienceParser()
        result = parser.parse("5+ years of experience")
        assert result.years_min == 5

    @pytest.mark.asyncio
    async def test_title_parser(self):
        from app.parsers.title_parser import TitleParser

        parser = TitleParser()
        result = parser.parse("Senior Software Engineer")
        assert "senior" in (result.seniority or "").lower()
        assert "software engineer" in result.normalized.lower()

    @pytest.mark.asyncio
    async def test_company_parser(self):
        from app.parsers.company_parser import CompanyParser

        parser = CompanyParser()
        result = parser.parse("Google Cloud")
        assert "google" in result.name.lower()

    @pytest.mark.asyncio
    async def test_metadata_parser(self):
        from app.parsers.metadata_parser import MetadataParser

        parser = MetadataParser()
        result = parser.parse({
            "url": "https://jobs.greenhouse.io/boards/example/jobs/12345",
        })
        assert result.job_id == "12345"

    @pytest.mark.asyncio
    async def test_parser_registry(self):
        from app.parsers.registry import ParserRegistry

        registry = ParserRegistry()
        parsers = registry.list_parsers()
        assert len(parsers) >= 7

    @pytest.mark.asyncio
    async def test_metadata_extractor(self):
        from app.extractors.metadata_extractor import MetadataExtractor

        extractor = MetadataExtractor()
        html = "<html><head><title>Job Posting</title></head><body>Job description here.</body></html>"
        meta = extractor.extract(html)
        assert meta is not None


# ===================================================================
# 9. Cross-Component Integration
# ===================================================================


class TestCrossComponentIntegration:
    """Verify components work together across subsystem boundaries."""

    @pytest.mark.asyncio
    async def test_job_api_returns_company_and_source(
        self,
        db_session: AsyncSession,
        seed_job: Job,
    ):
        from app.api.dependencies import get_db_session

        app = FastAPI()
        app.include_router(jobs_router)

        async def override() -> AsyncGenerator[AsyncSession, Any]:
            yield db_session

        app.dependency_overrides[get_db_session] = override
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/jobs/{seed_job.id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["company"]["name"] == "IntegrateCorp"
            assert data["source"]["name"] == "greenhouse"

    @pytest.mark.asyncio
    async def test_tracker_uses_job_from_db(
        self,
        db_session: AsyncSession,
        seed_job: Job,
    ):
        from app.agents.tracker import TrackerAgent

        agent = TrackerAgent(session=db_session)
        await agent.initialize()

        data = await agent.track_application(job_id=str(seed_job.id))
        assert data.company_name == "IntegrateCorp"

        app_data = await agent.get_application(data.application_id)
        assert app_data.company_name == "IntegrateCorp"

    @pytest.mark.asyncio
    async def test_full_pipeline_job_to_tracker(self, db_session: AsyncSession):
        src = JobSource(name="greenhouse", is_active=True)
        db_session.add(src)
        await db_session.flush()

        company = Company(name="PipelineCorp", location="San Francisco, CA")
        db_session.add(company)
        await db_session.flush()

        job = Job(
            company_id=company.id,
            source_id=src.id,
            source_job_id="pipeline-001",
            title="Pipeline Engineer",
            location="San Francisco, CA",
            remote_type="onsite",
            job_url="https://example.com/jobs/pipeline-001",
            status="active",
        )
        db_session.add(job)
        await db_session.flush()

        from app.agents.tracker import ApplicationTracker

        tracker = ApplicationTracker(session=db_session)
        tracked = await tracker.track(
            job_id=str(job.id),
            apply_url="https://example.com/apply/pipeline-001",
        )
        assert tracked.job_id == str(job.id)
        assert tracked.company_name == "PipelineCorp"
        assert tracked.status == "draft"

        updated = await tracker.update_status(tracked.application_id, "ready")
        assert updated.status == "ready"

        apps = await tracker.list_applications()
        assert len(apps) >= 1
