"""Application, timeline and interview schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from app.models.enums import ApplicationStatus, OpportunityType
from app.schemas.common import APIModel
from app.schemas.opportunity import CompanyBrief


class ApplyRequest(APIModel):
    cover_letter: str = Field(default="", max_length=6000)
    resume_document_id: uuid.UUID | None = Field(
        default=None, description="One of your uploaded resume documents"
    )
    answers: dict[str, Any] = Field(
        default_factory=dict, description="Answers to any screening questions"
    )


class ApplicantBrief(APIModel):
    student_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    full_name: str = ""
    email: str | None = None
    avatar_url: str | None = None
    headline: str | None = None
    city: str | None = None
    institution_name: str | None = None
    degree: str | None = None
    graduation_year: int | None = None
    cgpa: float | None = None
    portfolio_slug: str | None = None
    skill_readiness_score: float = 0.0


class OpportunityBrief(APIModel):
    id: uuid.UUID
    title: str
    opportunity_type: OpportunityType
    location_city: str | None = None
    work_mode: str | None = None
    application_deadline: datetime | None = None
    company: CompanyBrief | None = None


class TimelineStep(APIModel):
    status: str
    label: str
    state: Literal["complete", "current", "upcoming", "stopped", "terminal"]
    reached_at: datetime | None = None


class StatusHistoryOut(APIModel):
    from_status: ApplicationStatus | None = None
    to_status: ApplicationStatus
    note: str = ""
    created_at: datetime


class InterviewOut(APIModel):
    id: uuid.UUID
    round_number: int
    round_name: str
    mode: str
    scheduled_at: datetime
    duration_minutes: int
    location_or_link: str | None = None
    interviewer_name: str | None = None
    status: str
    instructions: str = ""
    feedback: str = ""
    rating: int | None = None


class ApplicationOut(APIModel):
    id: uuid.UUID
    status: ApplicationStatus
    match_score: float
    match_breakdown: dict[str, Any] = {}
    matching_skills: list[Any] = []
    missing_skills: list[Any] = []
    cover_letter: str = ""
    resume_document_id: uuid.UUID | None = None
    submitted_at: datetime
    last_status_change_at: datetime | None = None
    decided_at: datetime | None = None
    rejection_reason: str | None = None
    recruiter_rating: int | None = None
    opportunity: OpportunityBrief | None = None
    applicant: ApplicantBrief | None = None
    timeline: list[TimelineStep] = []
    history: list[StatusHistoryOut] = []
    interviews: list[InterviewOut] = []
    # Recruiter-only field, omitted for students.
    recruiter_notes: str | None = None


class ApplicationListItem(APIModel):
    id: uuid.UUID
    status: ApplicationStatus
    match_score: float
    matching_skills: list[Any] = []
    missing_skills: list[Any] = []
    submitted_at: datetime
    last_status_change_at: datetime | None = None
    opportunity: OpportunityBrief | None = None
    applicant: ApplicantBrief | None = None
    next_interview_at: datetime | None = None
    recruiter_rating: int | None = None


class StatusChangeRequest(APIModel):
    status: ApplicationStatus
    note: str = Field(default="", max_length=2000)
    reason: str | None = Field(default=None, max_length=400)

    @field_validator("status")
    @classmethod
    def _not_applied(cls, v: ApplicationStatus) -> ApplicationStatus:
        if v == ApplicationStatus.APPLIED:
            raise ValueError("An application cannot be moved back to APPLIED")
        return v


class BulkStatusChangeRequest(APIModel):
    application_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
    status: ApplicationStatus
    note: str = Field(default="", max_length=2000)


class BulkStatusResult(APIModel):
    updated: int
    failed: list[dict[str, str]] = []


class WithdrawRequest(APIModel):
    reason: str = Field(default="", max_length=400)


class RecruiterNoteRequest(APIModel):
    recruiter_notes: str | None = Field(default=None, max_length=4000)
    recruiter_rating: int | None = Field(default=None, ge=1, le=5)


class InterviewCreate(APIModel):
    scheduled_at: datetime
    round_name: str = Field(default="Technical Round", max_length=120)
    duration_minutes: int = Field(default=45, ge=10, le=480)
    mode: Literal["ONLINE", "ONSITE", "PHONE"] = "ONLINE"
    location_or_link: str | None = Field(default=None, max_length=400)
    interviewer_name: str | None = Field(default=None, max_length=160)
    instructions: str = Field(default="", max_length=2000)


class InterviewFeedback(APIModel):
    status: Literal["SCHEDULED", "COMPLETED", "CANCELLED", "NO_SHOW"]
    feedback: str = Field(default="", max_length=4000)
    rating: int | None = Field(default=None, ge=1, le=5)


class ApplicationFunnelOut(APIModel):
    total: int
    by_status: dict[str, int]
    conversion: dict[str, float]
