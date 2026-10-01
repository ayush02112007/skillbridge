"""Learning programmes, modules, enrolments and certifications."""
from __future__ import annotations

import uuid
from datetime import date, datetime
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
    Difficulty,
    EnrollmentStatus,
    ProgramType,
    VerificationStatus,
    WorkMode,
)
from app.models.organization import Company
from app.models.skill import Skill


class LearningProgram(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "learning_programs"
    __table_args__ = (
        Index("ix_learning_programs_type_published", "program_type", "is_published"),
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    summary: Mapped[str] = mapped_column(String(400), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    program_type: Mapped[ProgramType] = mapped_column(
        SAEnum(ProgramType, native_enum=False, length=28),
        default=ProgramType.COURSE, nullable=False, index=True,
    )
    provider_company_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    provider_name: Mapped[str | None] = mapped_column(String(180))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        SAEnum(Difficulty, native_enum=False, length=12), default=Difficulty.MEDIUM, nullable=False
    )
    duration_hours: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    mode: Mapped[WorkMode] = mapped_column(
        SAEnum(WorkMode, native_enum=False, length=16), default=WorkMode.REMOTE, nullable=False
    )
    price_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    is_free: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    external_url: Mapped[str | None] = mapped_column(String(500))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    seats: Mapped[int | None] = mapped_column(Integer)
    grants_certificate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    outcomes: Mapped[list[Any]] = mapped_column(default=list)
    prerequisites: Mapped[list[Any]] = mapped_column(default=list)
    rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    enrollment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    search_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    company: Mapped[Company | None] = relationship(lazy="selectin")
    modules: Mapped[list[CourseModule]] = relationship(
        back_populates="program", cascade="all, delete-orphan",
        order_by="CourseModule.display_order", lazy="selectin",
    )
    skills: Mapped[list[ProgramSkill]] = relationship(
        back_populates="program", cascade="all, delete-orphan", lazy="selectin"
    )


class ProgramSkill(UUIDMixin, TimestampMixin, Base):
    """Which skill a programme teaches, and how far it takes you."""

    __tablename__ = "program_skills"
    __table_args__ = (
        UniqueConstraint("program_id", "skill_id", name="program_skill_unique"),
    )

    program_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("learning_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Level a learner is expected to reach on completion.
    target_level: Mapped[str] = mapped_column(String(16), default="INTERMEDIATE", nullable=False)
    coverage_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    program: Mapped[LearningProgram] = relationship(back_populates="skills", lazy="noload")
    skill: Mapped[Skill] = relationship(lazy="selectin")


class CourseModule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "course_modules"
    __table_args__ = (
        Index("ix_course_modules_program_order", "program_id", "display_order"),
    )

    program_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("learning_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    content_type: Mapped[str] = mapped_column(String(20), default="VIDEO")
    content_url: Mapped[str | None] = mapped_column(String(500))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    program: Mapped[LearningProgram] = relationship(back_populates="modules", lazy="noload")


class Enrollment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("program_id", "student_id", name="enrollment_unique"),
        CheckConstraint("progress_percentage between 0 and 100", name="progress_range"),
    )

    program_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("learning_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[EnrollmentStatus] = mapped_column(
        SAEnum(EnrollmentStatus, native_enum=False, length=20),
        default=EnrollmentStatus.ENROLLED, nullable=False, index=True,
    )
    progress_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    final_score: Mapped[float | None] = mapped_column(Float)
    # Set when this enrolment was created from a recommended learning path.
    recommended_for_role_id: Mapped[uuid.UUID | None] = mapped_column(GUID)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    program: Mapped[LearningProgram] = relationship(lazy="selectin")
    module_progress: Mapped[list[ModuleProgress]] = relationship(
        back_populates="enrollment", cascade="all, delete-orphan", lazy="selectin"
    )


class ModuleProgress(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "module_progress"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "module_id", name="module_progress_unique"),
    )

    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("course_modules.id", ondelete="CASCADE"), nullable=False
    )
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_spent_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    enrollment: Mapped[Enrollment] = relationship(back_populates="module_progress", lazy="noload")


class Certification(UUIDMixin, TimestampMixin, Base):
    """A certification that exists in the world (catalogue entry)."""

    __tablename__ = "certifications"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    issuer: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("learning_programs.id", ondelete="SET NULL")
    )
    validity_months: Mapped[int | None] = mapped_column(Integer)
    skill_ids: Mapped[list[Any]] = mapped_column(default=list)
    external_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class StudentCertification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "student_certifications"
    __table_args__ = (
        Index("ix_student_certifications_student", "student_id", "verification_status"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    certification_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("certifications.id", ondelete="SET NULL"), index=True
    )
    enrollment_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("enrollments.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer: Mapped[str] = mapped_column(String(180), nullable=False)
    credential_id: Mapped[str | None] = mapped_column(String(160))
    credential_url: Mapped[str | None] = mapped_column(String(500))
    issued_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("documents.id", ondelete="SET NULL")
    )
    skill_ids: Mapped[list[Any]] = mapped_column(default=list)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, native_enum=False, length=20),
        default=VerificationStatus.UNVERIFIED, nullable=False,
    )
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class LearningPath(UUIDMixin, TimestampMixin, Base):
    """A generated, ordered plan that closes a student's gap for a target role."""

    __tablename__ = "learning_paths"
    __table_args__ = (
        UniqueConstraint("student_id", "job_role_id", name="learning_path_unique"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_role_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("job_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    estimated_weeks: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    # [{order, skill_id, skill_name, target_level, why, program_ids, estimated_hours}]
    steps: Mapped[list[Any]] = mapped_column(default=list)
    generated_by: Mapped[str] = mapped_column(String(32), default="deterministic", nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
