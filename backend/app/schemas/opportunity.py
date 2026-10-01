"""Opportunity schemas: internships, jobs, live projects, faculty programmes."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from app.models.enums import (
    EmploymentType,
    FacultyOpportunityKind,
    OpportunityStatus,
    OpportunityType,
    ProficiencyLevel,
    SkillImportance,
    WorkMode,
)
from app.schemas.common import APIModel
from app.schemas.skill import SkillBrief


class CompanyBrief(APIModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    industry_sector: str = ""
    headquarters_city: str | None = None
    verification_status: str | None = None


class OpportunitySkillIn(APIModel):
    skill_id: uuid.UUID
    required_level: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE
    importance: SkillImportance = SkillImportance.REQUIRED
    weight: float = Field(default=1.0, gt=0, le=5)


class OpportunitySkillOut(APIModel):
    skill_id: uuid.UUID
    skill: SkillBrief | None = None
    required_level: ProficiencyLevel
    importance: SkillImportance
    weight: float


class OpportunityBase(APIModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=20, max_length=20000)
    responsibilities: list[str] = Field(default_factory=list, max_length=20)
    eligibility_text: str = Field(default="", max_length=4000)
    work_mode: WorkMode = WorkMode.ONSITE
    location_city: str | None = Field(default=None, max_length=120)
    location_country: str = "India"
    positions: int = Field(default=1, ge=1, le=10000)
    min_cgpa: float | None = Field(default=None, ge=0, le=10)
    max_backlogs: int | None = Field(default=None, ge=0, le=50)
    eligible_degrees: list[str] = Field(default_factory=list, max_length=10)
    eligible_graduation_years: list[int] = Field(default_factory=list, max_length=10)
    eligible_departments: list[str] = Field(default_factory=list, max_length=30)
    application_deadline: datetime | None = None
    starts_on: date | None = None
    perks: list[str] = Field(default_factory=list, max_length=15)
    job_role_id: uuid.UUID | None = None
    skills: list[OpportunitySkillIn] = Field(default_factory=list, max_length=30)


class InternshipCreate(OpportunityBase):
    duration_weeks: int = Field(default=8, ge=1, le=104)
    stipend_min: int | None = Field(default=None, ge=0)
    stipend_max: int | None = Field(default=None, ge=0)
    stipend_currency: str = Field(default="INR", max_length=8)
    is_paid: bool = True
    learning_outcomes: list[str] = Field(default_factory=list, max_length=15)
    mentor_name: str | None = Field(default=None, max_length=160)
    is_ppo_available: bool = False
    certificate_provided: bool = True

    @model_validator(mode="after")
    def _stipend(self) -> InternshipCreate:
        if self.stipend_min and self.stipend_max and self.stipend_max < self.stipend_min:
            raise ValueError("Maximum stipend cannot be lower than the minimum")
        if self.is_paid and not (self.stipend_min or self.stipend_max):
            raise ValueError("A paid internship must state a stipend")
        return self


class JobCreate(OpportunityBase):
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str = Field(default="INR", max_length=8)
    salary_period: Literal["YEAR", "MONTH", "HOUR"] = "YEAR"
    experience_min_years: float = Field(default=0.0, ge=0, le=50)
    experience_max_years: float | None = Field(default=None, ge=0, le=50)
    notice_period_days: int | None = Field(default=None, ge=0, le=365)
    bond_months: int | None = Field(default=None, ge=0, le=120)
    hiring_process: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _ranges(self) -> JobCreate:
        if self.salary_min and self.salary_max and self.salary_max < self.salary_min:
            raise ValueError("Maximum salary cannot be lower than the minimum")
        if (
            self.experience_max_years is not None
            and self.experience_max_years < self.experience_min_years
        ):
            raise ValueError("Maximum experience cannot be lower than the minimum")
        return self


class LiveProjectCreate(OpportunityBase):
    problem_statement: str = Field(default="", max_length=8000)
    expected_outcome: str = Field(default="", max_length=4000)
    team_size_min: int = Field(default=1, ge=1, le=20)
    team_size_max: int = Field(default=4, ge=1, le=20)
    timeline_weeks: int = Field(default=8, ge=1, le=104)
    stipend_amount: int | None = Field(default=None, ge=0)
    allows_team_application: bool = True

    @model_validator(mode="after")
    def _team(self) -> LiveProjectCreate:
        if self.team_size_max < self.team_size_min:
            raise ValueError("Maximum team size cannot be lower than the minimum")
        return self


class FacultyOpportunityCreate(OpportunityBase):
    kind: FacultyOpportunityKind = FacultyOpportunityKind.FDP
    duration_days: int | None = Field(default=None, ge=1, le=365)
    honorarium: int | None = Field(default=None, ge=0)
    min_teaching_experience_years: int = Field(default=0, ge=0, le=50)
    focus_areas: list[str] = Field(default_factory=list, max_length=15)
    certification_provided: bool = True
    seats: int | None = Field(default=None, ge=1, le=10000)


class OpportunityUpdate(APIModel):
    """Partial update shared by every opportunity type."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=20, max_length=20000)
    responsibilities: list[str] | None = None
    eligibility_text: str | None = None
    work_mode: WorkMode | None = None
    location_city: str | None = None
    positions: int | None = Field(default=None, ge=1)
    min_cgpa: float | None = Field(default=None, ge=0, le=10)
    max_backlogs: int | None = Field(default=None, ge=0)
    eligible_degrees: list[str] | None = None
    eligible_graduation_years: list[int] | None = None
    eligible_departments: list[str] | None = None
    application_deadline: datetime | None = None
    starts_on: date | None = None
    perks: list[str] | None = None
    job_role_id: uuid.UUID | None = None
    skills: list[OpportunitySkillIn] | None = None
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific fields, e.g. {\"stipend_min\": 25000} for an "
                    "internship or {\"salary_max\": 1800000} for a job.",
    )


