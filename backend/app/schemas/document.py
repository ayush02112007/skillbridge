"""Document, portfolio and resume schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.models.enums import DocumentType, ScanStatus, Visibility
from app.schemas.common import APIModel


class DocumentOut(APIModel):
    id: uuid.UUID
    document_type: DocumentType
    title: str
    original_filename: str
    content_type: str
    size_bytes: int
    visibility: Visibility
    scan_status: ScanStatus
    is_primary_resume: bool = False
    extraction_status: str = "PENDING"
    download_count: int = 0
    created_at: datetime
    # Short-lived signed URL, generated per request. Never a filesystem path.
    download_url: str | None = None


class DocumentUpdate(APIModel):
    title: str | None = Field(default=None, max_length=220)
    visibility: Visibility | None = None
    is_primary_resume: bool | None = None


class DocumentGrantIn(APIModel):
    granted_to_user_id: uuid.UUID
    reason: str = Field(default="", max_length=200)
    expires_in_hours: int | None = Field(default=168, ge=1, le=8760)


class ResumeAnalysisOut(APIModel):
    id: uuid.UUID
    document_id: uuid.UUID
    job_role_id: uuid.UUID | None = None
    job_role_title: str | None = None
    ats_score: int
    extracted_skills: list[Any] = []
    extracted_education: list[Any] = []
    extracted_experience: list[Any] = []
    extracted_projects: list[Any] = []
    extracted_certifications: list[Any] = []
    matched_skills: list[Any] = []
    missing_skills: list[Any] = []
    suggestions: list[Any] = []
    analyzed_by: str = "deterministic"
    created_at: datetime


class ResumeAnalysisRequest(APIModel):
    job_role_id: uuid.UUID | None = None
    import_skills: bool = Field(
        default=False,
        description="Add the detected skills to your profile as resume-sourced "
                    "evidence (lower confidence than an assessment).",
    )


# ----------------------------------------------------------- portfolio ----
class PortfolioOut(APIModel):
    id: uuid.UUID
    slug: str
    headline: str = ""
    about: str = ""
    theme: str = "slate"
    visibility: Visibility
    sections: list[Any] = []
    featured_project_ids: list[Any] = []
    contact_email_visible: bool = False
    phone_visible: bool = False
    view_count: int = 0
    completion_percentage: int = 0
    published_at: datetime | None = None


class PortfolioUpdate(APIModel):
    headline: str | None = Field(default=None, max_length=200)
    about: str | None = Field(default=None, max_length=4000)
    theme: Literal["slate", "indigo", "emerald", "amber", "rose"] | None = None
    visibility: Visibility | None = None
    sections: list[str] | None = None
    featured_project_ids: list[uuid.UUID] | None = None
    contact_email_visible: bool | None = None
    phone_visible: bool | None = None


class PublicPortfolioOut(APIModel):
    """What a visitor sees. Contact details appear only if explicitly enabled."""

    slug: str
    full_name: str
    headline: str = ""
    about: str = ""
    theme: str = "slate"
    avatar_url: str | None = None
    city: str | None = None
    institution_name: str | None = None
    program_name: str | None = None
    graduation_year: int | None = None
    email: str | None = None
    phone: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    skills: list[dict[str, Any]] = []
    education: list[dict[str, Any]] = []
    experience: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    certifications: list[dict[str, Any]] = []
    achievements: list[dict[str, Any]] = []
    badges: list[dict[str, Any]] = []
    skill_readiness_score: float = 0.0
    verified_credential_count: int = 0


# ------------------------------------------------------- resume builder ---
class ResumeContact(APIModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: list[dict[str, str]] = []


class ResumeSectionEntry(APIModel):
    title: str = ""
    subtitle: str = ""
    start: str = ""
    end: str = ""
    location: str = ""
    bullets: list[str] = []


class ResumeContent(APIModel):
    contact: ResumeContact = ResumeContact()
    summary: str = ""
    skills: list[str] = []
    education: list[ResumeSectionEntry] = []
    experience: list[ResumeSectionEntry] = []
    projects: list[ResumeSectionEntry] = []
    certifications: list[ResumeSectionEntry] = []
    achievements: list[str] = []


class ResumeIn(APIModel):
    title: str = Field(default="My Resume", max_length=160)
    template: Literal["modern", "minimal", "professional", "technical"] = "modern"
    content: ResumeContent = ResumeContent()
    target_job_role_id: uuid.UUID | None = None
    is_default: bool = False


class ResumeOut(APIModel):
    id: uuid.UUID
    title: str
    template: str
    content: dict[str, Any] = {}
    target_job_role_id: uuid.UUID | None = None
    is_default: bool = False
    last_exported_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
