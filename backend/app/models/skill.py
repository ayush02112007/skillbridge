"""Skill taxonomy, job-role requirements, student skill profile and gap analysis."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

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
from app.models.enums import ProficiencyLevel, SkillImportance, SkillSource

if TYPE_CHECKING:
    from app.models.profile import StudentProfile


class SkillCategory(UUIDMixin, TimestampMixin, Base):
    """Top level of the taxonomy (Programming, Backend, Cloud, Soft Skills...).

    Categories are self-nesting so the admin panel can extend the tree without
    a schema change.
    """

    __tablename__ = "skill_categories"

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("skill_categories.id", ondelete="SET NULL"), index=True
    )
    icon: Mapped[str | None] = mapped_column(String(60))
    color: Mapped[str | None] = mapped_column(String(20))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_soft_skill: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped[SkillCategory | None] = relationship(
        remote_side="SkillCategory.id", lazy="noload"
    )
    skills: Mapped[list[Skill]] = relationship(back_populates="category", lazy="noload")


class Skill(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "skills"
    __table_args__ = (
        Index("ix_skills_category_active", "category_id", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("skill_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, default="")
    # Alternate spellings used by the resume / job-description extractors.
    aliases: Mapped[list[Any]] = mapped_column(default=list)
    parent_skill_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("skills.id", ondelete="SET NULL")
    )
    is_soft_skill: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_trending: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Rolling demand signal recomputed from live opportunity postings.
    demand_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    learning_resources: Mapped[list[Any]] = mapped_column(default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped[SkillCategory] = relationship(back_populates="skills", lazy="selectin")

    @property
    def search_terms(self) -> list[str]:
        return [self.name.lower(), self.slug, *[str(a).lower() for a in (self.aliases or [])]]


class JobRole(UUIDMixin, TimestampMixin, Base):
    """A canonical career target (Backend Developer, Data Scientist, ...)."""

    __tablename__ = "job_roles"

    title: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    family: Mapped[str] = mapped_column(String(80), default="Engineering", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    responsibilities: Mapped[list[Any]] = mapped_column(default=list)
    typical_qualifications: Mapped[list[Any]] = mapped_column(default=list)
    aliases: Mapped[list[Any]] = mapped_column(default=list)
    seniority: Mapped[str] = mapped_column(String(30), default="ENTRY")
    avg_salary_min: Mapped[int | None] = mapped_column(Integer)
    avg_salary_max: Mapped[int | None] = mapped_column(Integer)
    demand_index: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    required_skills: Mapped[list[RoleSkill]] = relationship(
        back_populates="job_role", cascade="all, delete-orphan", lazy="selectin"
    )


class RoleSkill(UUIDMixin, TimestampMixin, Base):
    """Industry expectation: which skill, at which level, how important."""

    __tablename__ = "role_skills"
    __table_args__ = (
        UniqueConstraint("job_role_id", "skill_id", name="role_skill_unique"),
        CheckConstraint("weight > 0", name="role_skill_weight_positive"),
    )

    job_role_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("job_roles.id", ondelete="CASCADE"), nullable=False, index=True
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

    job_role: Mapped[JobRole] = relationship(back_populates="required_skills", lazy="noload")
    skill: Mapped[Skill] = relationship(lazy="selectin")


class StudentSkill(UUIDMixin, TimestampMixin, Base):
    """A student's evidenced proficiency in one skill."""

    __tablename__ = "student_skills"
    __table_args__ = (
        UniqueConstraint("student_id", "skill_id", name="student_skill_unique"),
        CheckConstraint("score between 0 and 100", name="student_skill_score_range"),
        CheckConstraint("confidence between 0 and 1", name="student_skill_confidence_range"),
        Index("ix_student_skills_skill_level", "skill_id", "level"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[ProficiencyLevel] = mapped_column(
        SAEnum(ProficiencyLevel, native_enum=False, length=16),
        default=ProficiencyLevel.BEGINNER, nullable=False,
    )
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # 0..1 - how much evidence backs this level (assessment > self-report).
    confidence: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    source: Mapped[SkillSource] = mapped_column(
        SAEnum(SkillSource, native_enum=False, length=24),
        default=SkillSource.SELF_REPORTED, nullable=False, index=True,
    )
    evidence: Mapped[dict[str, Any]] = mapped_column(default=dict)
    years_of_experience: Mapped[float | None] = mapped_column(Float)
    last_assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    endorsement_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student: Mapped[StudentProfile] = relationship(back_populates="skills", lazy="noload")
    skill: Mapped[Skill] = relationship(lazy="selectin")


class SkillGapAnalysis(UUIDMixin, TimestampMixin, Base):
    """A stored snapshot of a student-vs-role comparison."""

    __tablename__ = "skill_gap_analyses"
    __table_args__ = (
        UniqueConstraint("student_id", "job_role_id", name="skill_gap_unique"),
        CheckConstraint("readiness_score between 0 and 100", name="gap_readiness_range"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_role_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("job_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    gap_percentage: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_required: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    items: Mapped[list[SkillGapItem]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", lazy="selectin",
        order_by="SkillGapItem.priority",
    )
    job_role: Mapped[JobRole] = relationship(lazy="selectin")


class SkillGapItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "skill_gap_items"
    __table_args__ = (
        UniqueConstraint("analysis_id", "skill_id", name="skill_gap_item_unique"),
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("skill_gap_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    current_level: Mapped[ProficiencyLevel] = mapped_column(
        SAEnum(ProficiencyLevel, native_enum=False, length=16),
        default=ProficiencyLevel.NONE, nullable=False,
    )
    required_level: Mapped[ProficiencyLevel] = mapped_column(
        SAEnum(ProficiencyLevel, native_enum=False, length=16),
        default=ProficiencyLevel.INTERMEDIATE, nullable=False,
    )
    # MISSING | WEAK | STRONG
    status: Mapped[str] = mapped_column(String(16), default="MISSING", nullable=False, index=True)
    gap_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=99, nullable=False)
    importance: Mapped[SkillImportance] = mapped_column(
        SAEnum(SkillImportance, native_enum=False, length=16),
        default=SkillImportance.REQUIRED, nullable=False,
    )
    recommendation: Mapped[str] = mapped_column(Text, default="")

    analysis: Mapped[SkillGapAnalysis] = relationship(back_populates="items", lazy="noload")
    skill: Mapped[Skill] = relationship(lazy="selectin")


class SkillEndorsement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "skill_endorsements"
    __table_args__ = (
        UniqueConstraint("student_skill_id", "endorsed_by_user_id", name="endorsement_unique"),
    )

    student_skill_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endorsed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    note: Mapped[str] = mapped_column(String(400), default="")
