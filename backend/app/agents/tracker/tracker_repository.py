from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, func, select, update

from app.agents.tracker.exceptions import (
    ApplicationNotFoundError,
    DuplicateApplicationError,
    TrackerError,
)
from app.agents.tracker.status_manager import StatusManager
from app.agents.tracker.tracker_models import ApplicationStatusData
from app.collectors.logging import CollectorLoggerProtocol


class ApplicationRepository:
    """SQLAlchemy repository for Application and ApplicationStatusHistory.

    Follows the same pattern as JobRepository/JobQueryRepository:
    - Takes an AsyncSession in the constructor.
    - All methods are async.
    - Returns ORM model instances.
    - Uses SQLAlchemy 2.0 select() style.

    Usage::

        repo = ApplicationRepository(session=db_session, logger=logger)
        app = await repo.create_application(job_id="...")
        app = await repo.get_application(app_id)
        apps = await repo.list_applications()
    """

    def __init__(
        self,
        session: Any,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._session = session
        self._logger = logger

    def _log(self, message: str, level: str = "info") -> None:
        if self._logger:
            getattr(self._logger, level, print)(message)

    @staticmethod
    def _uuid(value: str | uuid.UUID) -> uuid.UUID:
        """Convert a string to a UUID, passing through UUID objects unchanged."""
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)

    async def create_application(
        self,
        job_id: str,
        status: str = "draft",
        apply_url: Optional[str] = None,
        resume_version: Optional[str] = None,
        cover_letter_version: Optional[str] = None,
        notes: Optional[str] = None,
        browser_session_id: Optional[str] = None,
    ) -> Any:
        """Create a new application record.

        Args:
            job_id: UUID of the job to track.
            status: Initial status (default: "draft").
            apply_url: Direct application URL.
            resume_version: Resume version identifier.
            cover_letter_version: Cover letter version identifier.
            notes: Optional notes.
            browser_session_id: Browser session identifier.

        Returns:
            The created Application ORM instance.

        Raises:
            DuplicateApplicationError: If a tracked application already
                exists for this job (when enabled).
        """
        from app.db.models.application import Application

        existing = await self._find_by_job(job_id)
        if existing is not None:
            raise DuplicateApplicationError(
                job_id=job_id,
                existing_id=str(existing.id),
            )

        StatusManager.validate_status(status)

        app = Application(
            id=uuid.uuid4(),
            job_id=self._uuid(job_id),
            status=status,
            apply_url=apply_url,
            resume_version=resume_version,
            cover_letter_version=cover_letter_version,
            notes=notes,
            browser_session_id=browser_session_id,
            applied_date=datetime.now(timezone.utc)
            if status == "applied"
            else None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._session.add(app)
        await self._session.flush()

        self._log(f"Created application {app.id} for job {job_id}")
        return app

    async def get_application(self, application_id: str) -> Any:
        """Get a single application by ID with related job data.

        Returns:
            The Application ORM instance.

        Raises:
            ApplicationNotFoundError: If not found.
        """
        from app.db.models.application import Application

        stmt = (
            select(Application)
            .where(Application.id == self._uuid(application_id))
        )
        result = await self._session.execute(stmt)
        app = result.scalar_one_or_none()
        if app is None:
            raise ApplicationNotFoundError(application_id=application_id)
        return app

    async def get_application_with_relations(
        self,
        application_id: str,
    ) -> Any:
        """Get an application with job, company, and history eagerly loaded."""
        from sqlalchemy.orm import selectinload

        from app.db.models.application import Application

        stmt = (
            select(Application)
            .options(
                selectinload(Application.job),
                selectinload(Application.status_history),
            )
            .where(Application.id == self._uuid(application_id))
        )
        result = await self._session.execute(stmt)
        app = result.scalar_one_or_none()
        if app is None:
            raise ApplicationNotFoundError(application_id=application_id)
        return app

    async def find_by_job(self, job_id: str) -> Optional[Any]:
        """Find an application by job ID.

        Returns None if no application exists for this job.
        """
        return await self._find_by_job(job_id)

    async def _find_by_job(self, job_id: str) -> Optional[Any]:
        """Internal: find application by job ID without raising."""
        from app.db.models.application import Application

        stmt = (
            select(Application)
            .where(Application.job_id == self._uuid(job_id))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_applications(
        self,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Any]:
        """List applications with optional filters.

        Args:
            status: Filter by status value.
            is_active: Filter by active/inactive.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            List of Application ORM instances.
        """
        from app.db.models.application import Application

        stmt = select(Application).order_by(
            Application.updated_at.desc(),
        )

        if status:
            stmt = stmt.where(Application.status == status)
        if is_active is not None:
            stmt = stmt.where(Application.is_active == is_active)

        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_applications_with_relations(
        self,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Any]:
        """List applications with eagerly loaded job + company."""
        from sqlalchemy.orm import selectinload

        from app.db.models.application import Application

        stmt = (
            select(Application)
            .options(
                selectinload(Application.job),
                selectinload(Application.status_history),
            )
            .order_by(Application.updated_at.desc())
        )

        if status:
            stmt = stmt.where(Application.status == status)
        if is_active is not None:
            stmt = stmt.where(Application.is_active == is_active)

        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        application_id: str,
        new_status: str,
        changed_by: str = "system",
        reason: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Update application status and record history.

        Validates the transition before applying.

        Args:
            application_id: The application UUID.
            new_status: Target status.
            changed_by: Who/what changed the status.
            reason: Optional reason for the change.
            metadata: Optional metadata dict.

        Returns:
            The updated Application ORM instance.

        Raises:
            ApplicationNotFoundError: If application not found.
            InvalidStatusTransitionError: If transition is invalid.
        """
        from app.db.models.application import Application
        from app.db.models.application_status_history import (
            ApplicationStatusHistory,
        )

        app = await self.get_application(application_id)
        old_status = app.status

        StatusManager.validate_transition(old_status, new_status)

        app.status = new_status
        app.updated_at = datetime.now(timezone.utc)

        if new_status == "applied" and app.applied_date is None:
            app.applied_date = datetime.now(timezone.utc)

        history = ApplicationStatusHistory(
            id=uuid.uuid4(),
            application_id=self._uuid(application_id),
            from_status=old_status,
            to_status=new_status,
            changed_by=changed_by,
            reason=reason,
            extra_data=metadata,
        )
        self._session.add(history)
        await self._session.flush()

        self._log(
            f"Application {application_id}: {old_status} -> {new_status}"
            f" ({changed_by})",
        )
        return app

    async def update_application(
        self,
        application_id: str,
        **kwargs: Any,
    ) -> Any:
        """Update arbitrary fields on an application.

        Args:
            application_id: The application UUID.
            **kwargs: Fields to update (e.g., notes, rating, offer_details).

        Returns:
            The updated Application ORM instance.
        """
        from app.db.models.application import Application

        app = await self.get_application(application_id)

        allowed_fields = {
            "notes",
            "rating",
            "offer_details",
            "rejection_reason",
            "interview_dates",
            "confirmation_code",
            "screenshot_path",
            "resume_version",
            "cover_letter_version",
            "apply_url",
            "browser_session_id",
            "apply_agent_result",
            "is_active",
        }

        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(app, key, value)

        app.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return app

    async def count_applications(
        self,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count applications matching filters."""
        from app.db.models.application import Application

        stmt = select(func.count(Application.id))
        conditions: list[Any] = []
        if status:
            conditions.append(Application.status == status)
        if is_active is not None:
            conditions.append(Application.is_active == is_active)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_all_for_metrics(self) -> list[Any]:
        """Get all applications with related job/company/source for metrics."""
        from sqlalchemy.orm import selectinload

        from app.db.models.application import Application

        stmt = (
            select(Application)
            .options(
                selectinload(Application.job),
                selectinload(Application.status_history),
            )
            .where(Application.is_active == True)  # noqa: E712
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_application(self, application_id: str) -> None:
        """Soft-delete an application by setting is_active to False."""
        from app.db.models.application import Application

        stmt = (
            update(Application)
            .where(Application.id == self._uuid(application_id))
            .values(
                is_active=False,
                updated_at=datetime.now(timezone.utc),
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise ApplicationNotFoundError(application_id=application_id)

    async def hard_delete_application(self, application_id: str) -> None:
        """Permanently remove an application and its history."""
        from app.db.models.application import Application

        app = await self.get_application(application_id)
        await self._session.delete(app)
        await self._session.flush()

    async def get_status_data(self, application_id: str) -> ApplicationStatusData:
        """Get a ApplicationStatusData DTO for an application."""
        from sqlalchemy.orm import selectinload

        from app.db.models.application import Application

        stmt = (
            select(Application)
            .options(selectinload(Application.job))
            .where(Application.id == self._uuid(application_id))
        )
        result = await self._session.execute(stmt)
        app = result.scalar_one_or_none()
        if app is None:
            raise ApplicationNotFoundError(application_id=application_id)

        company_name = ""
        job_title = ""
        if app.job:
            job_title = app.job.title or ""
            if app.job.company:
                company_name = app.job.company.name or ""

        return ApplicationStatusData(
            application_id=str(app.id),
            job_id=str(app.job_id),
            job_title=job_title,
            company_name=company_name,
            status=app.status,
            resume_version=app.resume_version,
            cover_letter_version=app.cover_letter_version,
            apply_url=app.apply_url,
            confirmation_code=app.confirmation_code,
            screenshot_path=app.screenshot_path,
            browser_session_id=app.browser_session_id,
            notes=app.notes,
            rating=app.rating,
            offer_details=app.offer_details,
            rejection_reason=app.rejection_reason,
            interview_dates=app.interview_dates,
            applied_date=app.applied_date,
            is_active=app.is_active,
            created_at=app.created_at,
            updated_at=app.updated_at,
        )
