"""Opportunity lifecycle: creation, publication, search and JD analysis."""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_polymorphic

from app.ai import matching
from app.ai.service import get_ai_service
from app.ai.text import extract_skills, normalise
from app.core.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.logging import get_logger
from app.models.enums import (
    OpportunityStatus,
    OpportunityType,
    ProficiencyLevel,
    RoleName,
    SkillImportance,
)
from app.models.opportunity import (
    FacultyOpportunity,
    Internship,
    Job,
    LiveProject,
    Opportunity,
    OpportunitySkill,
    SavedOpportunity,
)
from app.models.organization import Company
from app.models.profile import StudentProfile
from app.models.skill import JobRole, RoleSkill, Skill
from app.models.user import User
from app.services import skill as skill_service
from app.services.auth import unique_slug

log = get_logger("opportunities")

MODEL_FOR_TYPE: dict[OpportunityType, type[Opportunity]] = {
    OpportunityType.INTERNSHIP: Internship,
    OpportunityType.JOB: Job,
    OpportunityType.LIVE_PROJECT: LiveProject,
    OpportunityType.FACULTY_OPPORTUNITY: FacultyOpportunity,
}

# Columns that live on a subtype table rather than on Opportunity.
SUBTYPE_FIELDS: dict[OpportunityType, set[str]] = {
    OpportunityType.INTERNSHIP: {
        "duration_weeks", "stipend_min", "stipend_max", "stipend_currency",
        "is_paid", "learning_outcomes", "mentor_name", "is_ppo_available",
        "certificate_provided",
    },
    OpportunityType.JOB: {
        "employment_type", "salary_min", "salary_max", "salary_currency",
        "salary_period", "experience_min_years", "experience_max_years",
        "notice_period_days", "bond_months", "hiring_process",
    },
    OpportunityType.LIVE_PROJECT: {
        "problem_statement", "expected_outcome", "team_size_min", "team_size_max",
        "timeline_weeks", "stipend_amount", "mentor_user_id",
        "allows_team_application",
    },
    OpportunityType.FACULTY_OPPORTUNITY: {
        "kind", "duration_days", "honorarium", "min_teaching_experience_years",
        "focus_areas", "certification_provided", "seats",
    },
}

BASE_FIELDS = {
    "title", "description", "responsibilities", "eligibility_text", "work_mode",
    "location_city", "location_country", "positions", "min_cgpa", "max_backlogs",
    "eligible_degrees", "eligible_graduation_years", "eligible_departments",
    "application_deadline", "starts_on", "perks", "job_role_id",
}


def _now() -> datetime:
    return datetime.now(UTC)


def build_search_text(opportunity: Opportunity, skill_names: Sequence[str]) -> str:
    """Denormalised text blob backing full-text search.

    PostgreSQL full-text search runs over this column; the same column powers a
    LIKE fallback on SQLite, so search behaves consistently in every environment.
    """
    parts = [
        opportunity.title,
        opportunity.description or "",
        opportunity.location_city or "",
        " ".join(str(r) for r in (opportunity.responsibilities or [])),
        " ".join(str(p) for p in (opportunity.perks or [])),
        " ".join(skill_names),
    ]
    if opportunity.company:
        parts.extend([opportunity.company.name, opportunity.company.industry_sector or ""])
    if opportunity.job_role:
        parts.append(opportunity.job_role.title)
    return normalise(" ".join(p for p in parts if p)).lower()[:12000]


async def refresh_search_text(db: AsyncSession, opportunity: Opportunity) -> None:
    names = [
        s.skill.name
        for s in (
            await db.execute(
                select(OpportunitySkill)
                .where(OpportunitySkill.opportunity_id == opportunity.id)
                .options(selectinload(OpportunitySkill.skill))
            )
        ).scalars()
        if s.skill
    ]
    opportunity.search_text = build_search_text(opportunity, names)


async def _set_skills(
    db: AsyncSession, opportunity: Opportunity, skills: list[Any]
) -> None:
    await db.execute(
        delete(OpportunitySkill).where(
            OpportunitySkill.opportunity_id == opportunity.id
        )
    )
    seen: set[uuid.UUID] = set()
    for entry in skills:
        skill_id = entry.skill_id if hasattr(entry, "skill_id") else entry["skill_id"]
        if skill_id in seen:
            continue
        seen.add(skill_id)
        if await db.get(Skill, skill_id) is None:
            raise NotFoundError(f"Skill {skill_id} not found", code="SKILL_NOT_FOUND")
        db.add(
            OpportunitySkill(
                opportunity_id=opportunity.id,
                skill_id=skill_id,
                required_level=(
                    entry.required_level if hasattr(entry, "required_level")
                    else entry["required_level"]
                ),
                importance=(
                    entry.importance if hasattr(entry, "importance") else entry["importance"]
                ),
                weight=entry.weight if hasattr(entry, "weight") else entry["weight"],
            )
        )
    await db.flush()


