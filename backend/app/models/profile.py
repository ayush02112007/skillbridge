"""Role-specific profiles: students, academicians, recruiters."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

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
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import Degree, Visibility, WorkMode

if TYPE_CHECKING:
    from app.models.skill import StudentSkill
    from app.models.user import User


class StudentProfile(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint("cgpa is null or (cgpa >= 0 and cgpa <= 10)", name="cgpa_range"),
        CheckConstraint("current_year is null or (current_year between 1 and 6)", name="year_range"),
        CheckConstraint(
            "profile_completion between 0 and 100", name="profile_completion_range"
        ),
        Index("ix_student_profiles_institution_dept", "institution_id", "department_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("institutions.id", ondelete="SET NULL"), index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("departments.id", ondelete="SET NULL")
    )

    # ------------------------------------------------------------ personal --
    headline: Mapped[str | None] = mapped_column(String(160))
    bio: Mapped[str] = mapped_column(Text, default="")
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    # Optional and never used for ranking - see app/ai/matching.py.
    gender: Mapped[str | None] = mapped_column(String(32))
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), default="India")

    # ----------------------------------------------------------- academics --
    enrollment_number: Mapped[str | None] = mapped_column(String(60), index=True)
    degree: Mapped[Degree] = mapped_column(
        SAEnum(Degree, native_enum=False, length=24), default=Degree.BACHELORS, nullable=False
    )
    program_name: Mapped[str | None] = mapped_column(String(140))
    current_year: Mapped[int | None] = mapped_column(Integer)
    current_semester: Mapped[int | None] = mapped_column(Integer)
    cgpa: Mapped[float | None] = mapped_column(Float)
    graduation_year: Mapped[int | None] = mapped_column(Integer, index=True)
    backlogs: Mapped[int] = mapped_column(Integer, default=0)

    # ----------------------------------------------------------- interests --
    career_interests: Mapped[list[Any]] = mapped_column(default=list)
    preferred_roles: Mapped[list[Any]] = mapped_column(default=list)
    preferred_industries: Mapped[list[Any]] = mapped_column(default=list)
    preferred_locations: Mapped[list[Any]] = mapped_column(default=list)
    preferred_work_mode: Mapped[WorkMode | None] = mapped_column(
        SAEnum(WorkMode, native_enum=False, length=16)
    )
    open_to_relocate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expected_stipend_min: Mapped[int | None] = mapped_column(Integer)
    expected_salary_min: Mapped[int | None] = mapped_column(Integer)
    target_job_role_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("job_roles.id", ondelete="SET NULL"), index=True
    )

    # ------------------------------------------------------------- outputs --
    portfolio_slug: Mapped[str | None] = mapped_column(String(120), unique=True, index=True)
    portfolio_visibility: Mapped[Visibility] = mapped_column(
        SAEnum(Visibility, native_enum=False, length=24),
        default=Visibility.INSTITUTION_ONLY, nullable=False,
    )
    profile_completion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skill_readiness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    readiness_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_open_to_work: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_placed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    placed_company_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("companies.id", ondelete="SET NULL")
    )
    github_url: Mapped[str | None] = mapped_column(String(255))
    linkedin_url: Mapped[str | None] = mapped_column(String(255))
    portfolio_url: Mapped[str | None] = mapped_column(String(255))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="student_profile", lazy="selectin")
    skills: Mapped[list[StudentSkill]] = relationship(
        back_populates="student", cascade="all, delete-orphan", lazy="noload"
    )
    education: Mapped[list[EducationRecord]] = relationship(
        back_populates="student", cascade="all, delete-orphan",
        order_by="EducationRecord.end_year.desc()", lazy="noload",
    )
    experiences: Mapped[list[ExperienceRecord]] = relationship(
        back_populates="student", cascade="all, delete-orphan",
        order_by="ExperienceRecord.start_date.desc()", lazy="noload",
    )
    achievements: Mapped[list[Achievement]] = relationship(
        back_populates="student", cascade="all, delete-orphan", lazy="noload"
    )


class AcademicianProfile(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "academician_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("institutions.id", ondelete="SET NULL"), index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("departments.id", ondelete="SET NULL")
    )

    designation: Mapped[str | None] = mapped_column(String(120))
    employee_code: Mapped[str | None] = mapped_column(String(60))
    highest_qualification: Mapped[str | None] = mapped_column(String(120))
    specialization: Mapped[str | None] = mapped_column(String(200))
    teaching_experience_years: Mapped[int] = mapped_column(Integer, default=0)
    industry_experience_years: Mapped[int] = mapped_column(Integer, default=0)
    research_areas: Mapped[list[Any]] = mapped_column(default=list)
    expertise_areas: Mapped[list[Any]] = mapped_column(default=list)
    publications_count: Mapped[int] = mapped_column(Integer, default=0)
    patents_count: Mapped[int] = mapped_column(Integer, default=0)
    orcid_id: Mapped[str | None] = mapped_column(String(40))
    google_scholar_url: Mapped[str | None] = mapped_column(String(255))
    bio: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str | None] = mapped_column(String(100))
    is_available_for_mentorship: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_available_for_consultancy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    profile_completion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="academician_profile", lazy="selectin")


class RecruiterProfile(UUIDMixin, TimestampMixin, Base):
    """Extra attributes for company-side users (recruiters and company admins)."""

    __tablename__ = "recruiter_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    designation: Mapped[str | None] = mapped_column(String(120))
    hiring_domains: Mapped[list[Any]] = mapped_column(default=list)
    linkedin_url: Mapped[str | None] = mapped_column(String(255))
    is_primary_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class EducationRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "education_records"
    __table_args__ = (
        CheckConstraint("end_year is null or end_year >= start_year", name="education_year_order"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[Degree] = mapped_column(
        SAEnum(Degree, native_enum=False, length=24), nullable=False
    )
    institution_name: Mapped[str] = mapped_column(String(200), nullable=False)
    board_or_university: Mapped[str | None] = mapped_column(String(200))
    program: Mapped[str | None] = mapped_column(String(160))
    specialization: Mapped[str | None] = mapped_column(String(160))
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[int | None] = mapped_column(Integer)
    score_value: Mapped[float | None] = mapped_column(Float)
    score_type: Mapped[str] = mapped_column(String(20), default="PERCENTAGE")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student: Mapped[StudentProfile] = relationship(back_populates="education", lazy="noload")


class ExperienceRecord(UUIDMixin, TimestampMixin, Base):
    """Internships, jobs, research and volunteering held by a student."""

    __tablename__ = "experience_records"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(40), default="INTERNSHIP", index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    organization: Mapped[str] = mapped_column(String(180), nullable=False)
    location: Mapped[str | None] = mapped_column(String(120))
    work_mode: Mapped[WorkMode | None] = mapped_column(SAEnum(WorkMode, native_enum=False, length=16))
    description: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    skill_tags: Mapped[list[Any]] = mapped_column(default=list)
    # Set when the experience came from a completed SkillBridge application.
    source_application_id: Mapped[uuid.UUID | None] = mapped_column(GUID, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by_company_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("companies.id", ondelete="SET NULL")
    )

    student: Mapped[StudentProfile] = relationship(back_populates="experiences", lazy="noload")


class StudentProject(UUIDMixin, TimestampMixin, Base):
    """A project a student built (distinct from an industry live project)."""

    __tablename__ = "student_projects"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    role: Mapped[str | None] = mapped_column(String(120))
    team_size: Mapped[int] = mapped_column(Integer, default=1)
    skill_tags: Mapped[list[Any]] = mapped_column(default=list)
    repository_url: Mapped[str | None] = mapped_column(String(255))
    demo_url: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    highlights: Mapped[list[Any]] = mapped_column(default=list)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Achievement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "achievements"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(40), default="COMPETITION", index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    issuer: Mapped[str | None] = mapped_column(String(180))
    achieved_on: Mapped[date | None] = mapped_column(Date)
    position: Mapped[str | None] = mapped_column(String(60))
    url: Mapped[str | None] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student: Mapped[StudentProfile] = relationship(back_populates="achievements", lazy="noload")
