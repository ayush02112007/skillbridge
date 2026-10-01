"""Digital portfolio, generated resumes and gamification badges."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
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
from app.models.enums import BadgeCode, Visibility


class Portfolio(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "portfolios"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    headline: Mapped[str] = mapped_column(String(200), default="")
    about: Mapped[str] = mapped_column(Text, default="")
    theme: Mapped[str] = mapped_column(String(30), default="slate", nullable=False)
    visibility: Mapped[Visibility] = mapped_column(
        SAEnum(Visibility, native_enum=False, length=24),
        default=Visibility.INSTITUTION_ONLY, nullable=False, index=True,
    )
    # Which sections to render, ordered: ["skills","projects","experience",...]
    sections: Mapped[list[Any]] = mapped_column(default=list)
    featured_project_ids: Mapped[list[Any]] = mapped_column(default=list)
    contact_email_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Resume(UUIDMixin, TimestampMixin, Base):
    """A structured resume the student composes in the builder."""

    __tablename__ = "resumes"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(160), default="My Resume", nullable=False)
    template: Mapped[str] = mapped_column(String(30), default="modern", nullable=False)
    # Full structured content snapshot - only data the student entered.
    content: Mapped[dict[str, Any]] = mapped_column(default=dict)
    target_job_role_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("job_roles.id", ondelete="SET NULL")
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generated_document_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("documents.id", ondelete="SET NULL")
    )
    last_exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ResumeAnalysis(UUIDMixin, TimestampMixin, Base):
    """Output of analysing an uploaded resume against a target role."""

    __tablename__ = "resume_analyses"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_role_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("job_roles.id", ondelete="SET NULL")
    )
    extracted_skills: Mapped[list[Any]] = mapped_column(default=list)
    extracted_education: Mapped[list[Any]] = mapped_column(default=list)
    extracted_experience: Mapped[list[Any]] = mapped_column(default=list)
    extracted_projects: Mapped[list[Any]] = mapped_column(default=list)
    extracted_certifications: Mapped[list[Any]] = mapped_column(default=list)
    matched_skills: Mapped[list[Any]] = mapped_column(default=list)
    missing_skills: Mapped[list[Any]] = mapped_column(default=list)
    suggestions: Mapped[list[Any]] = mapped_column(default=list)
    ats_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    analyzed_by: Mapped[str] = mapped_column(String(32), default="deterministic", nullable=False)


class Badge(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "badges"

    code: Mapped[BadgeCode] = mapped_column(
        SAEnum(BadgeCode, native_enum=False, length=40), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(400), default="")
    icon: Mapped[str] = mapped_column(String(60), default="award")
    criteria: Mapped[str] = mapped_column(String(400), default="")
    tier: Mapped[str] = mapped_column(String(20), default="BRONZE")


class StudentBadge(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "student_badges"
    __table_args__ = (
        UniqueConstraint("student_id", "badge_id", name="student_badge_unique"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    badge_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("badges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(default=dict)

    badge: Mapped[Badge] = relationship(lazy="selectin")