async def create_opportunity(
    db: AsyncSession,
    *,
    opportunity_type: OpportunityType,
    payload: Any,
    company_id: uuid.UUID,
    posted_by: User,
    publish: bool = False,
) -> Opportunity:
    company = await db.get(Company, company_id)
    if company is None or company.deleted_at is not None:
        raise NotFoundError("Company not found", code="COMPANY_NOT_FOUND")

    data = payload.model_dump()
    skills = data.pop("skills", []) or []
    if data.get("job_role_id") and await db.get(JobRole, data["job_role_id"]) is None:
        raise NotFoundError("Job role not found", code="JOB_ROLE_NOT_FOUND")

    model = MODEL_FOR_TYPE[opportunity_type]
    base = {k: v for k, v in data.items() if k in BASE_FIELDS}
    subtype = {k: v for k, v in data.items() if k in SUBTYPE_FIELDS[opportunity_type]}

    opportunity = model(
        **base,
        **subtype,
        company_id=company.id,
        posted_by_id=posted_by.id,
        slug=await unique_slug(db, Opportunity, f"{payload.title}-{company.slug}"),
        status=OpportunityStatus.PUBLISHED if publish else OpportunityStatus.DRAFT,
        published_at=_now() if publish else None,
    )
    db.add(opportunity)
    await db.flush()

    # If the recruiter did not list skills, inherit the role's canonical profile
    # so the posting is still matchable rather than invisible to the engine.
    if not skills and opportunity.job_role_id:
        role_skills = (
            await db.execute(
                select(RoleSkill).where(RoleSkill.job_role_id == opportunity.job_role_id)
            )
        ).scalars().all()
        skills = [
            {
                "skill_id": rs.skill_id,
                "required_level": rs.required_level,
                "importance": rs.importance,
                "weight": rs.weight,
            }
            for rs in role_skills
        ]
    await _set_skills(db, opportunity, skills)

    await db.refresh(opportunity, ["company", "job_role"])
    await refresh_search_text(db, opportunity)
    await db.flush()
    log.info(
        "opportunities.created",
        id=str(opportunity.id), type=opportunity_type.value,
        company=company.slug, published=publish,
    )
    return opportunity


async def update_opportunity(
    db: AsyncSession, opportunity: Opportunity, payload: Any
) -> Opportunity:
    changes = payload.model_dump(exclude_unset=True)
    skills = changes.pop("skills", None)
    extra = changes.pop("extra", {}) or {}

    for field, value in changes.items():
        if field in BASE_FIELDS:
            setattr(opportunity, field, value)

    allowed_extra = SUBTYPE_FIELDS[opportunity.opportunity_type]
    unknown = set(extra) - allowed_extra
    if unknown:
        raise ValidationError(
            "Unknown fields for this opportunity type",
            code="UNKNOWN_FIELDS",
            details={"unknown": sorted(unknown), "allowed": sorted(allowed_extra)},
        )
    for field, value in extra.items():
        setattr(opportunity, field, value)

    if skills is not None:
        await _set_skills(db, opportunity, skills)
    await refresh_search_text(db, opportunity)
    await db.flush()
    return opportunity


async def change_status(
    db: AsyncSession, opportunity: Opportunity, status: OpportunityStatus
) -> Opportunity:
    if status == OpportunityStatus.PUBLISHED:
        problems = []
        if len(opportunity.description or "") < 20:
            problems.append("a description of at least 20 characters")
        skill_count = (
            await db.execute(
                select(func.count())
                .select_from(OpportunitySkill)
                .where(OpportunitySkill.opportunity_id == opportunity.id)
            )
        ).scalar_one()
        if not skill_count:
            problems.append("at least one required skill")
        if problems:
            raise BusinessRuleError(
                "This posting cannot be published yet: it needs " + ", ".join(problems),
                code="OPPORTUNITY_INCOMPLETE",
                details={"missing": problems},
            )
        if opportunity.published_at is None:
            opportunity.published_at = _now()
    if status in (OpportunityStatus.CLOSED, OpportunityStatus.ARCHIVED):
        opportunity.closed_at = _now()
    opportunity.status = status
    await db.flush()
    return opportunity


