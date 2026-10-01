"""Research, consultancy and joint innovation collaborations."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
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
from app.models.enums import CollaborationStatus, ResearchProjectType


class ResearchProject(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "research_projects"
    __table_args__ = (
        Index("ix_research_projects_type_status", "project_type", "status"),
    )

    title: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(260), unique=True, nullable=False, index=True)
    abstract: Mapped[str] = mapped_column(Text, default="")
    project_type: Mapped[ResearchProjectType] = mapped_column(
        SAEnum(ResearchProjectType, native_enum=False, length=32),
        default=ResearchProjectType.RESEARCH, nullable=False, index=True,
    )
    status: Mapped[CollaborationStatus] = mapped_column(
        SAEnum(CollaborationStatus, native_enum=False, length=20),
        default=CollaborationStatus.OPEN, nullable=False, index=True,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("institutions.id", ondelete="SET NULL"), index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    principal_investigator_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("academician_profiles.id", ondelete="SET NULL"), index=True
    )
    research_areas: Mapped[list[Any]] = mapped_column(default=list)
    required_expertise: Mapped[list[Any]] = mapped_column(default=list)
    deliverables: Mapped[list[Any]] = mapped_column(default=list)
    funding_amount: Mapped[int | None] = mapped_column(Integer)
    funding_currency: Mapped[str] = mapped_column(String(8), default="INR")
    duration_months: Mapped[int | None] = mapped_column(Integer)
    starts_on: Mapped[date | None] = mapped_column(Date)
    application_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    positions: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    search_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    applications: Mapped[list[ResearchApplication]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="noload"
    )


class ResearchApplication(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "research_applications"
    __table_args__ = (
        UniqueConstraint("project_id", "academician_id", name="research_application_unique"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academician_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("academician_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    proposal: Mapped[str] = mapped_column(Text, default="")
    relevant_publications: Mapped[list[Any]] = mapped_column(default=list)
    # APPLIED | UNDER_REVIEW | SHORTLISTED | ACCEPTED | REJECTED | WITHDRAWN
    status: Mapped[str] = mapped_column(String(20), default="APPLIED", nullable=False, index=True)
    reviewer_notes: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    project: Mapped[ResearchProject] = relationship(back_populates="applications", lazy="selectin")
