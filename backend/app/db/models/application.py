from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        index=True,
    )
    resume_version: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    cover_letter_version: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    apply_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    confirmation_code: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    screenshot_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    browser_session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    apply_agent_result: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(nullable=True)
    offer_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    interview_dates: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )
    applied_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    job: Mapped["Job"] = relationship(  # noqa: F821
        "Job",
        back_populates="applications",
    )
    status_history: Mapped[list["ApplicationStatusHistory"]] = relationship(  # noqa: F821
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStatusHistory.created_at",
    )

    def __repr__(self) -> str:
        return f"<Application {self.id} job={self.job_id} status={self.status}>"
