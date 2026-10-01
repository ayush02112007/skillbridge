"""Skill taxonomy, student skill profile and skill-gap persistence.

This module is the bridge between the pure engines in ``app/ai`` and the
database: it loads rows, converts them into engine inputs, runs the engine and
persists the result.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai import matching, skill_gap
from app.ai.scoring import SOURCE_CONFIDENCE, HeldSkill, Requirement, blend_scores
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.enums import (
    ProficiencyLevel,
    SkillImportance,
    SkillSource,
)
from app.models.learning import StudentCertification
from app.models.opportunity import Opportunity, OpportunitySkill
from app.models.profile import ExperienceRecord, StudentProfile, StudentProject
from app.models.skill import (
    JobRole,
    RoleSkill,
    Skill,
    SkillCategory,
    SkillGapAnalysis,
    SkillGapItem,
    StudentSkill,
)

log = get_logger("skills")


def _now() -> datetime:
    return datetime.now(UTC)


# ------------------------------------------------------------- taxonomy ----
async def get_skill_vocabulary(db: AsyncSession) -> list[tuple[str, str, list[str]]]:
    """``(skill_id, name, aliases)`` tuples for the text extractors."""
    rows = (
        await db.execute(select(Skill).where(Skill.is_active.is_(True)))
    ).scalars().all()
    return [(str(s.id), s.name, list(s.aliases or [])) for s in rows]


async def get_taxonomy(db: AsyncSession) -> list[dict[str, Any]]:
    """The full category -> skills tree, as the admin panel and filters use it."""
    categories = (
        await db.execute(
            select(SkillCategory)
            .where(SkillCategory.is_active.is_(True))
            .order_by(SkillCategory.display_order, SkillCategory.name)
        )
    ).scalars().all()
    skills = (
        await db.execute(
            select(Skill).where(Skill.is_active.is_(True)).order_by(Skill.name)
        )
    ).scalars().all()
    by_category: dict[uuid.UUID, list[Skill]] = {}
    for skill in skills:
        by_category.setdefault(skill.category_id, []).append(skill)
    return [
        {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "icon": category.icon,
            "color": category.color,
            "is_soft_skill": category.is_soft_skill,
            "skill_count": len(by_category.get(category.id, [])),
            "skills": by_category.get(category.id, []),
        }
        for category in categories
    ]


async def resolve_skills(db: AsyncSession, skill_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Skill]:
    ids = list(skill_ids)
    if not ids:
        return {}
    rows = (await db.execute(select(Skill).where(Skill.id.in_(ids)))).scalars().all()
    return {s.id: s for s in rows}


async def find_skill_by_name(db: AsyncSession, name: str) -> Skill | None:
    """Match on canonical name first, then aliases."""
    cleaned = name.strip().lower()
    if not cleaned:
        return None
    direct = (
        await db.execute(select(Skill).where(func.lower(Skill.name) == cleaned))
    ).scalar_one_or_none()
    if direct:
        return direct
    for skill in (await db.execute(select(Skill))).scalars().all():
        if cleaned in [str(a).lower() for a in (skill.aliases or [])]:
            return skill
    return None


# -------------------------------------------------------- engine inputs ----
async def load_held_skills(db: AsyncSession, student_id: uuid.UUID) -> list[HeldSkill]:
    rows = (
        await db.execute(
            select(StudentSkill)
            .where(StudentSkill.student_id == student_id)
            .options(selectinload(StudentSkill.skill).selectinload(Skill.category))
        )
    ).scalars().all()
    return [
        HeldSkill(
            skill_id=str(row.skill_id),
            skill_name=row.skill.name if row.skill else "",
            level=row.level,
            score=row.score,
            confidence=row.confidence,
            source=row.source.value if hasattr(row.source, "value") else str(row.source),
            category=row.skill.category.slug if row.skill and row.skill.category else "",
            slug=row.skill.slug if row.skill else "",
        )
        for row in rows
    ]


async def load_role_requirements(
    db: AsyncSession, job_role_id: uuid.UUID
) -> list[Requirement]:
    rows = (
        await db.execute(
            select(RoleSkill)
            .where(RoleSkill.job_role_id == job_role_id)
            .options(selectinload(RoleSkill.skill).selectinload(Skill.category))
        )
    ).scalars().all()
    return [
        Requirement(
            skill_id=str(row.skill_id),
            skill_name=row.skill.name if row.skill else "",
            required_level=row.required_level,
            importance=row.importance,
            weight=row.weight,
            demand_score=row.skill.demand_score if row.skill else 0.0,
            category=row.skill.category.slug if row.skill and row.skill.category else "",
            slug=row.skill.slug if row.skill else "",
        )
        for row in rows
    ]


async def load_opportunity_requirements(
    db: AsyncSession, opportunity_id: uuid.UUID
) -> list[Requirement]:
    rows = (
        await db.execute(
            select(OpportunitySkill)
            .where(OpportunitySkill.opportunity_id == opportunity_id)
            .options(selectinload(OpportunitySkill.skill).selectinload(Skill.category))
        )
    ).scalars().all()
    return [
        Requirement(
            skill_id=str(row.skill_id),
            skill_name=row.skill.name if row.skill else "",
            required_level=row.required_level,
            importance=row.importance,
            weight=row.weight,
            demand_score=row.skill.demand_score if row.skill else 0.0,
            category=row.skill.category.slug if row.skill and row.skill.category else "",
            slug=row.skill.slug if row.skill else "",
        )
        for row in rows
    ]


async def build_candidate_snapshot(
    db: AsyncSession, student: StudentProfile
) -> matching.CandidateSnapshot:
    """Assemble the (privacy-scoped) view of a student the matcher may use."""
    skills = await load_held_skills(db, student.id)

    experiences = (
        await db.execute(
            select(ExperienceRecord).where(ExperienceRecord.student_id == student.id)
        )
    ).scalars().all()
    months = 0.0
    experience_skill_names: set[str] = set()
    for record in experiences:
        if record.start_date:
            end = record.end_date or datetime.now().date()
            months += max(0, (end - record.start_date).days) / 30.44
        experience_skill_names |= {str(t).lower() for t in (record.skill_tags or [])}

    projects = (
        await db.execute(
            select(StudentProject).where(StudentProject.student_id == student.id)
        )
    ).scalars().all()
    project_skill_names: set[str] = set()
    for project in projects:
        project_skill_names |= {str(t).lower() for t in (project.skill_tags or [])}

    certifications = (
        await db.execute(
            select(StudentCertification).where(
                StudentCertification.student_id == student.id
            )
        )
    ).scalars().all()
    certification_skill_ids = {
        str(sid) for cert in certifications for sid in (cert.skill_ids or [])
    }

    # Skill tags are stored as names; map them back onto taxonomy ids.
    name_to_id = {s.skill_name.lower(): s.skill_id for s in skills}
    all_skills = (await db.execute(select(Skill))).scalars().all()
    for skill in all_skills:
        name_to_id.setdefault(skill.name.lower(), str(skill.id))
        for alias in skill.aliases or []:
            name_to_id.setdefault(str(alias).lower(), str(skill.id))

    def to_ids(names: set[str]) -> set[str]:
        return {name_to_id[n] for n in names if n in name_to_id}

    department = None
    if student.department_id:
        from app.models.organization import Department

        dept = await db.get(Department, student.department_id)
        department = dept.code if dept else None

    return matching.CandidateSnapshot(
        skills=skills,
        degree=student.degree,
        cgpa=student.cgpa,
        graduation_year=student.graduation_year,
        backlogs=student.backlogs or 0,
        department=department,
        career_interests=list(student.career_interests or []),
        preferred_roles=list(student.preferred_roles or []),
        preferred_industries=list(student.preferred_industries or []),
        preferred_locations=list(student.preferred_locations or []),
        preferred_work_mode=student.preferred_work_mode,
        open_to_relocate=student.open_to_relocate,
        city=student.city,
        experience_months=round(months, 1),
        experience_skill_ids=to_ids(experience_skill_names),
        certification_skill_ids=certification_skill_ids,
        certification_count=len(certifications),
        project_skill_ids=to_ids(project_skill_names),
        project_count=len(projects),
    )


async def build_opportunity_snapshot(
    db: AsyncSession, opportunity: Opportunity
) -> matching.OpportunitySnapshot:
    requirements = await load_opportunity_requirements(db, opportunity.id)
    experience_min = float(getattr(opportunity, "experience_min_years", 0.0) or 0.0)
    return matching.OpportunitySnapshot(
        id=str(opportunity.id),
        title=opportunity.title,
        company_name=opportunity.company.name if opportunity.company else "",
        industry_sector=(
            opportunity.company.industry_sector if opportunity.company else ""
        ),
        requirements=requirements,
        job_role_title=opportunity.job_role.title if opportunity.job_role else None,
        work_mode=opportunity.work_mode,
        location_city=opportunity.location_city,
        min_cgpa=opportunity.min_cgpa,
        max_backlogs=opportunity.max_backlogs,
        eligible_degrees=list(opportunity.eligible_degrees or []),
        eligible_graduation_years=[
            int(y) for y in (opportunity.eligible_graduation_years or [])
        ],
        eligible_departments=list(opportunity.eligible_departments or []),
        experience_min_years=experience_min,
        opportunity_type=opportunity.opportunity_type.value,
    )


# --------------------------------------------------- student skill CRUD ----
async def upsert_student_skill(
    db: AsyncSession,
    student_id: uuid.UUID,
    skill_id: uuid.UUID,
    *,
    level: ProficiencyLevel,
    source: SkillSource,
    score: float | None = None,
    confidence: float | None = None,
    evidence: dict[str, Any] | None = None,
    years_of_experience: float | None = None,
    mark_assessed: bool = False,
) -> StudentSkill:
    """Create or merge a skill claim, combining evidence rather than overwriting.

    A fresh assessment result should raise (or lower) a self-reported level and
    raise confidence; a second self-report should not pretend to be proof.
    """
    existing = (
        await db.execute(
            select(StudentSkill).where(
                StudentSkill.student_id == student_id,
                StudentSkill.skill_id == skill_id,
            )
        )
    ).scalar_one_or_none()

    incoming_confidence = (
        confidence if confidence is not None else SOURCE_CONFIDENCE.get(source.value, 0.35)
    )
    incoming_score = score if score is not None else level.score * 25.0

    if existing is None:
        row = StudentSkill(
            student_id=student_id,
            skill_id=skill_id,
            level=level,
            score=round(incoming_score, 2),
            confidence=round(incoming_confidence, 3),
            source=source,
            evidence=evidence or {},
            years_of_experience=years_of_experience,
            last_assessed_at=_now() if mark_assessed else None,
        )
        db.add(row)
        await db.flush()
        return row

    # An assessment is authoritative: it replaces the level outright.
    if source == SkillSource.ASSESSMENT:
        existing.level = level
        existing.score = round(incoming_score, 2)
        existing.confidence = round(max(existing.confidence, incoming_confidence), 3)
        existing.source = source
        existing.last_assessed_at = _now()
    else:
        merged_score, merged_confidence = blend_scores(
            existing.score, incoming_score, existing.confidence, incoming_confidence
        )
        existing.score = merged_score
        existing.confidence = merged_confidence
        # Keep the stronger evidence source; never downgrade an assessed skill.
        if SOURCE_CONFIDENCE.get(source.value, 0) > SOURCE_CONFIDENCE.get(
            existing.source.value, 0
        ):
            existing.source = source
        if existing.source != SkillSource.ASSESSMENT:
            existing.level = ProficiencyLevel.from_score(merged_score)
    if evidence:
        merged = dict(existing.evidence or {})
        merged.update(evidence)
        existing.evidence = merged
    if years_of_experience is not None:
        existing.years_of_experience = years_of_experience
    await db.flush()
    return existing


async def remove_student_skill(
    db: AsyncSession, student_id: uuid.UUID, skill_id: uuid.UUID
) -> None:
    result = await db.execute(
        delete(StudentSkill).where(
            StudentSkill.student_id == student_id, StudentSkill.skill_id == skill_id
        )
    )
    if not result.rowcount:
        raise NotFoundError("Skill is not on your profile", code="STUDENT_SKILL_NOT_FOUND")


# ----------------------------------------------------------- skill gap -----
async def compute_skill_gap(
    db: AsyncSession,
    student: StudentProfile,
    job_role: JobRole,
    *,
    persist: bool = True,
) -> skill_gap.GapResult:
    """Run the gap engine for one student/role pair and store the snapshot."""
    held = await load_held_skills(db, student.id)
    requirements = await load_role_requirements(db, job_role.id)
    if not requirements:
        raise ValidationError(
            f"No skill requirements are defined for {job_role.title}",
            code="ROLE_HAS_NO_REQUIREMENTS",
        )

    result = skill_gap.analyse(
        held, requirements, job_role_id=str(job_role.id), job_role_title=job_role.title
    )
    if not persist:
        return result

    analysis = (
        await db.execute(
            select(SkillGapAnalysis).where(
                SkillGapAnalysis.student_id == student.id,
                SkillGapAnalysis.job_role_id == job_role.id,
            )
        )
    ).scalar_one_or_none()
    if analysis is None:
        analysis = SkillGapAnalysis(student_id=student.id, job_role_id=job_role.id)
        db.add(analysis)
        await db.flush()
    else:
        await db.execute(
            delete(SkillGapItem).where(SkillGapItem.analysis_id == analysis.id)
        )

    analysis.readiness_score = result.readiness_score
    analysis.gap_percentage = result.gap_percentage
    analysis.matched_count = result.matched_count
    analysis.total_required = result.total_required
    analysis.summary = result.summary
    analysis.computed_at = _now()

    for item in result.items:
        db.add(
            SkillGapItem(
                analysis_id=analysis.id,
                skill_id=uuid.UUID(item.skill_id),
                current_level=ProficiencyLevel(item.current_level),
                required_level=ProficiencyLevel(item.required_level),
                status=item.status,
                gap_size=item.gap_size,
                priority=item.priority,
                importance=SkillImportance(item.importance),
                recommendation=item.recommendation,
            )
        )
    await db.flush()

    # The readiness score shown on the dashboard tracks the student's own target.
    if student.target_job_role_id == job_role.id:
        student.skill_readiness_score = result.readiness_score
        student.readiness_computed_at = _now()
    return result


async def compute_all_role_readiness(
    db: AsyncSession, student: StudentProfile, *, limit: int = 8
) -> list[dict[str, Any]]:
    """Readiness for every active role, best first - powers 'roles you fit'."""
    held = await load_held_skills(db, student.id)
    roles = (
        await db.execute(
            select(JobRole)
            .where(JobRole.is_active.is_(True))
            .options(selectinload(JobRole.required_skills).selectinload(RoleSkill.skill))
        )
    ).scalars().all()

    scored: list[dict[str, Any]] = []
    for role in roles:
        requirements = [
            Requirement(
                skill_id=str(rs.skill_id),
                skill_name=rs.skill.name if rs.skill else "",
                required_level=rs.required_level,
                importance=rs.importance,
                weight=rs.weight,
                demand_score=rs.skill.demand_score if rs.skill else 0.0,
                slug=rs.skill.slug if rs.skill else "",
            )
            for rs in role.required_skills
        ]
        if not requirements:
            continue
        result = skill_gap.analyse(
            held, requirements, job_role_id=str(role.id), job_role_title=role.title
        )
        scored.append(
            {
                "job_role_id": role.id,
                "title": role.title,
                "family": role.family,
                "readiness_score": result.readiness_score,
                "gap_percentage": result.gap_percentage,
                "matched_count": result.matched_count,
                "total_required": result.total_required,
                "top_missing": [i.skill_name for i in result.missing[:3]],
                "demand_index": role.demand_index,
            }
        )
    scored.sort(key=lambda r: (-r["readiness_score"], -r["demand_index"]))
    return scored[:limit]


async def refresh_student_readiness(
    db: AsyncSession, student: StudentProfile
) -> float:
    """Recompute the headline readiness score against the student's target role."""
    if not student.target_job_role_id:
        # No target chosen: use the best-fitting role as a proxy so the
        # dashboard still shows something meaningful and honest.
        ranked = await compute_all_role_readiness(db, student, limit=1)
        score = ranked[0]["readiness_score"] if ranked else 0.0
    else:
        role = await db.get(JobRole, student.target_job_role_id)
        if role is None:
            return student.skill_readiness_score
        result = await compute_skill_gap(db, student, role)
        score = result.readiness_score
    student.skill_readiness_score = score
    student.readiness_computed_at = _now()
    await db.flush()
    return score


