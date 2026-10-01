"""Execution artefacts for live industry projects: teams, milestones, tasks."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
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
from app.models.enums import MilestoneStatus


class ProjectTeam(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "project_teams"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="project_team_name_unique"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("live_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    lead_student_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="SET NULL")
    )
    # PROPOSED | SELECTED | ACTIVE | COMPLETED | REJECTED
    status: Mapped[str] = mapped_column(String(20), default="PROPOSED", nullable=False, index=True)
    pitch: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float | None] = mapped_column(Float)

    members: Mapped[list[ProjectTeamMember]] = relationship(
        back_populates="team", cascade="all, delete-orphan", lazy="selectin"
    )


class ProjectTeamMember(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "project_team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "student_id", name="project_member_unique"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("project_teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_in_team: Mapped[str] = mapped_column(String(80), default="Member")

    team: Mapped[ProjectTeam] = relationship(back_populates="members", lazy="noload")


class ProjectMilestone(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "project_milestones"
    __table_args__ = (
        Index("ix_project_milestones_project_order", "project_id", "display_order"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("live_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("project_teams.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    due_on: Mapped[date | None] = mapped_column(Date)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[MilestoneStatus] = mapped_column(
        SAEnum(MilestoneStatus, native_enum=False, length=20),
        default=MilestoneStatus.PENDING, nullable=False, index=True,
    )

    tasks: Mapped[list[ProjectTask]] = relationship(
        back_populates="milestone", cascade="all, delete-orphan", lazy="selectin"
    )
    submissions: Mapped[list[ProjectSubmission]] = relationship(
        back_populates="milestone", cascade="all, delete-orphan", lazy="selectin"
    )


class ProjectTask(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "project_tasks"

    milestone_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("project_milestones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    assignee_student_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="SET NULL"), index=True
    )
    # TODO | IN_PROGRESS | REVIEW | DONE
    status: Mapped[str] = mapped_column(String(20), default="TODO", nullable=False, index=True)
    due_on: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    milestone: Mapped[ProjectMilestone] = relationship(back_populates="tasks", lazy="noload")


class ProjectSubmission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "project_submissions"

    milestone_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("project_milestones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("project_teams.id", ondelete="SET NULL"), index=True
    )
    submitted_by_student_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="SET NULL")
    )
    summary: Mapped[str] = mapped_column(Text, default="")
    repository_url: Mapped[str | None] = mapped_column(String(400))
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("documents.id", ondelete="SET NULL")
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    evaluator_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    feedback: Mapped[str] = mapped_column(Text, default="")
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    milestone: Mapped[ProjectMilestone] = relationship(back_populates="submissions", lazy="noload")