def assert_can_manage(opportunity: Opportunity, user: User, company_id: uuid.UUID) -> None:
    """Object-level authorisation: recruiters act only for their own company."""
    if RoleName.SUPER_ADMIN.value in user.role_names:
        return
    if opportunity.company_id != company_id:
        raise PermissionDeniedError(
            "This posting belongs to another company", code="CROSS_COMPANY_ACCESS"
        )


# ------------------------------------------------------------- retrieval ---
def polymorphic_opportunity():
    return with_polymorphic(Opportunity, "*")


async def get_opportunity_or_404(
    db: AsyncSession, opportunity_id: uuid.UUID, *, include_unpublished: bool = False
) -> Opportunity:
    entity = polymorphic_opportunity()
    stmt = (
        select(entity)
        .where(entity.id == opportunity_id, entity.deleted_at.is_(None))
        .options(
            selectinload(entity.company),
            selectinload(entity.job_role),
            selectinload(entity.skills).selectinload(OpportunitySkill.skill),
        )
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Opportunity not found", code="OPPORTUNITY_NOT_FOUND")
    if not include_unpublished and row.status != OpportunityStatus.PUBLISHED:
        raise NotFoundError("Opportunity not found", code="OPPORTUNITY_NOT_FOUND")
    return row


def apply_filters(
    stmt: Select,
    entity: Any,
    *,
    q: str | None = None,
    opportunity_type: OpportunityType | None = None,
    company_id: uuid.UUID | None = None,
    job_role_id: uuid.UUID | None = None,
    skill_ids: Sequence[uuid.UUID] | None = None,
    location: str | None = None,
    work_mode: Any = None,
    min_stipend: int | None = None,
    min_salary: int | None = None,
    max_experience_years: float | None = None,
    open_only: bool = True,
    status: OpportunityStatus | None = None,
    is_demo: bool | None = None,
) -> Select:
    if opportunity_type:
        stmt = stmt.where(entity.opportunity_type == opportunity_type)
    if company_id:
        stmt = stmt.where(entity.company_id == company_id)
    if job_role_id:
        stmt = stmt.where(entity.job_role_id == job_role_id)
    if status:
        stmt = stmt.where(entity.status == status)
    if q:
        needle = f"%{q.lower().strip()}%"
        stmt = stmt.where(
            or_(func.lower(entity.title).like(needle), entity.search_text.like(needle))
        )
    if location:
        stmt = stmt.where(func.lower(entity.location_city) == location.lower().strip())
    if work_mode:
        stmt = stmt.where(entity.work_mode == work_mode)
    if skill_ids:
        stmt = stmt.where(
            entity.id.in_(
                select(OpportunitySkill.opportunity_id).where(
                    OpportunitySkill.skill_id.in_(list(skill_ids))
                )
            )
        )
    if min_stipend is not None:
        stmt = stmt.where(
            entity.Internship.stipend_max.isnot(None),
            entity.Internship.stipend_max >= min_stipend,
        )
    if min_salary is not None:
        stmt = stmt.where(
            entity.Job.salary_max.isnot(None), entity.Job.salary_max >= min_salary
        )
    if max_experience_years is not None:
        stmt = stmt.where(entity.Job.experience_min_years <= max_experience_years)
    if open_only:
        stmt = stmt.where(
            entity.status == OpportunityStatus.PUBLISHED,
            or_(
                entity.application_deadline.is_(None),
                entity.application_deadline >= _now(),
            ),
        )
    if is_demo is not None:
        stmt = stmt.where(entity.is_demo.is_(is_demo))
    return stmt.where(entity.deleted_at.is_(None))


async def saved_opportunity_ids(
    db: AsyncSession, user_id: uuid.UUID, opportunity_ids: Sequence[uuid.UUID]
) -> set[uuid.UUID]:
    if not opportunity_ids:
        return set()
    rows = (
        await db.execute(
            select(SavedOpportunity.opportunity_id).where(
                SavedOpportunity.user_id == user_id,
                SavedOpportunity.opportunity_id.in_(list(opportunity_ids)),
            )
        )
    ).scalars().all()
    return set(rows)


async def applied_opportunity_ids(
    db: AsyncSession, student_id: uuid.UUID, opportunity_ids: Sequence[uuid.UUID]
) -> set[uuid.UUID]:
    from app.models.application import Application

    if not opportunity_ids:
        return set()
    rows = (
        await db.execute(
            select(Application.opportunity_id).where(
                Application.student_id == student_id,
                Application.opportunity_id.in_(list(opportunity_ids)),
            )
        )
    ).scalars().all()
    return set(rows)


# -------------------------------------------------- job description parse --
LEVEL_BY_FREQUENCY = [
    (5, ProficiencyLevel.ADVANCED),
    (3, ProficiencyLevel.INTERMEDIATE),
    (0, ProficiencyLevel.BEGINNER),
]

PREFERRED_MARKERS = (
    "nice to have", "good to have", "plus", "bonus", "preferred", "desirable",
    "advantage", "familiarity with",
)


async def analyse_job_description(
    db: AsyncSession, description: str, title: str | None = None
) -> dict[str, Any]:
    """Turn free-text into structured, reviewable requirements.

    Skills are detected by exact taxonomy matching so a recruiter is never shown
    a requirement the text does not contain. The result is a *suggestion*: the
    recruiter edits it before publishing.
    """
    vocabulary = await skill_service.get_skill_vocabulary(db)
    text = f"{title or ''}\n{description}"
    hits = extract_skills(text, vocabulary)

    detected: list[dict[str, Any]] = []
    for hit in hits:
        level = next(
            level for threshold, level in LEVEL_BY_FREQUENCY if hit.occurrences > threshold
        )
        context = " ".join(hit.contexts).lower()
        importance = (
            SkillImportance.PREFERRED
            if any(marker in context for marker in PREFERRED_MARKERS)
            else SkillImportance.REQUIRED
        )
        detected.append(
            {
                "skill_id": uuid.UUID(hit.skill_id),
                "skill_name": hit.skill_name,
                "matched_term": hit.matched_term,
                "occurrences": hit.occurrences,
                "suggested_level": level,
                "suggested_importance": importance,
            }
        )

    result = await get_ai_service().extract_job_requirements(
        description, [
            {
                "skill_id": str(d["skill_id"]),
                "skill_name": d["skill_name"],
                "occurrences": d["occurrences"],
            }
            for d in detected
        ]
    )

    # Suggest the closest canonical role by title overlap, then skill overlap.
    suggested_role: JobRole | None = None
    roles = (
        await db.execute(
            select(JobRole)
            .where(JobRole.is_active.is_(True))
            .options(selectinload(JobRole.required_skills))
        )
    ).scalars().all()
    haystack = (title or "").lower()
    for role in roles:
        if role.title.lower() in haystack or haystack in role.title.lower():
            suggested_role = role
            break
    if suggested_role is None and detected:
        detected_ids = {d["skill_id"] for d in detected}
        best, best_overlap = None, 0
        for role in roles:
            overlap = len(detected_ids & {rs.skill_id for rs in role.required_skills})
            if overlap > best_overlap:
                best, best_overlap = role, overlap
        if best_overlap >= 3:
            suggested_role = best

    return {
        "skills": detected,
        "keywords": result.get("keywords", []),
        "responsibilities": result.get("responsibilities", []),
        "education": result.get("education"),
        "experience_years": result.get("experience_years"),
        "seniority": result.get("seniority"),
        "suggested_job_role_id": suggested_role.id if suggested_role else None,
        "suggested_job_role_title": suggested_role.title if suggested_role else None,
        "extracted_by": result.get("extracted_by", "deterministic"),
    }


# ------------------------------------------------------------- matching ----
async def match_student_to_opportunity(
    db: AsyncSession, student: StudentProfile, opportunity: Opportunity
) -> matching.MatchResult:
    candidate = await skill_service.build_candidate_snapshot(db, student)
    snapshot = await skill_service.build_opportunity_snapshot(db, opportunity)
    return matching.match(candidate, snapshot)


async def match_many(
    db: AsyncSession, student: StudentProfile, opportunities: Sequence[Opportunity]
) -> dict[uuid.UUID, matching.MatchResult]:
    """Score a page of opportunities for one student in a single pass."""
    if not opportunities:
        return {}
    candidate = await skill_service.build_candidate_snapshot(db, student)
    results: dict[uuid.UUID, matching.MatchResult] = {}
    for opportunity in opportunities:
        snapshot = await skill_service.build_opportunity_snapshot(db, opportunity)
        results[opportunity.id] = matching.match(candidate, snapshot)
    return results
