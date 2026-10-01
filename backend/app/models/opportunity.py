"""Opportunities: internships, jobs, live industry projects, faculty programmes.

A joined-table inheritance hierarchy is used so every opportunity kind shares
one set of skill requirements, one application pipeline and one search index,
while keeping its own specific columns in its own table.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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

from app.core.database import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import (
    EmploymentType,
    FacultyOpportunityKind,
    OpportunityStatus,
    OpportunityType,
    ProficiencyLevel,
    SkillImportance,
    WorkMode,
)
from app.models.organization import Company
from app.models.skill import JobRole, Skill


class Opportunity(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint("positions >= 1", name="positions_positive"),
        CheckConstraint("views_count >= 0", name="views_non_negative"),
        Index("ix_opportunities_type_status", "opportunity_type", "status"),
        Index("ix_opportunities_company_status", "company_id", "status"),
        Index("ix_opportunities_deadline", "application_deadline"),
    )

    opportunity_type: Mapped[OpportunityType] = mapped_column(
        SAEnum(OpportunityType, native_enum=False, length=28), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    responsibilities: Mapped[list[Any]] = mapped_column(default=list)
    eligibility_text: Mapped[str] = mapped_column(Text, default="")

    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    posted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    job_role_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("job_roles.id", ondelete="SET NULL"), index=True
    )

    status: Mapped[OpportunityStatus] = mapped_column(
        SAEnum(OpportunityStatus, native_enum=False, length=20),
        default=OpportunityStatus.DRAFT, nullable=False, index=True,
    )
    work_mode: Mapped[WorkMode] = mapped_column(
        SAEnum(WorkMode, native_enum=False, length=16), default=WorkMode.ONSITE, nullable=False
    )
    location_city: Mapped[str | None] = mapped_column(String(120), index=True)
    location_country: Mapped[str] = mapped_column(String(100), default="India")
    positions: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Eligibility filters applied server-side when a student applies.
    min_cgpa: Mapped[float | None] = mapped_column(Float)
    max_backlogs: Mapped[int | None] = mapped_column(Integer)
    eligible_degrees: Mapped[list[Any]] = mapped_column(default=list)
    eligible_graduation_years: Mapped[list[Any]] = mapped_column(default=list)
    eligible_departments: Mapped[list[Any]] = mapped_column(default=list)

    application_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    starts_on: Mapped[date | None] = mapped_column(Date)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applications_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Free-text search document, refreshed whenever the record is written.
    search_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Structured output of the job-description analyser, editable before publish.
    extracted_requirements: Mapped[dict[str, Any]] = mapped_column(default=dict)
    perks: Mapped[list[Any]] = mapped_column(default=list)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __mapper_args__ = {
        "polymorphic_on": opportunity_type,
        "polymorphic_identity": None,
        "with_polymorphic": "*",
    }

    company: Mapped[Company] = relationship(lazy="selectin")
    job_role: Mapped[JobRole | None] = relationship(lazy="selectin")
    skills: Mapped[list[OpportunitySkill]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def is_open(self) -> bool:
        if self.status != OpportunityStatus.PUBLISHED:
            return False
        if self.application_deadline is None:
            return True
        deadline = self.application_deadline
        if deadline.tzinfo is None:

            deadline = deadline.replace(tzinfo=UTC)
        return deadline >= datetime.now(deadline.tzinfo)


class OpportunitySkill(UUIDMixin, TimestampMixin, Base):
    """Skill requirement attached to a specific posting."""

    __tablename__ = "opportunity_skills"
    __table_args__ = (
        UniqueConstraint("opportunity_id", "skill_id", name="opportunity_skill_unique"),
        CheckConstraint("weight > 0", name="opportunity_skill_weight_positive"),
    )

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required_level: Mapped[ProficiencyLevel] = mapped_column(
        SAEnum(ProficiencyLevel, native_enum=False, length=16),
        default=ProficiencyLevel.INTERMEDIATE, nullable=False,
    )
    importance: Mapped[SkillImportance] = mapped_column(
        SAEnum(SkillImportance, native_enum=False, length=16),
        default=SkillImportance.REQUIRED, nullable=False, index=True,
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    opportunity: Mapped[Opportunity] = relationship(back_populates="skills", lazy="noload")
    skill: Mapped[Skill] = relationship(lazy="selectin")


class Internship(Opportunity):
    __tablename__ = "internships"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True
    )
    duration_weeks: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    stipend_min: Mapped[int | None] = mapped_column(Integer)
    stipend_max: Mapped[int | None] = mapped_column(Integer)
    stipend_currency: Mapped[str] = mapped_column(String(8), default="INR")
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    learning_outcomes: Mapped[list[Any]] = mapped_column(default=list)
    mentor_name: Mapped[str | None] = mapped_column(String(160))
    is_ppo_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    certificate_provided: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __mapper_args__ = {"polymorphic_identity": OpportunityType.INTERNSHIP}
    __table_args__ = (
        CheckConstraint(
            "stipend_max is null or stipend_min is null or stipend_max >= stipend_min",
            name="stipend_range_order",
        ),
        CheckConstraint("duration_weeks between 1 and 104", name="duration_range"),
    )


class Job(Opportunity):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True
    )
    employment_type: Mapped[EmploymentType] = mapped_column(
        SAEnum(EmploymentType, native_enum=False, length=20),
        default=EmploymentType.FULL_TIME, nullable=False,
    )
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String(8), default="INR")
    salary_period: Mapped[str] = mapped_column(String(16), default="YEAR")
    experience_min_years: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    experience_max_years: Mapped[float | None] = mapped_column(Float)
    notice_period_days: Mapped[int | None] = mapped_column(Integer)
    bond_months: Mapped[int | None] = mapped_column(Integer)
    hiring_process: Mapped[list[Any]] = mapped_column(default=list)

    __mapper_args__ = {"polymorphic_identity": OpportunityType.JOB}
    __table_args__ = (
        CheckConstraint(
            "salary_max is null or salary_min is null or salary_max >= salary_min",
            name="salary_range_order",
        ),
        CheckConstraint("experience_min_years >= 0", name="experience_non_negative"),
    )


class LiveProject(Opportunity):
    """A real-world problem published by industry for student teams."""

    __tablename__ = "live_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True
    )
    problem_statement: Mapped[str] = mapped_column(Text, default="")
    expected_outcome: Mapped[str] = mapped_column(Text, default="")
    team_size_min: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    team_size_max: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    timeline_weeks: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    stipend_amount: Mapped[int | None] = mapped_column(Integer)
    mentor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    allows_team_application: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __mapper_args__ = {"polymorphic_identity": OpportunityType.LIVE_PROJECT}
    __table_args__ = (
        CheckConstraint("team_size_max >= team_size_min", name="team_size_order"),
    )


class FacultyOpportunity(Opportunity):
    """Industry programme aimed at academicians (FDP, consultancy, training...)."""

    __tablename__ = "faculty_opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[FacultyOpportunityKind] = mapped_column(
        SAEnum(FacultyOpportunityKind, native_enum=False, length=32),
        default=FacultyOpportunityKind.FDP, nullable=False, index=True,
    )
    duration_days: Mapped[int | None] = mapped_column(Integer)
    honorarium: Mapped[int | None] = mapped_column(Integer)
    min_teaching_experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    focus_areas: Mapped[list[Any]] = mapped_column(default=list)
    certification_provided: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    seats: Mapped[int | None] = mapped_column(Integer)

    __mapper_args__ = {"polymorphic_identity": OpportunityType.FACULTY_OPPORTUNITY}


class SavedOpportunity(UUIDMixin, TimestampMixin, Base):
    """Bookmark ('favourites' in the spec)."""

    __tablename__ = "saved_opportunities"
    __table_args__ = (
        UniqueConstraint("user_id", "opportunity_id", name="saved_opportunity_unique"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    note: Mapped[str] = mapped_column(String(400), default="")

    opportunity: Mapped[Opportunity] = relationship(lazy="selectin")
