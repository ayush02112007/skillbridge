"""Applications, their status history and interview scheduling."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base, TimestampMixin, UUIDMixin
from app.models.enums import ApplicationStatus
from app.models.opportunity import Opportunity
from app.models.profile import StudentProfile


class Application(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        # A student may hold only one application per opportunity.
        UniqueConstraint("opportunity_id", "student_id", name="application_unique"),
        # ... and likewise an academician applying to a faculty programme.
        UniqueConstraint(
            "opportunity_id", "academician_id", name="faculty_application_unique"
        ),
        # Exactly one applicant identity must be set.
        CheckConstraint(
            "(student_id is not null and academician_id is null) or "
            "(student_id is null and academician_id is not null)",
            name="one_applicant_identity",
        ),
        CheckConstraint("match_score between 0 and 100", name="match_score_range"),
        Index("ix_applications_status_created", "status", "created_at"),
        Index("ix_applications_student_status", "student_id", "status"),
    )

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Students apply to internships, jobs and live projects; academicians apply
    # to faculty programmes. Exactly one identity is set (see the CHECK above).
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), index=True
    )
    academician_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("academician_profiles.id", ondelete="CASCADE"), index=True
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus, native_enum=False, length=20),
        default=ApplicationStatus.APPLIED, nullable=False, index=True,
    )
    cover_letter: Mapped[str] = mapped_column(Text, default="")
    resume_document_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("documents.id", ondelete="SET NULL")
    )
    answers: Mapped[dict[str, Any]] = mapped_column(default=dict)

    # Explainability snapshot captured at submission time.
    match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    match_breakdown: Mapped[dict[str, Any]] = mapped_column(default=dict)
    matching_skills: Mapped[list[Any]] = mapped_column(default=list)
    missing_skills: Mapped[list[Any]] = mapped_column(default=list)

    recruiter_rating: Mapped[int | None] = mapped_column(Integer)
    recruiter_notes: Mapped[str] = mapped_column(Text, default="")
    rejection_reason: Mapped[str | None] = mapped_column(String(400))
    withdrawn_reason: Mapped[str | None] = mapped_column(String(400))

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_status_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    opportunity: Mapped[Opportunity] = relationship(lazy="selectin")
    student: Mapped[StudentProfile | None] = relationship(lazy="selectin")
    history: Mapped[list[ApplicationStatusHistory]] = relationship(
        back_populates="application", cascade="all, delete-orphan",
        order_by="ApplicationStatusHistory.created_at", lazy="selectin",
    )
    interviews: Mapped[list[Interview]] = relationship(
        back_populates="application", cascade="all, delete-orphan", lazy="selectin"
    )


class ApplicationStatusHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "application_status_history"

    application_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[ApplicationStatus | None] = mapped_column(
        SAEnum(ApplicationStatus, native_enum=False, length=20)
    )
    to_status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus, native_enum=False, length=20), nullable=False
    )
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    note: Mapped[str] = mapped_column(Text, default="")

    application: Mapped[Application] = relationship(back_populates="history", lazy="noload")


class Interview(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "interviews"
    __table_args__ = (
        Index("ix_interviews_scheduled", "scheduled_at", "status"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    round_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    round_name: Mapped[str] = mapped_column(String(120), default="Technical Round")
    mode: Mapped[str] = mapped_column(String(20), default="ONLINE")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    location_or_link: Mapped[str | None] = mapped_column(String(400))
    interviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    interviewer_name: Mapped[str | None] = mapped_column(String(160))
    # SCHEDULED | COMPLETED | CANCELLED | NO_SHOW
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED", nullable=False)
    feedback: Mapped[str] = mapped_column(Text, default="")
    rating: Mapped[int | None] = mapped_column(Integer)
    instructions: Mapped[str] = mapped_column(Text, default="")

    application: Mapped[Application] = relationship(back_populates="interviews", lazy="noload")
