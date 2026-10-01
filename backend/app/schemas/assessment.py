"""Assessment schemas.

Correct answers are never present in the schemas used while an attempt is in
progress - ``QuestionForAttempt`` deliberately omits them, and they only appear
in the post-submission report.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from app.models.enums import (
    AssessmentType,
    AttemptStatus,
    Difficulty,
    ProficiencyLevel,
    QuestionType,
)
from app.schemas.common import APIModel
from app.schemas.skill import SkillBrief


class OptionForAttempt(APIModel):
    """An option as the candidate sees it - no `is_correct`."""

    id: uuid.UUID
    label: str
    display_order: int = 0


class QuestionForAttempt(APIModel):
    id: uuid.UUID
    prompt: str
    code_snippet: str | None = None
    question_type: QuestionType
    difficulty: Difficulty
    skill_id: uuid.UUID
    skill_name: str = ""
    subskill: str | None = None
    weight: float = 1.0
    display_order: int = 0
    options: list[OptionForAttempt] = []


class AssessmentOut(APIModel):
    id: uuid.UUID
    title: str
    slug: str
    description: str = ""
    assessment_type: AssessmentType
    domain: str | None = None
    job_role_id: uuid.UUID | None = None
    primary_skill_id: uuid.UUID | None = None
    duration_minutes: int
    passing_score: float
    max_attempts: int
    cooldown_hours: int
    is_published: bool = True
    question_count: int = 0
    skills_covered: list[SkillBrief] = []


class AssessmentListItem(APIModel):
    id: uuid.UUID
    title: str
    slug: str
    description: str = ""
    assessment_type: AssessmentType
    domain: str | None = None
    duration_minutes: int
    passing_score: float
    question_count: int = 0
    job_role_title: str | None = None
    attempts_used: int = 0
    max_attempts: int = 3
    best_percentage: float | None = None
    can_attempt: bool = True


class AttemptStartOut(APIModel):
    attempt_id: uuid.UUID
    assessment_id: uuid.UUID
    assessment_title: str
    attempt_number: int
    status: AttemptStatus
    started_at: datetime
    expires_at: datetime | None = None
    duration_minutes: int
    total_questions: int
    questions: list[QuestionForAttempt]


class AnswerIn(APIModel):
    question_id: uuid.UUID
    selected_option_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    free_text: str | None = Field(default=None, max_length=4000)
    time_spent_seconds: int | None = Field(default=None, ge=0, le=86400)


class AttemptSubmitIn(APIModel):
    answers: list[AnswerIn] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def _unique_questions(self) -> AttemptSubmitIn:
        seen = {a.question_id for a in self.answers}
        if len(seen) != len(self.answers):
            raise ValueError("Each question may be answered only once")
        return self


class SkillScoreOut(APIModel):
    skill_id: uuid.UUID
    skill_name: str
    score: float
    max_score: float
    percentage: float
    questions_count: int
    correct_count: int
    confidence: float
    level: ProficiencyLevel


class AnswerReviewOut(APIModel):
    question_id: uuid.UUID
    prompt: str
    skill_name: str
    difficulty: str
    is_correct: bool
    awarded_score: float
    max_score: float
    selected_option_ids: list[Any] = []
    correct_option_ids: list[Any] = []
    explanation: str = ""


class AttemptResultOut(APIModel):
    attempt_id: uuid.UUID
    assessment_id: uuid.UUID
    assessment_title: str
    status: str
    attempt_number: int
    raw_score: float
    max_score: float
    percentage: float
    confidence: float
    is_passed: bool
    duration_seconds: int | None = None
    submitted_at: datetime | None = None
    feedback: str = ""
    skill_scores: list[SkillScoreOut] = []
    answers: list[AnswerReviewOut] = []


class AttemptSummaryOut(APIModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    assessment_title: str = ""
    attempt_number: int
    status: AttemptStatus
    percentage: float
    is_passed: bool
    started_at: datetime
    submitted_at: datetime | None = None


# ------------------------------------------------------- authoring --------
class OptionIn(APIModel):
    label: str = Field(min_length=1, max_length=1000)
    is_correct: bool = False
    proficiency_value: int | None = Field(default=None, ge=0, le=4)
    display_order: int = 0


class QuestionIn(APIModel):
    skill_id: uuid.UUID
    prompt: str = Field(min_length=5, max_length=4000)
    code_snippet: str | None = None
    question_type: QuestionType = QuestionType.SINGLE_CHOICE
    difficulty: Difficulty = Difficulty.MEDIUM
    subskill: str | None = Field(default=None, max_length=120)
    weight: float = Field(default=1.0, gt=0, le=10)
    explanation: str = Field(default="", max_length=4000)
    display_order: int = 0
    options: list[OptionIn] = Field(min_length=2, max_length=8)

    @model_validator(mode="after")
    def _validate_options(self) -> QuestionIn:
        correct = [o for o in self.options if o.is_correct]
        if self.question_type == QuestionType.LIKERT:
            if any(o.proficiency_value is None for o in self.options):
                raise ValueError("Likert options must each carry a proficiency_value")
            return self
        if not correct:
            raise ValueError("At least one option must be marked correct")
        if self.question_type in (QuestionType.SINGLE_CHOICE, QuestionType.TRUE_FALSE):
            if len(correct) != 1:
                raise ValueError("Single-answer questions need exactly one correct option")
        elif len(correct) < 2:
            raise ValueError("Multi-select questions need at least two correct options")
        return self


class AssessmentCreate(APIModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=4000)
    assessment_type: AssessmentType = AssessmentType.MCQ
    job_role_id: uuid.UUID | None = None
    primary_skill_id: uuid.UUID | None = None
    domain: str | None = Field(default=None, max_length=80)
    duration_minutes: int = Field(default=20, ge=1, le=300)
    passing_score: float = Field(default=60.0, ge=0, le=100)
    max_attempts: int = Field(default=3, ge=1, le=20)
    cooldown_hours: int = Field(default=24, ge=0, le=720)
    shuffle_questions: bool = True
    is_published: bool = True
    questions: list[QuestionIn] = Field(default_factory=list, max_length=100)


class AssessmentUpdate(APIModel):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = None
    domain: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=300)
    passing_score: float | None = Field(default=None, ge=0, le=100)
    max_attempts: int | None = Field(default=None, ge=1, le=20)
    cooldown_hours: int | None = Field(default=None, ge=0, le=720)
    shuffle_questions: bool | None = None
    is_published: bool | None = None
