"""Skill assessment engine models."""
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
from app.models.enums import (
    AssessmentType,
    AttemptStatus,
    Difficulty,
    ProficiencyLevel,
    QuestionType,
)
from app.models.skill import JobRole, Skill


class Assessment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "assessments"

    title: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    assessment_type: Mapped[AssessmentType] = mapped_column(
        SAEnum(AssessmentType, native_enum=False, length=24),
        default=AssessmentType.MCQ, nullable=False, index=True,
    )
    job_role_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("job_roles.id", ondelete="SET NULL"), index=True
    )
    primary_skill_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("skills.id", ondelete="SET NULL"), index=True
    )
    domain: Mapped[str | None] = mapped_column(String(80), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    passing_score: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    cooldown_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL")
    )

    # lazy="raise": an un-eager-loaded access is a bug, and silently
    # returning an empty question list would score every attempt as zero.
    questions: Mapped[list[AssessmentQuestion]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan",
        order_by="AssessmentQuestion.display_order", lazy="raise",
    )
    job_role: Mapped[JobRole | None] = relationship(lazy="selectin")
    primary_skill: Mapped[Skill | None] = relationship(lazy="selectin")

    @property
    def question_count(self) -> int:
        return len(self.questions)


class AssessmentQuestion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "assessment_questions"
    __table_args__ = (
        CheckConstraint("weight > 0", name="question_weight_positive"),
        Index("ix_assessment_questions_assessment_order", "assessment_id", "display_order"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    subskill: Mapped[str | None] = mapped_column(String(120))
    question_type: Mapped[QuestionType] = mapped_column(
        SAEnum(QuestionType, native_enum=False, length=24),
        default=QuestionType.SINGLE_CHOICE, nullable=False,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    code_snippet: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[Difficulty] = mapped_column(
        SAEnum(Difficulty, native_enum=False, length=12),
        default=Difficulty.MEDIUM, nullable=False, index=True,
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="")
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    assessment: Mapped[Assessment] = relationship(back_populates="questions", lazy="noload")
    options: Mapped[list[AssessmentOption]] = relationship(
        back_populates="question", cascade="all, delete-orphan",
        order_by="AssessmentOption.display_order", lazy="selectin",
    )
    skill: Mapped[Skill] = relationship(lazy="selectin")

    @property
    def correct_option_ids(self) -> set[uuid.UUID]:
        return {o.id for o in self.options if o.is_correct}


class AssessmentOption(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "assessment_options"

    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("assessment_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # For LIKERT / self-assessment questions: how much proficiency this answer implies.
    proficiency_value: Mapped[int | None] = mapped_column(Integer)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    question: Mapped[AssessmentQuestion] = relationship(back_populates="options", lazy="noload")


class AssessmentAttempt(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "assessment_attempts"
    __table_args__ = (
        CheckConstraint("percentage between 0 and 100", name="attempt_percentage_range"),
        Index("ix_attempts_student_assessment", "student_id", "assessment_id"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(
        SAEnum(AttemptStatus, native_enum=False, length=20),
        default=AttemptStatus.IN_PROGRESS, nullable=False, index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    raw_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Snapshot of the question order presented, so scoring is reproducible.
    question_order: Mapped[list[Any]] = mapped_column(default=list)
    feedback: Mapped[str] = mapped_column(Text, default="")

    answers: Mapped[list[AssessmentAnswer]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan", lazy="noload"
    )
    skill_scores: Mapped[list[AttemptSkillScore]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan", lazy="selectin"
    )
    assessment: Mapped[Assessment] = relationship(lazy="selectin")


class AssessmentAnswer(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "assessment_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="attempt_question_unique"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("assessment_questions.id", ondelete="CASCADE"), nullable=False
    )
    selected_option_ids: Mapped[list[Any]] = mapped_column(default=list)
    free_text: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    awarded_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_spent_seconds: Mapped[int | None] = mapped_column(Integer)

    attempt: Mapped[AssessmentAttempt] = relationship(back_populates="answers", lazy="noload")
    question: Mapped[AssessmentQuestion] = relationship(lazy="selectin")


class AttemptSkillScore(UUIDMixin, TimestampMixin, Base):
    """Per-skill breakdown of one attempt - the input to the skill profile."""

    __tablename__ = "attempt_skill_scores"
    __table_args__ = (
        UniqueConstraint("attempt_id", "skill_id", name="attempt_skill_unique"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    questions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    level: Mapped[ProficiencyLevel] = mapped_column(
        SAEnum(ProficiencyLevel, native_enum=False, length=16),
        default=ProficiencyLevel.BEGINNER, nullable=False,
    )

    attempt: Mapped[AssessmentAttempt] = relationship(back_populates="skill_scores", lazy="noload")
    skill: Mapped[Skill] = relationship(lazy="selectin")
