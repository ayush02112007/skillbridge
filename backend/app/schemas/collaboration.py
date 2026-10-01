"""Mentorship, event, research and academician schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from app.models.enums import (
    CollaborationStatus,
    EventType,
    MentorshipStatus,
    RegistrationStatus,
    ResearchProjectType,
    WorkMode,
)
from app.schemas.common import APIModel
from app.schemas.opportunity import CompanyBrief


# ----------------------------------------------------------- mentorship ---
class MentorIn(APIModel):
    headline: str = Field(default="", max_length=200)
    bio: str = Field(default="", max_length=4000)
    designation: str | None = Field(default=None, max_length=140)
    experience_years: int = Field(default=0, ge=0, le=60)
    industry: str | None = Field(default=None, max_length=100)
    expertise_skill_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    topics: list[str] = Field(default_factory=list, max_length=15)
    languages: list[str] = Field(default_factory=list, max_length=10)
    availability: list[dict[str, str]] = Field(default_factory=list, max_length=21)
    capacity_per_month: int = Field(default=4, ge=0, le=100)
    session_duration_minutes: int = Field(default=45, ge=15, le=240)
    is_accepting_requests: bool = True


class MentorOut(APIModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str = ""
    avatar_url: str | None = None
    headline: str = ""
    bio: str = ""
    designation: str | None = None
    experience_years: int = 0
    industry: str | None = None
    company_id: uuid.UUID | None = None
    institution_id: uuid.UUID | None = None
    expertise_skill_ids: list[Any] = []
    expertise_skills: list[str] = []
    topics: list[Any] = []
    languages: list[Any] = []
    availability: list[Any] = []
    capacity_per_month: int = 4
    session_duration_minutes: int = 45
    is_accepting_requests: bool = True
    rating: float = 0.0
    sessions_completed: int = 0
    is_demo: bool = False


class MentorshipRequestIn(APIModel):
    mentor_id: uuid.UUID
    topic: str = Field(min_length=3, max_length=200)
    message: str = Field(default="", max_length=4000)
    goals: list[str] = Field(default_factory=list, max_length=8)
    preferred_slots: list[str] = Field(default_factory=list, max_length=6)


class MentorshipRespondIn(APIModel):
    decision: Literal["ACCEPTED", "DECLINED"]
    response_message: str = Field(default="", max_length=2000)


class MentorshipSessionIn(APIModel):
    scheduled_at: datetime
    duration_minutes: int = Field(default=45, ge=15, le=240)
    meeting_link: str | None = Field(default=None, max_length=400)
    agenda: str = Field(default="", max_length=2000)


class MentorshipSessionOut(APIModel):
    id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int
    meeting_link: str | None = None
    agenda: str = ""
    status: str
    mentor_notes: str = ""
    student_notes: str = ""
    action_items: list[Any] = []
    student_rating: int | None = None
    student_feedback: str = ""
    completed_at: datetime | None = None


class MentorshipSessionUpdate(APIModel):
    status: Literal["SCHEDULED", "COMPLETED", "CANCELLED", "NO_SHOW"] | None = None
    mentor_notes: str | None = Field(default=None, max_length=4000)
    student_notes: str | None = Field(default=None, max_length=4000)
    action_items: list[str] | None = None
    student_rating: int | None = Field(default=None, ge=1, le=5)
    student_feedback: str | None = Field(default=None, max_length=2000)


class MentorshipRequestOut(APIModel):
    id: uuid.UUID
    mentor_id: uuid.UUID
    mentor: MentorOut | None = None
    student_id: uuid.UUID
    student_name: str = ""
    topic: str
    message: str = ""
    goals: list[Any] = []
    status: MentorshipStatus
    preferred_slots: list[Any] = []
    response_message: str = ""
    responded_at: datetime | None = None
    match_reason: str = ""
    sessions: list[MentorshipSessionOut] = []
    created_at: datetime


# --------------------------------------------------------------- events ---
class EventIn(APIModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=20000)
    event_type: EventType = EventType.WORKSHOP
    speaker_name: str | None = Field(default=None, max_length=160)
    speaker_designation: str | None = Field(default=None, max_length=160)
    mode: WorkMode = WorkMode.REMOTE
    venue: str | None = Field(default=None, max_length=300)
    meeting_link: str | None = Field(default=None, max_length=500)
    starts_at: datetime
    ends_at: datetime
    registration_deadline: datetime | None = None
    capacity: int | None = Field(default=None, ge=1, le=100000)
    skill_tags: list[str] = Field(default_factory=list, max_length=15)
    target_audience: list[str] = Field(default_factory=list, max_length=10)
    grants_certificate: bool = True
    banner_url: str | None = Field(default=None, max_length=500)
    is_published: bool = True

    @model_validator(mode="after")
    def _times(self) -> EventIn:
        if self.ends_at <= self.starts_at:
            raise ValueError("The event must end after it starts")
        if self.registration_deadline and self.registration_deadline > self.starts_at:
            raise ValueError("Registration must close before the event starts")
        return self


class EventOut(APIModel):
    id: uuid.UUID
    title: str
    slug: str
    description: str = ""
    event_type: EventType
    host_company_id: uuid.UUID | None = None
    host_institution_id: uuid.UUID | None = None
    company: CompanyBrief | None = None
    speaker_name: str | None = None
    speaker_designation: str | None = None
    mode: WorkMode
    venue: str | None = None
    meeting_link: str | None = None
    starts_at: datetime
    ends_at: datetime
    registration_deadline: datetime | None = None
    capacity: int | None = None
    registered_count: int = 0
    skill_tags: list[Any] = []
    target_audience: list[Any] = []
    grants_certificate: bool = True
    banner_url: str | None = None
    is_published: bool = True
    is_registered: bool = False
    has_capacity: bool = True
    is_demo: bool = False


class EventRegistrationOut(APIModel):
    id: uuid.UUID
    event_id: uuid.UUID
    event: EventOut | None = None
    status: RegistrationStatus
    attended_at: datetime | None = None
    certificate_issued: bool = False
    certificate_code: str | None = None
    feedback_rating: int | None = None
    created_at: datetime


class EventFeedbackIn(APIModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)


class AttendanceIn(APIModel):
    user_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)
    issue_certificates: bool = True


# ------------------------------------------------------------- research ---
class ResearchProjectIn(APIModel):
    title: str = Field(min_length=5, max_length=250)
    abstract: str = Field(default="", max_length=20000)
    project_type: ResearchProjectType = ResearchProjectType.RESEARCH
    institution_id: uuid.UUID | None = None
    research_areas: list[str] = Field(default_factory=list, max_length=12)
    required_expertise: list[str] = Field(default_factory=list, max_length=12)
    deliverables: list[str] = Field(default_factory=list, max_length=12)
    funding_amount: int | None = Field(default=None, ge=0)
    funding_currency: str = Field(default="INR", max_length=8)
    duration_months: int | None = Field(default=None, ge=1, le=120)
    starts_on: date | None = None
    application_deadline: datetime | None = None
    positions: int = Field(default=1, ge=1, le=100)


class ResearchProjectOut(APIModel):
    id: uuid.UUID
    title: str
    slug: str
    abstract: str = ""
    project_type: ResearchProjectType
    status: CollaborationStatus
    company_id: uuid.UUID | None = None
    company: CompanyBrief | None = None
    institution_id: uuid.UUID | None = None
    research_areas: list[Any] = []
    required_expertise: list[Any] = []
    deliverables: list[Any] = []
    funding_amount: int | None = None
    funding_currency: str = "INR"
    duration_months: int | None = None
    starts_on: date | None = None
    application_deadline: datetime | None = None
    positions: int = 1
    application_count: int = 0
    has_applied: bool = False
    is_demo: bool = False
    created_at: datetime


class ResearchApplicationIn(APIModel):
    proposal: str = Field(min_length=20, max_length=20000)
    relevant_publications: list[str] = Field(default_factory=list, max_length=15)


class ResearchApplicationOut(APIModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project: ResearchProjectOut | None = None
    academician_id: uuid.UUID
    academician_name: str = ""
    proposal: str = ""
    relevant_publications: list[Any] = []
    status: str
    reviewer_notes: str = ""
    decided_at: datetime | None = None
    created_at: datetime


class ResearchDecisionIn(APIModel):
    status: Literal["UNDER_REVIEW", "SHORTLISTED", "ACCEPTED", "REJECTED"]
    reviewer_notes: str = Field(default="", max_length=4000)


# ---------------------------------------------------------- academician ---
class AcademicianProfileOut(APIModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str = ""
    email: str | None = None
    avatar_url: str | None = None
    institution_id: uuid.UUID | None = None
    institution_name: str | None = None
    department_id: uuid.UUID | None = None
    designation: str | None = None
    employee_code: str | None = None
    highest_qualification: str | None = None
    specialization: str | None = None
    teaching_experience_years: int = 0
    industry_experience_years: int = 0
    research_areas: list[Any] = []
    expertise_areas: list[Any] = []
    publications_count: int = 0
    patents_count: int = 0
    orcid_id: str | None = None
    google_scholar_url: str | None = None
    bio: str = ""
    city: str | None = None
    is_available_for_mentorship: bool = False
    is_available_for_consultancy: bool = False
    profile_completion: int = 0


class AcademicianProfileUpdate(APIModel):
    institution_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    designation: str | None = Field(default=None, max_length=120)
    employee_code: str | None = Field(default=None, max_length=60)
    highest_qualification: str | None = Field(default=None, max_length=120)
    specialization: str | None = Field(default=None, max_length=200)
    teaching_experience_years: int | None = Field(default=None, ge=0, le=60)
    industry_experience_years: int | None = Field(default=None, ge=0, le=60)
    research_areas: list[str] | None = Field(default=None, max_length=15)
    expertise_areas: list[str] | None = Field(default=None, max_length=15)
    publications_count: int | None = Field(default=None, ge=0, le=5000)
    patents_count: int | None = Field(default=None, ge=0, le=1000)
    orcid_id: str | None = Field(default=None, max_length=40)
    google_scholar_url: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=4000)
    city: str | None = Field(default=None, max_length=100)
    is_available_for_mentorship: bool | None = None
    is_available_for_consultancy: bool | None = None


class AcademicianDashboardOut(APIModel):
    profile_completion: int
    open_faculty_opportunities: int
    my_applications: dict[str, int]
    mentorship: dict[str, int]
    research: dict[str, int]
    events_hosted: int
    upcoming_sessions: list[dict[str, Any]] = []
    recommended_opportunities: list[dict[str, Any]] = []
