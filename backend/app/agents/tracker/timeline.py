from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select

from app.agents.tracker.exceptions import TimelineBuildError
from app.agents.tracker.tracker_models import ApplicationTimeline, TimelineEntry


class Timeline:
    """Builds a chronological timeline for an application from its history.

    The timeline includes status changes, notes, interview events, and
    offer events — all sorted chronologically.

    Usage::

        timeline = Timeline()
        result = await timeline.build(db_session, application_id)
        for entry in result.entries:
            print(entry.timestamp, entry.title)
    """

    async def build(
        self,
        db_session: Any,
        application: Any,
    ) -> ApplicationTimeline:
        """Build a complete timeline for an application.

        Args:
            db_session: SQLAlchemy async session.
            application: The Application ORM object with loaded relationships.

        Returns:
            An ApplicationTimeline with all entries sorted chronologically.
        """
        try:
            from app.db.models.application_status_history import (
                ApplicationStatusHistory,
            )

            entries: list[TimelineEntry] = []

            created_entry = TimelineEntry(
                event_type="status_change",
                timestamp=application.created_at,
                title="Application Created",
                description=f"Initial status: {application.status}",
            )
            entries.append(created_entry)

            stmt = (
                select(ApplicationStatusHistory)
                .where(
                    ApplicationStatusHistory.application_id == application.id,
                )
                .order_by(ApplicationStatusHistory.created_at.asc())
            )
            result = await db_session.execute(stmt)
            status_history = list(result.scalars().all())

            for hist in status_history:
                from_s = hist.from_status or "none"
                to_s = hist.to_status
                title = f"Status: {from_s} -> {to_s}"
                desc = hist.reason or f"Changed by {hist.changed_by}"

                entry = TimelineEntry(
                    event_type="status_change",
                    timestamp=hist.created_at,
                    title=title,
                    description=desc,
                    metadata=hist.extra_data,
                )
                entries.append(entry)

                if to_s in ("offer", "accepted"):
                    offer_entry = TimelineEntry(
                        event_type="offer",
                        timestamp=hist.created_at,
                        title=f"Offer: {to_s}",
                        description=hist.reason or f"Status changed to {to_s}",
                        metadata=hist.extra_data,
                    )
                    entries.append(offer_entry)

            if application.notes:
                note_entry = TimelineEntry(
                    event_type="note",
                    timestamp=application.updated_at,
                    title="Notes Updated",
                    description=application.notes[:200],
                )
                entries.append(note_entry)

            if application.interview_dates:
                for dt in application.interview_dates:
                    iv_entry = TimelineEntry(
                        event_type="interview",
                        timestamp=application.updated_at,
                        title="Interview Scheduled",
                        description=f"Interview on {dt}",
                        metadata={"date": dt},
                    )
                    entries.append(iv_entry)

            entries.sort(key=lambda e: e.timestamp)

            return ApplicationTimeline(
                application_id=str(application.id),
                entries=entries,
            )

        except Exception as exc:
            raise TimelineBuildError(
                message=f"Failed to build timeline: {exc}",
                original=exc,
            ) from exc
