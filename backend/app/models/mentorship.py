"""Mentorship: mentor profiles, requests and sessions."""
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
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base, TimestampMixin, UUIDMixin
from app.models.enums import MentorshipStatus
from app.models.user import User


class MentorProfile(UUIDMixin, TimestampMixin, Base):
    """Any industry professional or academician who offers mentorship."""

    __tablename__ = "mentors"
    __table_args__ = (
        CheckConstraint("capacity_per_month >= 0", name="mentor_capacity_non_negative"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("institutions.id", ondelete="SET NULL"), index=True
    )
    headline: Mapped[str] = mapped_column(String(200), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    designation: Mapped[str | None] = mapped_column(String(140))
    experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), index=True)
    expertise_skill_ids: Mapped[list[Any]] = mapped_column(default=list)
    topics: Mapped[list[Any]] = mapped_column(default=list)
    languages: Mapped[list[Any]] = mapped_column(default=list)
    # [{day: "MON", from: "18:00", to: "20:00"}]
    availability: Mapped[list[Any]] = mapped_column(default=list)
    capacity_per_month: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    session_duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    is_accepting_requests: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sessions_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(lazy="selectin")


class MentorshipRequest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "mentorship_requests"
    __table_args__ = (
        Index("ix_mentorship_requests_mentor_status", "mentor_id", "status"),
    )

    mentor_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("mentors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="")
    goals: Mapped[list[Any]] = mapped_column(default=list)
    status: Mapped[MentorshipStatus] = mapped_column(
        SAEnum(MentorshipStatus, native_enum=False, length=20),
        default=MentorshipStatus.REQUESTED, nullable=False, index=True,
    )
    preferred_slots: Mapped[list[Any]] = mapped_column(default=list)
    response_message: Mapped[str] = mapped_column(Text, default="")
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    match_reason: Mapped[str] = mapped_column(Text, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    mentor: Mapped[MentorProfile] = relationship(lazy="selectin")
    sessions: Mapped[list[MentorshipSession]] = relationship(
        back_populates="request", cascade="all, delete-orphan", lazy="selectin"
    )


class MentorshipSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "mentorship_sessions"

    request_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("mentorship_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    meeting_link: Mapped[str | None] = mapped_column(String(400))
    agenda: Mapped[str] = mapped_column(Text, default="")
    # SCHEDULED | COMPLETED | CANCELLED | NO_SHOW
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED", nullable=False, index=True)
    mentor_notes: Mapped[str] = mapped_column(Text, default="")
    student_notes: Mapped[str] = mapped_column(Text, default="")
    action_items: Mapped[list[Any]] = mapped_column(default=list)
    student_rating: Mapped[int | None] = mapped_column(Integer)
    student_feedback: Mapped[str] = mapped_column(Text, default="")
    mentor_rating: Mapped[int | None] = mapped_column(Integer)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    request: Mapped[MentorshipRequest] = relationship(back_populates="sessions", lazy="noload")