class StatusChange(APIModel):
    status: OpportunityStatus


class OpportunityListItem(APIModel):
    id: uuid.UUID
    opportunity_type: OpportunityType
    title: str
    slug: str
    company: CompanyBrief | None = None
    status: OpportunityStatus
    work_mode: WorkMode
    location_city: str | None = None
    positions: int = 1
    application_deadline: datetime | None = None
    published_at: datetime | None = None
    applications_count: int = 0
    views_count: int = 0
    job_role_title: str | None = None
    skills: list[OpportunitySkillOut] = []
    is_open: bool = True
    is_demo: bool = False
    # Populated for signed-in students.
    match_score: float | None = None
    matching_skills: list[str] | None = None
    missing_skills: list[str] | None = None
    has_applied: bool = False
    is_saved: bool = False
    # Type-specific summary fields, flattened for list rendering.
    stipend_min: int | None = None
    stipend_max: int | None = None
    duration_weeks: int | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    employment_type: EmploymentType | None = None
    experience_min_years: float | None = None


class MatchExplanation(APIModel):
    match_score: float
    breakdown: dict[str, float]
    contributions: dict[str, float]
    matching_skills: list[str]
    missing_skills: list[str]
    reasons: list[str]
    reason_summary: str
    next_steps: list[str] = []
    is_eligible: bool = True
    ineligibility_reasons: list[str] = []


class OpportunityDetail(OpportunityListItem):
    description: str = ""
    responsibilities: list[Any] = []
    eligibility_text: str = ""
    location_country: str = "India"
    min_cgpa: float | None = None
    max_backlogs: int | None = None
    eligible_degrees: list[Any] = []
    eligible_graduation_years: list[Any] = []
    eligible_departments: list[Any] = []
    starts_on: date | None = None
    perks: list[Any] = []
    extracted_requirements: dict[str, Any] = {}
    created_at: datetime | None = None
    # Type-specific detail
    details: dict[str, Any] = {}
    match: MatchExplanation | None = None


class JobDescriptionAnalysisIn(APIModel):
    description: str = Field(min_length=30, max_length=20000)
    title: str | None = Field(default=None, max_length=200)


class DetectedSkill(APIModel):
    skill_id: uuid.UUID
    skill_name: str
    matched_term: str
    occurrences: int
    suggested_level: ProficiencyLevel
    suggested_importance: SkillImportance


class JobDescriptionAnalysisOut(APIModel):
    skills: list[DetectedSkill] = []
    keywords: list[str] = []
    responsibilities: list[str] = []
    education: str | None = None
    experience_years: float | None = None
    seniority: str | None = None
    suggested_job_role_id: uuid.UUID | None = None
    suggested_job_role_title: str | None = None
    extracted_by: str = "deterministic"
