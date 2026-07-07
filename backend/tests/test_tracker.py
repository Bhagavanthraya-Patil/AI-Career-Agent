from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents.tracker import (
    ApplicationNotFoundError,
    ApplicationRepository,
    ApplicationStatusData,
    ApplicationTracker,
    ApplyAgentIntegration,
    DuplicateApplicationError,
    HistoryManager,
    InvalidStatusError,
    InvalidStatusTransitionError,
    Metrics,
    StatusChangeEvent,
    StatusManager,
    Timeline,
    TrackerAgent,
    TrackerConfig,
    TrackerError,
    TrackerMetrics,
)
from app.agents.tracker.exceptions import (
    CleanupError,
    DuplicateHistoryEntryError,
    MetricsComputationError,
    TimelineBuildError,
)
from app.agents.tracker.status_manager import (
    TERMINAL_STATUSES,
    VALID_STATUSES,
)
from app.agents.tracker.tracker_models import (
    ApplicationTimeline,
    HistoryEntry,
    TimelineEntry,
)
from app.db.models import Application, ApplicationStatusHistory, Base, Company, Job, JobSource


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
def in_memory_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    return engine


@pytest_asyncio.fixture
async def tables(in_memory_engine):
    async with in_memory_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with in_memory_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(
    in_memory_engine,
    tables,
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
async def seed_job_source(db_session: AsyncSession) -> JobSource:
    source = JobSource(name="greenhouse", is_active=True)
    db_session.add(source)
    await db_session.flush()
    return source


@pytest_asyncio.fixture
async def seed_company(db_session: AsyncSession) -> Company:
    company = Company(name="TestCorp", location="San Francisco, CA")
    db_session.add(company)
    await db_session.flush()
    return company


@pytest_asyncio.fixture
async def seed_job(
    db_session: AsyncSession,
    seed_company: Company,
    seed_job_source: JobSource,
) -> Job:
    job = Job(
        company_id=seed_company.id,
        source_id=seed_job_source.id,
        source_job_id="ext-123",
        title="Software Engineer",
        location="San Francisco, CA",
        remote_type="hybrid",
        job_url="https://example.com/jobs/123",
        status="discovered",
    )
    db_session.add(job)
    await db_session.flush()
    return job


@pytest_asyncio.fixture
async def seed_application(
    db_session: AsyncSession,
    seed_job: Job,
) -> Application:
    app = Application(
        job_id=seed_job.id,
        status="draft",
        apply_url="https://example.com/apply",
    )
    db_session.add(app)
    await db_session.flush()
    return app


# ---------------------------------------------------------------------------
# StatusManager Tests
# ---------------------------------------------------------------------------


class TestStatusManager:
    def test_valid_statuses(self):
        assert "draft" in VALID_STATUSES
        assert "accepted" in VALID_STATUSES
        assert "rejected" in VALID_STATUSES
        assert "invalid_status" not in VALID_STATUSES

    def test_validate_status_valid(self):
        StatusManager.validate_status("draft")
        StatusManager.validate_status("accepted")

    def test_validate_status_invalid(self):
        with pytest.raises(InvalidStatusError) as exc:
            StatusManager.validate_status("not_a_real_status")
        assert "not_a_real_status" in str(exc.value)

    def test_valid_transition(self):
        StatusManager.validate_transition("draft", "ready")

    def test_invalid_transition_raises(self):
        with pytest.raises(InvalidStatusTransitionError) as exc:
            StatusManager.validate_transition("draft", "accepted")
        assert "draft" in str(exc.value)
        assert "accepted" in str(exc.value)

    def test_full_lifecycle(self):
        transitions = [
            ("draft", "ready"),
            ("ready", "applied"),
            ("applied", "submitted"),
            ("submitted", "viewed"),
            ("viewed", "assessment"),
            ("assessment", "interview"),
            ("interview", "technical_interview"),
            ("technical_interview", "hr_interview"),
            ("hr_interview", "offer"),
            ("offer", "accepted"),
        ]
        for from_s, to_s in transitions:
            StatusManager.validate_transition(from_s, to_s)

    def test_rejection_from_multiple_states(self):
        rejectable = ["viewed", "assessment", "interview", "technical_interview", "hr_interview", "offer"]
        for state in rejectable:
            StatusManager.validate_transition(state, "rejected")

    def test_terminal_states_have_no_transitions(self):
        for terminal in TERMINAL_STATUSES:
            allowed = StatusManager.get_allowed_transitions(terminal)
            assert allowed == set()

    def test_get_allowed_transitions(self):
        allowed = StatusManager.get_allowed_transitions("draft")
        assert "ready" in allowed
        assert "cancelled" in allowed
        assert "accepted" not in allowed

    def test_is_terminal(self):
        assert StatusManager.is_terminal("accepted")
        assert StatusManager.is_terminal("rejected")
        assert not StatusManager.is_terminal("draft")

    def test_is_success(self):
        assert StatusManager.is_success("accepted")
        assert not StatusManager.is_success("rejected")

    def test_is_failure(self):
        assert StatusManager.is_failure("rejected")
        assert StatusManager.is_failure("failed")
        assert not StatusManager.is_failure("draft")

    def test_is_interview(self):
        assert StatusManager.is_interview("interview")
        assert StatusManager.is_interview("technical_interview")
        assert StatusManager.is_interview("hr_interview")
        assert not StatusManager.is_interview("offer")

    def test_is_offer(self):
        assert StatusManager.is_offer("offer")
        assert StatusManager.is_offer("accepted")
        assert not StatusManager.is_offer("interview")

    def test_is_active(self):
        assert StatusManager.is_active("draft")
        assert not StatusManager.is_active("accepted")

    def test_failed_can_retry(self):
        StatusManager.validate_transition("failed", "ready")
        StatusManager.validate_transition("failed", "draft")

    def test_invalid_from_status_raises(self):
        with pytest.raises(InvalidStatusError):
            StatusManager.validate_transition("bogus", "draft")

    def test_invalid_to_status_raises(self):
        with pytest.raises(InvalidStatusError):
            StatusManager.validate_transition("draft", "bogus")

    def test_terminal_status_sets(self):
        for s in TERMINAL_STATUSES:
            assert s in VALID_STATUSES


# ---------------------------------------------------------------------------
# ApplicationRepository Tests
# ---------------------------------------------------------------------------


class TestApplicationRepository:
    @pytest.mark.asyncio
    async def test_create_application(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        app = await repo.create_application(
            job_id=str(seed_job.id),
            status="draft",
        )
        assert app is not None
        assert app.status == "draft"
        assert str(app.job_id) == str(seed_job.id)

    @pytest.mark.asyncio
    async def test_create_application_duplicate_raises(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        await repo.create_application(job_id=str(seed_job.id))
        with pytest.raises(DuplicateApplicationError):
            await repo.create_application(job_id=str(seed_job.id))

    @pytest.mark.asyncio
    async def test_get_application(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        app = await repo.create_application(job_id=str(seed_job.id))
        fetched = await repo.get_application(str(app.id))
        assert str(fetched.id) == str(app.id)
        assert fetched.status == "draft"

    @pytest.mark.asyncio
    async def test_get_application_not_found(self, db_session):
        repo = ApplicationRepository(session=db_session)
        with pytest.raises(ApplicationNotFoundError):
            await repo.get_application(str(uuid.uuid4()))

    @pytest.mark.asyncio
    async def test_update_status(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        app = await repo.create_application(job_id=str(seed_job.id), status="draft")
        updated = await repo.update_status(
            str(app.id),
            new_status="ready",
            changed_by="user",
            reason="Ready to apply",
        )
        assert updated.status == "ready"

    @pytest.mark.asyncio
    async def test_update_status_records_history(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        app = await repo.create_application(job_id=str(seed_job.id))
        await repo.update_status(str(app.id), "ready")
        await repo.update_status(str(app.id), "applied")

        history = await repo.get_application_with_relations(str(app.id))
        assert len(history.status_history) == 2

    @pytest.mark.asyncio
    async def test_update_status_invalid_transition(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        app = await repo.create_application(job_id=str(seed_job.id), status="draft")
        with pytest.raises(InvalidStatusTransitionError):
            await repo.update_status(str(app.id), "accepted")

    @pytest.mark.asyncio
    async def test_list_applications(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        await repo.create_application(job_id=str(seed_job.id))
        await repo.create_application(
            job_id=str(uuid.uuid4()),
            status="draft",
        )
        apps = await repo.list_applications(limit=100)
        assert len(apps) >= 2

    @pytest.mark.asyncio
    async def test_find_by_job(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        app = await repo.create_application(job_id=str(seed_job.id))
        found = await repo.find_by_job(str(seed_job.id))
        assert found is not None
        assert str(found.id) == str(app.id)

    @pytest.mark.asyncio
    async def test_find_by_job_not_found(self, db_session):
        repo = ApplicationRepository(session=db_session)
        found = await repo.find_by_job(str(uuid.uuid4()))
        assert found is None

    @pytest.mark.asyncio
    async def test_update_application_fields(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        app = await repo.create_application(job_id=str(seed_job.id))
        updated = await repo.update_application(
            str(app.id),
            notes="Test note",
            rating=4,
        )
        assert updated.notes == "Test note"
        assert updated.rating == 4

    @pytest.mark.asyncio
    async def test_delete_application_soft(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        app = await repo.create_application(job_id=str(seed_job.id))
        await repo.delete_application(str(app.id))

        apps = await repo.list_applications(is_active=True)
        assert len(apps) == 0

    @pytest.mark.asyncio
    async def test_count_applications(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        await repo.create_application(job_id=str(seed_job.id))
        count = await repo.count_applications()
        assert count >= 1

    @pytest.mark.asyncio
    async def test_get_status_data(self, db_session, seed_job, seed_company):
        repo = ApplicationRepository(session=db_session)
        app = await repo.create_application(job_id=str(seed_job.id))
        data = await repo.get_status_data(str(app.id))
        assert data.application_id == str(app.id)
        assert data.job_id == str(seed_job.id)
        assert data.company_name == "TestCorp"
        assert data.status == "draft"

    @pytest.mark.asyncio
    async def test_hard_delete(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        app = await repo.create_application(job_id=str(seed_job.id))
        await repo.hard_delete_application(str(app.id))
        with pytest.raises(ApplicationNotFoundError):
            await repo.get_application(str(app.id))

    @pytest.mark.asyncio
    async def test_apply_url_stored(self, db_session, seed_job):
        repo = ApplicationRepository(session=db_session)
        app = await repo.create_application(
            job_id=str(seed_job.id),
            apply_url="https://example.com/apply",
        )
        assert app.apply_url == "https://example.com/apply"


# ---------------------------------------------------------------------------
# HistoryManager Tests
# ---------------------------------------------------------------------------


class TestHistoryManager:
    @pytest.mark.asyncio
    async def test_record_event(self, db_session, seed_application):
        mgr = HistoryManager()
        event = StatusChangeEvent(
            application_id=str(seed_application.id),
            from_status="draft",
            to_status="ready",
            changed_by="user",
            reason="Ready to go",
        )
        entry = await mgr.record_event(db_session, event)
        assert entry.to_status == "ready"
        assert entry.from_status == "draft"
        assert entry.reason == "Ready to go"

    @pytest.mark.asyncio
    async def test_get_history(self, db_session, seed_application):
        mgr = HistoryManager()
        event1 = StatusChangeEvent(
            application_id=str(seed_application.id),
            from_status=None,
            to_status="draft",
            changed_by="system",
        )
        event2 = StatusChangeEvent(
            application_id=str(seed_application.id),
            from_status="draft",
            to_status="ready",
            changed_by="user",
        )
        await mgr.record_event(db_session, event1)
        await mgr.record_event(db_session, event2)

        history = await mgr.get_history(db_session, str(seed_application.id))
        assert len(history) == 2
        assert history[0].to_status == "draft"
        assert history[1].to_status == "ready"

    @pytest.mark.asyncio
    async def test_get_latest_event(self, db_session, seed_application):
        mgr = HistoryManager()
        await mgr.record_event(
            db_session,
            StatusChangeEvent(
                application_id=str(seed_application.id),
                from_status=None,
                to_status="draft",
            ),
        )
        await mgr.record_event(
            db_session,
            StatusChangeEvent(
                application_id=str(seed_application.id),
                from_status="draft",
                to_status="ready",
            ),
        )
        latest = await mgr.get_latest_event(db_session, str(seed_application.id))
        assert latest is not None
        assert latest.to_status == "ready"

    @pytest.mark.asyncio
    async def test_get_latest_event_empty(self, db_session):
        mgr = HistoryManager()
        latest = await mgr.get_latest_event(db_session, str(uuid.uuid4()))
        assert latest is None

    def test_build_event_validates(self):
        mgr = HistoryManager()
        event = mgr.build_event(
            application_id=str(uuid.uuid4()),
            from_status="draft",
            to_status="ready",
            changed_by="user",
        )
        assert event.to_status == "ready"
        assert event.changed_by == "user"

    def test_build_event_invalid_raises(self):
        mgr = HistoryManager()
        with pytest.raises(InvalidStatusTransitionError):
            mgr.build_event(
                application_id=str(uuid.uuid4()),
                from_status="draft",
                to_status="accepted",
            )


# ---------------------------------------------------------------------------
# Metrics Tests
# ---------------------------------------------------------------------------


class TestMetrics:
    @pytest.mark.asyncio
    async def test_empty_metrics(self):
        metrics = Metrics()
        result = await metrics.compute([])
        assert result.total_applications == 0
        assert result.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_compute_with_applications(self, db_session, seed_job, seed_company):
        from app.db.models.application import Application

        apps = []
        for status in ["accepted", "rejected", "draft", "interview"]:
            app = Application(
                job_id=seed_job.id,
                status=status,
            )
            # Manually set job relationship for company name extraction
            app.job = seed_job
            apps.append(app)

        metrics_obj = Metrics()
        result = await metrics_obj.compute(apps)
        assert result.total_applications == 4
        assert result.success_count == 1
        assert result.failure_count == 1
        assert result.interview_count == 1
        assert result.offer_count == 1  # accepted is an offer status

    @pytest.mark.asyncio
    async def test_by_status_breakdown(self, db_session, seed_job):
        from app.db.models.application import Application

        apps = []
        for status in ["draft", "draft", "ready", "applied"]:
            app = Application(job_id=seed_job.id, status=status)
            app.job = seed_job
            apps.append(app)

        metrics_obj = Metrics()
        result = await metrics_obj.compute(apps)
        assert result.by_status.get("draft") == 2
        assert result.by_status.get("ready") == 1
        assert result.by_status.get("applied") == 1

    @pytest.mark.asyncio
    async def test_metrics_to_dict(self):
        metrics = TrackerMetrics(
            total_applications=10,
            success_count=3,
            success_rate=30.0,
        )
        d = metrics.to_dict()
        assert d["total_applications"] == 10
        assert d["success_rate"] == 30.0

    @pytest.mark.asyncio
    async def test_compute_for_application(self, db_session, seed_application):
        metrics_obj = Metrics()
        result = await metrics_obj.compute_for_application(seed_application, db_session)
        assert result["status"] == "draft"
        assert result["is_terminal"] is False


# ---------------------------------------------------------------------------
# Timeline Tests
# ---------------------------------------------------------------------------


class TestTimeline:
    @pytest.mark.asyncio
    async def test_build_timeline(self, db_session, seed_application):
        from app.db.models.application_status_history import (
            ApplicationStatusHistory,
        )

        hist = ApplicationStatusHistory(
            application_id=seed_application.id,
            from_status="draft",
            to_status="ready",
            changed_by="user",
            reason="Prepared",
        )
        db_session.add(hist)
        await db_session.flush()

        timeline = Timeline()
        result = await timeline.build(db_session, seed_application)
        assert isinstance(result, ApplicationTimeline)
        assert len(result.entries) >= 2  # creation + status change

    @pytest.mark.asyncio
    async def test_timeline_includes_offer_events(self, db_session, seed_application):
        from app.db.models.application_status_history import (
            ApplicationStatusHistory,
        )

        hist = ApplicationStatusHistory(
            application_id=seed_application.id,
            from_status="hr_interview",
            to_status="offer",
            changed_by="system",
        )
        db_session.add(hist)
        await db_session.flush()

        timeline = Timeline()
        result = await timeline.build(db_session, seed_application)
        offer_entries = [e for e in result.entries if e.event_type == "offer"]
        assert len(offer_entries) >= 1

    def test_timeline_entry_to_dict(self):
        entry = TimelineEntry(
            event_type="status_change",
            timestamp=datetime.now(timezone.utc),
            title="Status Update",
            description="Changed to applied",
        )
        d = entry.to_dict()
        assert d["event_type"] == "status_change"
        assert d["title"] == "Status Update"

    def test_timeline_to_dict(self):
        timeline = ApplicationTimeline(
            application_id=str(uuid.uuid4()),
            entries=[
                TimelineEntry(
                    event_type="status_change",
                    timestamp=datetime.now(timezone.utc),
                    title="Created",
                ),
            ],
        )
        d = timeline.to_dict()
        assert d["application_id"] is not None
        assert len(d["entries"]) == 1


# ---------------------------------------------------------------------------
# ApplicationTracker Tests
# ---------------------------------------------------------------------------


class TestApplicationTracker:
    @pytest.mark.asyncio
    async def test_track_new_application(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        data = await tracker.track(
            job_id=str(seed_job.id),
            apply_url="https://example.com/apply",
        )
        assert data.status == "draft"
        assert data.job_id == str(seed_job.id)

    @pytest.mark.asyncio
    async def test_track_duplicate_raises(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        await tracker.track(job_id=str(seed_job.id))
        with pytest.raises(DuplicateApplicationError):
            await tracker.track(job_id=str(seed_job.id))

    @pytest.mark.asyncio
    async def test_update_status(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        data = await tracker.track(job_id=str(seed_job.id))
        updated = await tracker.update_status(
            data.application_id,
            "ready",
            changed_by="user",
        )
        assert updated.status == "ready"

    @pytest.mark.asyncio
    async def test_update_status_records_history(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        data = await tracker.track(job_id=str(seed_job.id))
        await tracker.update_status(data.application_id, "ready")
        await tracker.update_status(data.application_id, "applied")

        history = await tracker.get_history(data.application_id)
        assert len(history) >= 2

    @pytest.mark.asyncio
    async def test_get_application(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        data = await tracker.track(job_id=str(seed_job.id))
        fetched = await tracker.get_application(data.application_id)
        assert fetched.application_id == data.application_id
        assert fetched.company_name == "TestCorp"

    @pytest.mark.asyncio
    async def test_find_by_job(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        await tracker.track(job_id=str(seed_job.id))
        found = await tracker.find_by_job(str(seed_job.id))
        assert found is not None
        assert found.job_id == str(seed_job.id)

    @pytest.mark.asyncio
    async def test_find_by_job_not_tracked(self, db_session):
        tracker = ApplicationTracker(session=db_session)
        found = await tracker.find_by_job(str(uuid.uuid4()))
        assert found is None

    @pytest.mark.asyncio
    async def test_list_applications(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        await tracker.track(job_id=str(seed_job.id), notes="Test note")
        apps = await tracker.list_applications()
        assert len(apps) >= 1

    @pytest.mark.asyncio
    async def test_list_applications_by_status(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        await tracker.track(job_id=str(seed_job.id))
        apps = await tracker.list_applications(status="draft")
        assert len(apps) >= 1
        apps = await tracker.list_applications(status="accepted")
        assert len(apps) == 0

    @pytest.mark.asyncio
    async def test_get_timeline(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        data = await tracker.track(job_id=str(seed_job.id))
        timeline = await tracker.get_timeline(data.application_id)
        assert isinstance(timeline, ApplicationTimeline)
        assert len(timeline.entries) >= 1

    @pytest.mark.asyncio
    async def test_compute_metrics_empty(self, db_session):
        tracker = ApplicationTracker(session=db_session)
        metrics = await tracker.compute_metrics()
        assert metrics.total_applications == 0

    @pytest.mark.asyncio
    async def test_count_by_status(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        await tracker.track(job_id=str(seed_job.id))
        counts = await tracker.count_by_status()
        assert isinstance(counts, dict)

    @pytest.mark.asyncio
    async def test_record_apply_result(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        data = await tracker.track(job_id=str(seed_job.id), status="applied")

        apply_result = ApplyAgentIntegration(
            success=True,
            final_state="verified",
            confirmation_code="CONF-123",
            screenshot_path="/tmp/screen.png",
            errors=[],
            duration_seconds=45.2,
            state_history=[("applied", "submitted", None)],
        )
        updated = await tracker.record_apply_result(
            data.application_id,
            apply_result,
        )
        assert updated.confirmation_code == "CONF-123"
        assert updated.screenshot_path == "/tmp/screen.png"
        # Status should be "submitted" on success
        assert updated.status == "submitted"

    @pytest.mark.asyncio
    async def test_record_apply_result_failure(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        data = await tracker.track(job_id=str(seed_job.id), status="applied")

        apply_result = ApplyAgentIntegration(
            success=False,
            final_state="failed",
            confirmation_code=None,
            screenshot_path=None,
            errors=["Network error"],
            duration_seconds=10.0,
            state_history=[],
        )
        updated = await tracker.record_apply_result(
            data.application_id,
            apply_result,
        )
        assert updated.status == "failed"

    @pytest.mark.asyncio
    async def test_update_application_fields(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        data = await tracker.track(job_id=str(seed_job.id))
        updated = await tracker.update_application(
            data.application_id,
            notes="Updated note",
            rating=5,
        )
        assert updated.notes == "Updated note"
        assert updated.rating == 5

    @pytest.mark.asyncio
    async def test_delete_application(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        data = await tracker.track(job_id=str(seed_job.id))
        await tracker.delete_application(data.application_id)
        apps = await tracker.list_applications()
        ids = [a.application_id for a in apps]
        assert data.application_id not in ids

    @pytest.mark.asyncio
    async def test_cleanup_inactive(self, db_session, seed_job):
        tracker = ApplicationTracker(session=db_session)
        data = await tracker.track(job_id=str(seed_job.id))
        await tracker.update_status(data.application_id, "ready")
        await tracker.update_status(data.application_id, "applied")
        await tracker.update_status(data.application_id, "submitted")
        await tracker.update_status(data.application_id, "viewed")
        await tracker.update_status(data.application_id, "assessment")
        await tracker.update_status(data.application_id, "interview")
        await tracker.update_status(data.application_id, "hr_interview")
        await tracker.update_status(data.application_id, "offer")
        await tracker.update_status(data.application_id, "accepted")
        count = await tracker.cleanup_inactive()
        assert count >= 1


# ---------------------------------------------------------------------------
# TrackerAgent Tests
# ---------------------------------------------------------------------------


class TestTrackerAgent:
    @pytest.mark.asyncio
    async def test_initialize(self, db_session):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        assert agent._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, db_session):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        await agent.initialize()
        assert agent._initialized is True

    @pytest.mark.asyncio
    async def test_track_application(self, db_session, seed_job):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        data = await agent.track_application(
            job_id=str(seed_job.id),
            apply_url="https://example.com/apply",
        )
        assert data.status == "draft"
        assert data.job_id == str(seed_job.id)

    @pytest.mark.asyncio
    async def test_update_status(self, db_session, seed_job):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        data = await agent.track_application(job_id=str(seed_job.id))
        updated = await agent.update_status(data.application_id, "ready")
        assert updated.status == "ready"

    @pytest.mark.asyncio
    async def test_get_history(self, db_session, seed_job):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        data = await agent.track_application(job_id=str(seed_job.id))
        await agent.update_status(data.application_id, "ready")
        history = await agent.get_history(data.application_id)
        assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_get_timeline(self, db_session, seed_job):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        data = await agent.track_application(job_id=str(seed_job.id))
        timeline = await agent.get_timeline(data.application_id)
        assert isinstance(timeline, ApplicationTimeline)

    @pytest.mark.asyncio
    async def test_get_metrics(self, db_session, seed_job):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        await agent.track_application(job_id=str(seed_job.id))
        metrics = await agent.get_metrics()
        assert isinstance(metrics, TrackerMetrics)
        assert metrics.total_applications >= 1

    @pytest.mark.asyncio
    async def test_get_application(self, db_session, seed_job):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        data = await agent.track_application(job_id=str(seed_job.id))
        fetched = await agent.get_application(data.application_id)
        assert fetched.application_id == data.application_id

    @pytest.mark.asyncio
    async def test_find_by_job(self, db_session, seed_job):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        await agent.track_application(job_id=str(seed_job.id))
        found = await agent.find_by_job(str(seed_job.id))
        assert found is not None

    @pytest.mark.asyncio
    async def test_list_applications(self, db_session, seed_job):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        await agent.track_application(job_id=str(seed_job.id))
        apps = await agent.list_applications()
        assert len(apps) >= 1

    @pytest.mark.asyncio
    async def test_delete_application(self, db_session, seed_job):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        data = await agent.track_application(job_id=str(seed_job.id))
        await agent.delete_application(data.application_id)
        apps = await agent.list_applications()
        assert len(apps) == 0

    @pytest.mark.asyncio
    async def test_cleanup(self, db_session):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        await agent.cleanup()
        assert agent._initialized is False

    @pytest.mark.asyncio
    async def test_uninitialized_raises(self, db_session):
        agent = TrackerAgent(session=db_session)
        with pytest.raises(TrackerError) as exc:
            await agent.track_application(job_id=str(uuid.uuid4()))
        assert "not initialized" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_record_event(self, db_session, seed_job):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        data = await agent.track_application(job_id=str(seed_job.id))
        event = StatusChangeEvent(
            application_id=data.application_id,
            from_status="draft",
            to_status="ready",
            changed_by="user",
        )
        entry = await agent.record_event(data.application_id, event)
        assert entry.to_status == "ready"

    @pytest.mark.asyncio
    async def test_record_apply_result(self, db_session, seed_job):
        agent = TrackerAgent(session=db_session)
        await agent.initialize()
        data = await agent.track_application(job_id=str(seed_job.id), status="applied")

        result = ApplyAgentIntegration(
            success=True,
            final_state="verified",
            confirmation_code="CONF-123",
            screenshot_path="/screenshots/1.png",
            errors=[],
            duration_seconds=30.0,
            state_history=[],
        )
        updated = await agent.record_apply_result(
            data.application_id,
            result,
        )
        assert updated.confirmation_code == "CONF-123"


# ---------------------------------------------------------------------------
# Data Model Tests
# ---------------------------------------------------------------------------


class TestStatusChangeEvent:
    def test_to_dict(self):
        event = StatusChangeEvent(
            application_id=str(uuid.uuid4()),
            from_status="draft",
            to_status="ready",
            changed_by="user",
            reason="Manual trigger",
        )
        d = event.to_dict()
        assert d["from_status"] == "draft"
        assert d["to_status"] == "ready"
        assert d["reason"] == "Manual trigger"

    def test_default_changed_by(self):
        event = StatusChangeEvent(
            application_id=str(uuid.uuid4()),
            from_status=None,
            to_status="draft",
        )
        assert event.changed_by == "system"


class TestApplicationStatusData:
    def test_to_dict(self):
        data = ApplicationStatusData(
            application_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            status="applied",
            company_name="TestCorp",
        )
        d = data.to_dict()
        assert d["status"] == "applied"
        assert d["company_name"] == "TestCorp"


class TestHistoryEntry:
    def test_to_dict(self):
        entry = HistoryEntry(
            entry_id=str(uuid.uuid4()),
            application_id=str(uuid.uuid4()),
            from_status="draft",
            to_status="ready",
            changed_by="user",
            reason="test",
            metadata={"key": "val"},
            created_at=datetime.now(timezone.utc),
        )
        d = entry.to_dict()
        assert d["to_status"] == "ready"
        assert d["metadata"] == {"key": "val"}


class TestApplyAgentIntegration:
    def test_defaults(self):
        result = ApplyAgentIntegration(
            success=True,
            final_state="verified",
            confirmation_code=None,
            screenshot_path=None,
            errors=[],
            duration_seconds=0.0,
            state_history=[],
        )
        assert result.success is True
        assert result.final_state == "verified"


# ---------------------------------------------------------------------------
# Exception Tests
# ---------------------------------------------------------------------------


class TestTrackerExceptions:
    def test_tracker_error_base(self):
        err = TrackerError("base", step="test")
        assert str(err) == "base"
        assert err.step == "test"

    def test_application_not_found(self):
        err = ApplicationNotFoundError(application_id="abc-123")
        assert "abc-123" in str(err)

    def test_duplicate_application_error(self):
        err = DuplicateApplicationError(job_id="job-1", existing_id="app-1")
        assert "job-1" in str(err)
        assert "app-1" in str(err)

    def test_invalid_status_transition_error(self):
        err = InvalidStatusTransitionError(from_status="draft", to_status="accepted")
        assert "draft" in str(err)
        assert "accepted" in str(err)

    def test_invalid_status_error(self):
        err = InvalidStatusError(status="bogus")
        assert "bogus" in str(err)

    def test_hierarchy(self):
        assert issubclass(ApplicationNotFoundError, TrackerError)
        assert issubclass(DuplicateApplicationError, TrackerError)
        assert issubclass(InvalidStatusTransitionError, TrackerError)
        assert issubclass(InvalidStatusError, TrackerError)
        assert issubclass(CleanupError, TrackerError)
        assert issubclass(MetricsComputationError, TrackerError)
        assert issubclass(TimelineBuildError, TrackerError)
