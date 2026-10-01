"""Recommendation schemas. Every payload is explainable by construction."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import APIModel


class RecommendationBase(APIModel):
    """Shared explainability contract for every recommendation type."""

    match_score: float
    breakdown: dict[str, float] = {}
    matching_skills: list[Any] = []
    missing_skills: list[Any] = []
    reasons: list[str] = []
    reason_summary: str = ""
    next_steps: list[str] = []
    generated_by: str = "deterministic"


class OpportunityRecommendation(RecommendationBase):
    target_id: uuid.UUID
    target_title: str
    opportunity_type: str
    company_id: uuid.UUID | None = None
    company_name: str = ""
    location_city: str | None = None
    work_mode: str | None = None
    application_deadline: datetime | None = None
    contributions: dict[str, float] = {}


class CareerRoleRecommendation(RecommendationBase):
    target_id: uuid.UUID
    target_title: str
    family: str = ""
    readiness_score: float = 0.0
    demand_index: float = 0.0
    salary_range: list[int | None] = []


class LearningRecommendation(RecommendationBase):
    target_id: uuid.UUID
    target_title: str
    program_type: str
    provider: str = ""
    duration_hours: int = 0
    is_free: bool = True
    difficulty: str = "MEDIUM"


class MentorRecommendation(RecommendationBase):
    target_id: uuid.UUID
    target_title: str
    headline: str = ""
    designation: str | None = None
    industry: str | None = None
    experience_years: int = 0
    rating: float = 0.0


class SkillRecommendation(APIModel):
    skill_id: uuid.UUID
    skill_name: str
    category: str = ""
    demand_score: float = 0.0
    open_postings: int = 0
    gap_priority: int | None = None
    already_held: bool = False
    score: float
    reasons: list[str] = []


class LearningPathStep(APIModel):
    order: int
    skill_id: uuid.UUID | str
    skill_name: str
    current_level: str
    target_level: str
    status: str
    why: str
    estimated_hours: int
    programs: list[dict[str, Any]] = []
    prerequisites: list[str] = []


class LearningPathOut(APIModel):
    job_role_id: uuid.UUID
    job_role_title: str
    title: str
    summary: str
    readiness_score: float = 0.0
    gap_percentage: float = 0.0
    estimated_weeks: int
    total_hours: int
    steps: list[LearningPathStep] = []
    generated_by: str = "deterministic"


class CareerGuidanceOut(APIModel):
    guidance: str
    generated_by: str = "deterministic"
    top_skills: list[str] = []
    target_role: str | None = None
    readiness_score: float | None = None


class InterviewQuestionOut(APIModel):
    question: str
    category: str
    skill: str = ""


class InterviewPrepOut(APIModel):
    role_title: str
    questions: list[InterviewQuestionOut] = []
    focus_skills: list[str] = []
    generated_by: str = "deterministic"


class RecommendationFeedbackIn(APIModel):
    signal: str
    comment: str = ""
