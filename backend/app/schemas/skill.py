"""Skill taxonomy, student skill profile and skill-gap schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from app.models.enums import ProficiencyLevel, SkillImportance, SkillSource
from app.schemas.common import APIModel


class SkillCategoryOut(APIModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str = ""
    icon: str | None = None
    color: str | None = None
    is_soft_skill: bool = False
    display_order: int = 0


class SkillOut(APIModel):
    id: uuid.UUID
    name: str
    slug: str
    category_id: uuid.UUID
    description: str = ""
    aliases: list[Any] = []
    is_soft_skill: bool = False
    is_trending: bool = False
    demand_score: float = 0.0
    learning_resources: list[Any] = []
    category: SkillCategoryOut | None = None


class SkillBrief(APIModel):
    id: uuid.UUID
    name: str
    slug: str
    demand_score: float = 0.0


class TaxonomyNode(APIModel):
    id: uuid.UUID
    name: str
    slug: str
    icon: str | None = None
    color: str | None = None
    is_soft_skill: bool = False
    skill_count: int = 0
    skills: list[SkillBrief] = []


class SkillCreate(APIModel):
    name: str = Field(min_length=1, max_length=120)
    category_id: uuid.UUID
    description: str = ""
    aliases: list[str] = []
    is_soft_skill: bool = False
    is_trending: bool = False
    learning_resources: list[dict[str, Any]] = []


class SkillUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category_id: uuid.UUID | None = None
    description: str | None = None
    aliases: list[str] | None = None
    is_soft_skill: bool | None = None
    is_trending: bool | None = None
    learning_resources: list[dict[str, Any]] | None = None
    is_active: bool | None = None


class SkillCategoryCreate(APIModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    parent_id: uuid.UUID | None = None
    icon: str | None = None
    color: str | None = None
    display_order: int = 0
    is_soft_skill: bool = False


# ------------------------------------------------------------- job roles ---
class RoleSkillOut(APIModel):
    skill_id: uuid.UUID
    skill: SkillBrief | None = None
    required_level: ProficiencyLevel
    importance: SkillImportance
    weight: float


class JobRoleOut(APIModel):
    id: uuid.UUID
    title: str
    slug: str
    family: str
    description: str = ""
    responsibilities: list[Any] = []
    typical_qualifications: list[Any] = []
    seniority: str = "ENTRY"
    avg_salary_min: int | None = None
    avg_salary_max: int | None = None
    demand_index: float = 0.0
    required_skills: list[RoleSkillOut] = []


class JobRoleBrief(APIModel):
    id: uuid.UUID
    title: str
    slug: str
    family: str
    demand_index: float = 0.0


class RoleSkillInput(APIModel):
    skill_id: uuid.UUID
    required_level: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE
    importance: SkillImportance = SkillImportance.REQUIRED
    weight: float = Field(default=1.0, gt=0, le=5)


class JobRoleCreate(APIModel):
    title: str = Field(min_length=2, max_length=140)
    family: str = "Engineering"
    description: str = ""
    responsibilities: list[str] = []
    typical_qualifications: list[str] = []
    seniority: Literal["ENTRY", "MID", "SENIOR", "LEAD"] = "ENTRY"
    avg_salary_min: int | None = Field(default=None, ge=0)
    avg_salary_max: int | None = Field(default=None, ge=0)
    skills: list[RoleSkillInput] = []


class JobRoleUpdate(APIModel):
    title: str | None = Field(default=None, min_length=2, max_length=140)
    family: str | None = None
    description: str | None = None
    responsibilities: list[str] | None = None
    typical_qualifications: list[str] | None = None
    seniority: Literal["ENTRY", "MID", "SENIOR", "LEAD"] | None = None
    avg_salary_min: int | None = None
    avg_salary_max: int | None = None
    skills: list[RoleSkillInput] | None = None
    is_active: bool | None = None


# -------------------------------------------------------- student skills ---
class StudentSkillOut(APIModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    skill: SkillBrief | None = None
    level: ProficiencyLevel
    score: float
    confidence: float
    source: SkillSource
    years_of_experience: float | None = None
    last_assessed_at: datetime | None = None
    endorsement_count: int = 0
    is_verified: bool = False
    evidence: dict[str, Any] = {}


class StudentSkillInput(APIModel):
    skill_id: uuid.UUID
    level: ProficiencyLevel = ProficiencyLevel.BEGINNER
    years_of_experience: float | None = Field(default=None, ge=0, le=50)

    @field_validator("level")
    @classmethod
    def _not_none_level(cls, v: ProficiencyLevel) -> ProficiencyLevel:
        if v == ProficiencyLevel.NONE:
            raise ValueError("Choose a level of BEGINNER or above")
        return v


class StudentSkillBulkInput(APIModel):
    skills: list[StudentSkillInput] = Field(min_length=1, max_length=100)


# ------------------------------------------------------------- skill gap ---
class GapItemOut(APIModel):
    skill_id: uuid.UUID | str
    skill_name: str
    skill_slug: str = ""
    category: str = ""
    current_level: str
    required_level: str
    status: Literal["MISSING", "WEAK", "STRONG"]
    gap_size: int
    importance: str
    weight: float
    coverage: float
    priority: int
    recommendation: str


class SkillGapOut(APIModel):
    job_role_id: uuid.UUID | str
    job_role_title: str
    readiness_score: float
    gap_percentage: float
    matched_count: int
    total_required: int
    summary: str
    computed_at: datetime | None = None
    generated_by: str = "deterministic"
    items: list[GapItemOut] = []
    missing_skills: list[GapItemOut] = []
    weak_skills: list[GapItemOut] = []
    strong_skills: list[GapItemOut] = []
    priority_skills: list[GapItemOut] = []


class RoleReadinessOut(APIModel):
    job_role_id: uuid.UUID
    title: str
    family: str
    readiness_score: float
    gap_percentage: float
    matched_count: int
    total_required: int
    top_missing: list[str] = []
    demand_index: float = 0.0
