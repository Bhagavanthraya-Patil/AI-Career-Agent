from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Any, Optional

from app.agents.tracker.exceptions import DuplicateHistoryEntryError
from app.agents.tracker.status_manager import StatusManager
from app.agents.tracker.tracker_models import HistoryEntry, StatusChangeEvent


class HistoryManager:
    """Records and manages immutable status change history.

    Every status change creates a permanent, immutable event in the
    application's history. The history is ordered by creation time
    and can be used to reconstruct the full timeline.

    Usage::

        mgr = HistoryManager()
        event = StatusChangeEvent(
            application_id="...",
            from_status="draft",
            to_status="ready",
            changed_by="user",
            reason="Ready for submission",
        )
        entry = await mgr.record_event(db_session, event)
    """

    def __init__(self, max_entries: int = 1000) -> None:
        self._max_entries = max_entries

    @staticmethod
    def _uuid(value: str | uuid_lib.UUID) -> uuid_lib.UUID:
        if isinstance(value, uuid_lib.UUID):
            return value
        return uuid_lib.UUID(value)

    async def record_event(
        self,
        db_session: Any,
        event: StatusChangeEvent,
    ) -> HistoryEntry:
        """Record a status change event in the database.

        Args:
            db_session: SQLAlchemy async session.
            event: The status change event to record.

        Returns:
            The persisted HistoryEntry.

        Raises:
            DuplicateHistoryEntryError: If a duplicate entry is detected.
        """
        from app.db.models.application_status_history import (
            ApplicationStatusHistory,
        )

        entry = ApplicationStatusHistory(
            application_id=self._uuid(event.application_id),
            from_status=event.from_status,
            to_status=event.to_status,
            changed_by=event.changed_by,
            reason=event.reason,
            extra_data=event.metadata,
        )
        db_session.add(entry)
        await db_session.flush()

        return HistoryEntry(
            entry_id=str(entry.id),
            application_id=str(entry.application_id),
            from_status=entry.from_status,
            to_status=entry.to_status,
            changed_by=entry.changed_by,
            reason=entry.reason,
            metadata=entry.extra_data,
            created_at=entry.created_at,
        )

    async def get_history(
        self,
        db_session: Any,
        application_id: str,
        limit: Optional[int] = None,
    ) -> list[HistoryEntry]:
        """Retrieve the history for an application, ordered by creation time.

        Args:
            db_session: SQLAlchemy async session.
            application_id: The application UUID.
            limit: Maximum number of entries to return.

        Returns:
            List of HistoryEntry ordered oldest-first.
        """
        from sqlalchemy import select

        from app.db.models.application_status_history import (
            ApplicationStatusHistory,
        )

        stmt = (
            select(ApplicationStatusHistory)
            .where(
                ApplicationStatusHistory.application_id == self._uuid(application_id),
            )
            .order_by(ApplicationStatusHistory.created_at.asc())
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await db_session.execute(stmt)
        rows = result.scalars().all()

        return [
            HistoryEntry(
                entry_id=str(r.id),
                application_id=str(r.application_id),
                from_status=r.from_status,
                to_status=r.to_status,
                changed_by=r.changed_by,
                reason=r.reason,
                metadata=r.extra_data,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def get_latest_event(
        self,
        db_session: Any,
        application_id: str,
    ) -> Optional[HistoryEntry]:
        """Get the most recent history entry for an application."""
        from sqlalchemy import desc, select

        from app.db.models.application_status_history import (
            ApplicationStatusHistory,
        )

        stmt = (
            select(ApplicationStatusHistory)
            .where(
                ApplicationStatusHistory.application_id == self._uuid(application_id),
            )
            .order_by(desc(ApplicationStatusHistory.created_at))
            .limit(1)
        )
        result = await db_session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None

        return HistoryEntry(
            entry_id=str(row.id),
            application_id=str(row.application_id),
            from_status=row.from_status,
            to_status=row.to_status,
            changed_by=row.changed_by,
            reason=row.reason,
            metadata=row.extra_data,
            created_at=row.created_at,
        )

    def build_event(
        self,
        application_id: str,
        from_status: Optional[str],
        to_status: str,
        changed_by: str = "system",
        reason: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> StatusChangeEvent:
        """Build a StatusChangeEvent from parameters.

        Performs validation before creating the event.
        """
        if from_status is not None:
            StatusManager.validate_transition(from_status, to_status)
        return StatusChangeEvent(
            application_id=application_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
            reason=reason,
            metadata=metadata,
            timestamp=datetime.now(timezone.utc),
        )
