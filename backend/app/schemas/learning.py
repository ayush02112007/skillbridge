"""Learning programme, enrolment and certification schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field, model_validator

from app.models.enums import (
    Difficulty,
    EnrollmentStatus,
    ProgramType,
    VerificationStatus,
    WorkMode,
)
from app.schemas.common import APIModel
from app.schemas.opportunity import CompanyBrief
from app.schemas.skill import SkillBrief


class ProgramSkillIn(APIModel):
    skill_id: uuid.UUID
    target_level: str = Field(default="INTERMEDIATE", pattern="^(BEGINNER|INTERMEDIATE|ADVANCED|EXPERT)$")
    coverage_weight: float = Field(default=1.0, gt=0, le=3)


class ProgramSkillOut(APIModel):
    skill_id: uuid.UUID
    skill: SkillBrief | None = None
    target_level: str
    coverage_weight: float


class ModuleIn(APIModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=4000)
    content_type: str = Field(default="VIDEO", max_length=20)
    content_url: str | None = Field(default=None, max_length=500)
    duration_minutes: int = Field(default=30, ge=1, le=1440)
    display_order: int = 0
    is_mandatory: bool = True


class ModuleOut(ModuleIn):
    id: uuid.UUID


class ProgramCreate(APIModel):
    title: str = Field(min_length=3, max_length=200)
    summary: str = Field(default="", max_length=400)
    description: str = Field(default="", max_length=20000)
    program_type: ProgramType = ProgramType.COURSE
    provider_name: str | None = Field(default=None, max_length=180)
    difficulty: Difficulty = Difficulty.MEDIUM
    duration_hours: int = Field(default=10, ge=1, le=2000)
    mode: WorkMode = WorkMode.REMOTE
    price_amount: int = Field(default=0, ge=0)
    currency: str = Field(default="INR", max_length=8)
    external_url: str | None = Field(default=None, max_length=500)
    starts_on: date | None = None
    ends_on: date | None = None
    seats: int | None = Field(default=None, ge=1)
    grants_certificate: bool = True
    outcomes: list[str] = Field(default_factory=list, max_length=15)
    prerequisites: list[str] = Field(default_factory=list, max_length=15)
    is_published: bool = True
    skills: list[ProgramSkillIn] = Field(default_factory=list, max_length=20)
    modules: list[ModuleIn] = Field(default_factory=list, max_length=60)

    @model_validator(mode="after")
    def _dates(self) -> ProgramCreate:
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("End date cannot be before the start date")
        return self


class ProgramUpdate(APIModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    summary: str | None = None
    description: str | None = None
    difficulty: Difficulty | None = None
    duration_hours: int | None = Field(default=None, ge=1, le=2000)
    price_amount: int | None = Field(default=None, ge=0)
    external_url: str | None = None
    seats: int | None = None
    grants_certificate: bool | None = None
    outcomes: list[str] | None = None
    prerequisites: list[str] | None = None
    is_published: bool | None = None
    skills: list[ProgramSkillIn] | None = None


class ProgramListItem(APIModel):
    id: uuid.UUID
    title: str
    slug: str
    summary: str = ""
    program_type: ProgramType
    provider_name: str | None = None
    company: CompanyBrief | None = None
    difficulty: Difficulty
    duration_hours: int
    mode: WorkMode
    is_free: bool
    price_amount: int = 0
    currency: str = "INR"
    grants_certificate: bool = True
    rating: float = 0.0
    enrollment_count: int = 0
    skills: list[ProgramSkillOut] = []
    is_enrolled: bool = False
    is_demo: bool = False


class ProgramDetail(ProgramListItem):
    description: str = ""
    outcomes: list[Any] = []
    prerequisites: list[Any] = []
    external_url: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    seats: int | None = None
    modules: list[ModuleOut] = []
    created_at: datetime | None = None


class ModuleProgressOut(APIModel):
    module_id: uuid.UUID
    is_completed: bool
    completed_at: datetime | None = None
    time_spent_minutes: int = 0


class EnrollmentOut(APIModel):
    id: uuid.UUID
    program_id: uuid.UUID
    program: ProgramListItem | None = None
    status: EnrollmentStatus
    progress_percentage: float
    enrolled_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    final_score: float | None = None
    module_progress: list[ModuleProgressOut] = []


class ModuleCompleteIn(APIModel):
    is_completed: bool = True
    time_spent_minutes: int = Field(default=0, ge=0, le=100000)


class CertificationIn(APIModel):
    name: str = Field(min_length=2, max_length=200)
    issuer: str = Field(min_length=2, max_length=180)
    credential_id: str | None = Field(default=None, max_length=160)
    credential_url: str | None = Field(default=None, max_length=500)
    issued_on: date | None = None
    expires_on: date | None = None
    document_id: uuid.UUID | None = None
    skill_ids: list[uuid.UUID] = Field(default_factory=list, max_length=15)


class CertificationOut(APIModel):
    id: uuid.UUID
    name: str
    issuer: str
    credential_id: str | None = None
    credential_url: str | None = None
    issued_on: date | None = None
    expires_on: date | None = None
    document_id: uuid.UUID | None = None
    skill_ids: list[Any] = []
    verification_status: VerificationStatus
    created_at: datetime
