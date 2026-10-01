"""Student profile, education, experience, project and dashboard schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import EmailStr, Field, model_validator

from app.models.enums import Degree, Visibility, WorkMode
from app.schemas.common import APIModel


class StudentProfileOut(APIModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str = ""
    email: EmailStr | None = None
    phone: str | None = None
    avatar_url: str | None = None
    headline: str | None = None
    bio: str = ""
    date_of_birth: date | None = None
    gender: str | None = None
    city: str | None = None
    state: str | None = None
    country: str = "India"

    institution_id: uuid.UUID | None = None
    institution_name: str | None = None
    department_id: uuid.UUID | None = None
    department_name: str | None = None
    enrollment_number: str | None = None
    degree: Degree = Degree.BACHELORS
    program_name: str | None = None
    current_year: int | None = None
    current_semester: int | None = None
    cgpa: float | None = None
    graduation_year: int | None = None
    backlogs: int = 0

    career_interests: list[Any] = []
    preferred_roles: list[Any] = []
    preferred_industries: list[Any] = []
    preferred_locations: list[Any] = []
    preferred_work_mode: WorkMode | None = None
    open_to_relocate: bool = True
    expected_stipend_min: int | None = None
    expected_salary_min: int | None = None
    target_job_role_id: uuid.UUID | None = None
    target_job_role_title: str | None = None

    portfolio_slug: str | None = None
    portfolio_visibility: Visibility = Visibility.INSTITUTION_ONLY
    profile_completion: int = 0
    skill_readiness_score: float = 0.0
    readiness_computed_at: datetime | None = None
    is_open_to_work: bool = True
    is_placed: bool = False
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    is_demo: bool = False
    created_at: datetime | None = None


class StudentProfileUpdate(APIModel):
    headline: str | None = Field(default=None, max_length=160)
    bio: str | None = Field(default=None, max_length=4000)
    date_of_birth: date | None = None
    gender: str | None = Field(
        default=None, max_length=32,
        description="Optional. Collected only where an institution requires it for "
                    "statutory reporting; never used in matching or ranking.",
    )
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    institution_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    enrollment_number: str | None = Field(default=None, max_length=60)
    degree: Degree | None = None
    program_name: str | None = Field(default=None, max_length=140)
    current_year: int | None = Field(default=None, ge=1, le=6)
    current_semester: int | None = Field(default=None, ge=1, le=12)
    cgpa: float | None = Field(default=None, ge=0, le=10)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    backlogs: int | None = Field(default=None, ge=0, le=50)
    career_interests: list[str] | None = Field(default=None, max_length=12)
    preferred_roles: list[str] | None = Field(default=None, max_length=12)
    preferred_industries: list[str] | None = Field(default=None, max_length=12)
    preferred_locations: list[str] | None = Field(default=None, max_length=12)
    preferred_work_mode: WorkMode | None = None
    open_to_relocate: bool | None = None
    expected_stipend_min: int | None = Field(default=None, ge=0)
    expected_salary_min: int | None = Field(default=None, ge=0)
    target_job_role_id: uuid.UUID | None = None
    portfolio_visibility: Visibility | None = None
    is_open_to_work: bool | None = None
    github_url: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=255)
    portfolio_url: str | None = Field(default=None, max_length=255)


# ----------------------------------------------------------- sub-resources --
class EducationIn(APIModel):
    level: Degree
    institution_name: str = Field(min_length=2, max_length=200)
    board_or_university: str | None = Field(default=None, max_length=200)
    program: str | None = Field(default=None, max_length=160)
    specialization: str | None = Field(default=None, max_length=160)
    start_year: int = Field(ge=1950, le=2100)
    end_year: int | None = Field(default=None, ge=1950, le=2100)
    score_value: float | None = Field(default=None, ge=0)
    score_type: str = Field(default="PERCENTAGE", pattern="^(PERCENTAGE|CGPA|GRADE)$")

    @model_validator(mode="after")
    def _years(self) -> EducationIn:
        if self.end_year is not None and self.end_year < self.start_year:
            raise ValueError("End year cannot be before start year")
        if self.score_type == "CGPA" and self.score_value and self.score_value > 10:
            raise ValueError("CGPA must be 10 or less")
        if self.score_type == "PERCENTAGE" and self.score_value and self.score_value > 100:
            raise ValueError("Percentage must be 100 or less")
        return self


class EducationOut(EducationIn):
    id: uuid.UUID
    is_verified: bool = False


class ExperienceIn(APIModel):
    kind: str = Field(default="INTERNSHIP", max_length=40)
    title: str = Field(min_length=2, max_length=180)
    organization: str = Field(min_length=1, max_length=180)
    location: str | None = Field(default=None, max_length=120)
    work_mode: WorkMode | None = None
    description: str = Field(default="", max_length=4000)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    skill_tags: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def _dates(self) -> ExperienceIn:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date")
        if self.is_current and self.end_date:
            raise ValueError("A current role cannot have an end date")
        return self


class ExperienceOut(ExperienceIn):
    id: uuid.UUID
    is_verified: bool = False
    source_application_id: uuid.UUID | None = None


class ProjectIn(APIModel):
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(default="", max_length=4000)
    role: str | None = Field(default=None, max_length=120)
    team_size: int = Field(default=1, ge=1, le=100)
    skill_tags: list[str] = Field(default_factory=list, max_length=20)
    repository_url: str | None = Field(default=None, max_length=255)
    demo_url: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    highlights: list[str] = Field(default_factory=list, max_length=10)
    is_featured: bool = False


class ProjectOut(ProjectIn):
    id: uuid.UUID


class AchievementIn(APIModel):
    category: str = Field(default="COMPETITION", max_length=40)
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2000)
    issuer: str | None = Field(default=None, max_length=180)
    achieved_on: date | None = None
    position: str | None = Field(default=None, max_length=60)
    url: str | None = Field(default=None, max_length=255)


class AchievementOut(AchievementIn):
    id: uuid.UUID
    is_verified: bool = False


# ------------------------------------------------------------- completion --
class CompletionSection(APIModel):
    key: str
    label: str
    weight: int
    earned: float
    percentage: int
    is_complete: bool


class CompletionSuggestion(APIModel):
    action: str
    impact: int
    url: str


class ProfileCompletionOut(APIModel):
    percentage: int
    sections: list[CompletionSection]
    suggestions: list[CompletionSuggestion]
    counts: dict[str, int]


# -------------------------------------------------------------- dashboard --
class DashboardSkill(APIModel):
    skill_id: uuid.UUID
    name: str
    level: str
    score: float
    confidence: float
    source: str


class DashboardGapSkill(APIModel):
    skill_id: uuid.UUID
    skill_name: str
    status: str
    current_level: str
    required_level: str
    priority: int


class DashboardGap(APIModel):
    job_role_id: uuid.UUID
    job_role_title: str
    readiness_score: float
    gap_percentage: float
    matched_count: int
    total_required: int
    summary: str
    priority_skills: list[DashboardGapSkill] = []


class DashboardApplication(APIModel):
    id: uuid.UUID
    status: str
    match_score: float
    submitted_at: datetime
    opportunity_id: uuid.UUID
    opportunity_title: str
    company_name: str


class DashboardApplications(APIModel):
    total: int
    by_status: dict[str, int]
    interviews_scheduled: int
    recent: list[DashboardApplication]


class DashboardDeadline(APIModel):
    id: uuid.UUID
    title: str
    company_name: str
    type: str
    deadline: datetime


class DashboardEnrollment(APIModel):
    id: uuid.UUID
    program_id: uuid.UUID
    title: str
    progress: float
    status: str


class DashboardLearning(APIModel):
    active_enrollments: int
    completed: int
    certifications: int
    recent: list[DashboardEnrollment]


class DashboardAttempt(APIModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    title: str
    percentage: float
    is_passed: bool
    submitted_at: datetime | None


class DashboardAssessments(APIModel):
    completed: int
    recent: list[DashboardAttempt]


class DashboardBadge(APIModel):
    code: str
    name: str
    icon: str
    awarded_at: datetime


class DashboardPortfolio(APIModel):
    slug: str | None
    visibility: str
    is_published: bool


class TargetRoleBrief(APIModel):
    id: uuid.UUID
    title: str


class StudentDashboardOut(APIModel):
    profile_completion: ProfileCompletionOut
    skill_readiness_score: float
    readiness_computed_at: datetime | None = None
    target_role: TargetRoleBrief | None = None
    top_skills: list[DashboardSkill] = []
    skill_gap: DashboardGap | None = None
    applications: DashboardApplications
    upcoming_deadlines: list[DashboardDeadline] = []
    learning: DashboardLearning
    assessments: DashboardAssessments
    badges: list[DashboardBadge] = []
    portfolio: DashboardPortfolio


class StudentSummaryOut(APIModel):
    """Compact student card used by recruiter search and institution lists."""

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    headline: str | None = None
    avatar_url: str | None = None
    city: str | None = None
    institution_name: str | None = None
    department_name: str | None = None
    degree: Degree | None = None
    graduation_year: int | None = None
    cgpa: float | None = None
    skill_readiness_score: float = 0.0
    profile_completion: int = 0
    is_placed: bool = False
    is_open_to_work: bool = True
    top_skills: list[str] = []
    portfolio_slug: str | None = None