# ------------------------------------------------------- demand signal -----
async def refresh_skill_demand(db: AsyncSession) -> int:
    """Recompute ``Skill.demand_score`` from live postings.

    Demand is the share of published opportunities requiring a skill, scaled to
    0-100. This is what makes the platform 'industry-aware': the taxonomy's
    notion of what matters follows what employers actually ask for.
    """
    from app.models.enums import OpportunityStatus

    total = (
        await db.execute(
            select(func.count())
            .select_from(Opportunity)
            .where(
                Opportunity.status == OpportunityStatus.PUBLISHED,
                Opportunity.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    if not total:
        return 0

    counts = (
        await db.execute(
            select(OpportunitySkill.skill_id, func.count(OpportunitySkill.id))
            .join(Opportunity, Opportunity.id == OpportunitySkill.opportunity_id)
            .where(
                Opportunity.status == OpportunityStatus.PUBLISHED,
                Opportunity.deleted_at.is_(None),
            )
            .group_by(OpportunitySkill.skill_id)
        )
    ).all()
    by_skill = dict(counts)
    peak = max(by_skill.values(), default=0)
    if not peak:
        return 0

    skills = (await db.execute(select(Skill))).scalars().all()
    updated = 0
    for skill in skills:
        observed = by_skill.get(skill.id, 0)
        market = round(observed / peak * 100, 1)
        # Blend with the catalogue's prior so a young deployment with few
        # postings does not zero out well-known skills.
        blended = round(0.6 * skill.demand_score + 0.4 * market, 1)
        if abs(blended - skill.demand_score) > 0.05:
            skill.demand_score = blended
            updated += 1
    await db.flush()
    log.info("skills.demand_refreshed", skills_updated=updated, postings=total)
    return updated
