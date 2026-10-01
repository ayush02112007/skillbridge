"""Workshops and events."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
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

from app.core.database import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import EventType, RegistrationStatus, WorkMode


class Event(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="event_time_order"),
        CheckConstraint("capacity is null or capacity > 0", name="event_capacity_positive"),
        Index("ix_events_starts_published", "starts_at", "is_published"),
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    event_type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, native_enum=False, length=28),
        default=EventType.WORKSHOP, nullable=False, index=True,
    )
    host_company_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    host_institution_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("institutions.id", ondelete="SET NULL"), index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    speaker_name: Mapped[str | None] = mapped_column(String(160))
    speaker_designation: Mapped[str | None] = mapped_column(String(160))
    mode: Mapped[WorkMode] = mapped_column(
        SAEnum(WorkMode, native_enum=False, length=16), default=WorkMode.REMOTE, nullable=False
    )
    venue: Mapped[str | None] = mapped_column(String(300))
    meeting_link: Mapped[str | None] = mapped_column(String(500))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    capacity: Mapped[int | None] = mapped_column(Integer)
    registered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skill_tags: Mapped[list[Any]] = mapped_column(default=list)
    target_audience: Mapped[list[Any]] = mapped_column(default=list)
    grants_certificate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    banner_url: Mapped[str | None] = mapped_column(String(500))
    search_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    registrations: Mapped[list[EventRegistration]] = relationship(
        back_populates="event", cascade="all, delete-orphan", lazy="noload"
    )

    @property
    def has_capacity(self) -> bool:
        return self.capacity is None or self.registered_count < self.capacity


class EventRegistration(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "event_registrations"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="event_registration_unique"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[RegistrationStatus] = mapped_column(
        SAEnum(RegistrationStatus, native_enum=False, length=20),
        default=RegistrationStatus.REGISTERED, nullable=False, index=True,
    )
    attended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    certificate_issued: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    certificate_code: Mapped[str | None] = mapped_column(String(60), unique=True)
    feedback_rating: Mapped[int | None] = mapped_column(Integer)
    feedback_comment: Mapped[str] = mapped_column(Text, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    event: Mapped[Event] = relationship(back_populates="registrations", lazy="selectin")
