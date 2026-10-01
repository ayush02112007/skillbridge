"""Explainable recommendation generation.

Every recommendation carries its full derivation: the match score, each
contributing factor, the skills already met, the skills still missing, the
reasons in plain language, and concrete next steps. Nothing is a black box, and
nothing here makes a decision on anyone's behalf.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai import matching, skill_gap
from app.ai.learning_path import build_plan
from app.ai.scoring import Requirement
from app.ai.service import get_ai_service
from app.core.logging import get_logger
from app.models.enums import OpportunityStatus, OpportunityType
from app.models.learning import LearningProgram, ProgramSkill
from app.models.mentorship import MentorProfile
from app.models.opportunity import Opportunity, OpportunitySkill
from app.models.profile import StudentProfile
from app.models.recommendation import Recommendation
from app.models.skill import JobRole, RoleSkill, Skill, StudentSkill
from app.services import skill as skill_service

log = get_logger("ai.recommender")

RECOMMENDATION_TTL_HOURS = 12
DEFAULT_LIMIT = 10


def _now() -> datetime:
    return datetime.now(UTC)


async def _publish(
    db: AsyncSession,
    user_id: uuid.UUID,
    recommendation_type: str,
    rows: list[dict[str, Any]],
) -> list[Recommendation]:
    """Upsert a freshly computed set, replacing the previous generation."""
    existing = {
        (r.recommendation_type, r.target_id): r
        for r in (
            await db.execute(
                select(Recommendation).where(
                    Recommendation.user_id == user_id,
                    Recommendation.recommendation_type == recommendation_type,
                )
            )
        ).scalars()
    }
    produced: list[Recommendation] = []
    seen: set[uuid.UUID] = set()
    expires = _now() + timedelta(hours=RECOMMENDATION_TTL_HOURS)

    for row in rows:
        target_id = row["target_id"]
        seen.add(target_id)
        record = existing.get((recommendation_type, target_id))
        if record is None:
            record = Recommendation(
                user_id=user_id,
                recommendation_type=recommendation_type,
                target_id=target_id,
                computed_at=_now(),
            )
            db.add(record)
        record.target_title = row.get("target_title", "")[:250]
        record.match_score = row["match_score"]
        record.breakdown = row.get("breakdown", {})
        record.matching_skills = row.get("matching_skills", [])
        record.missing_skills = row.get("missing_skills", [])
        record.reasons = row.get("reasons", [])
        record.reason_summary = row.get("reason_summary", "")
        record.next_steps = row.get("next_steps", [])
        record.generated_by = row.get("generated_by", "deterministic")
        record.computed_at = _now()
        record.expires_at = expires
        produced.append(record)

    # Drop stale entries that no longer qualify, unless the user dismissed them
    # (keeping those prevents a dismissed item reappearing on every refresh).
    for (_kind, target_id), record in existing.items():
        if target_id not in seen and not record.is_dismissed:
            await db.delete(record)

    await db.flush()
    return produced


# ------------------------------------------------- opportunity matching ----
async def recommend_opportunities(
    db: AsyncSession,
    student: StudentProfile,
    *,
    opportunity_type: OpportunityType | None = None,
    limit: int = DEFAULT_LIMIT,
    min_score: float = 25.0,
    persist: bool = True,
    explain_with_llm: bool = False,
) -> list[dict[str, Any]]:
    """Rank open opportunities for one student."""
    entity = Opportunity
    stmt = (
        select(entity)
        .where(
            entity.status == OpportunityStatus.PUBLISHED,
            entity.deleted_at.is_(None),
            or_(
                entity.application_deadline.is_(None),
                entity.application_deadline >= _now(),
            ),
        )
        .options(
            selectinload(entity.company),
            selectinload(entity.job_role),
            selectinload(entity.skills).selectinload(OpportunitySkill.skill),
        )
    )
    if opportunity_type:
        stmt = stmt.where(entity.opportunity_type == opportunity_type)
    else:
        stmt = stmt.where(
            entity.opportunity_type != OpportunityType.FACULTY_OPPORTUNITY
        )
    # Bound the working set: recommendations run over recent open postings.
    stmt = stmt.order_by(entity.published_at.desc().nullslast()).limit(400)
    opportunities = (await db.execute(stmt)).scalars().all()
    if not opportunities:
        return []

    candidate = await skill_service.build_candidate_snapshot(db, student)
    # Exclude anything already applied to - a recommendation to reapply is noise.
    from app.models.application import Application

    applied = set(
        (
            await db.execute(
                select(Application.opportunity_id).where(
                    Application.student_id == student.id
                )
            )
        ).scalars()
    )

    scored: list[tuple[Opportunity, matching.MatchResult]] = []
    for opportunity in opportunities:
        if opportunity.id in applied:
            continue
        snapshot = await skill_service.build_opportunity_snapshot(db, opportunity)
        if not snapshot.requirements:
            continue
        result = matching.match(candidate, snapshot)
        if result.match_score >= min_score and result.is_eligible:
            scored.append((opportunity, result))

    scored.sort(key=lambda pair: -pair[1].match_score)
    scored = scored[:limit]

    service = get_ai_service()
    rows: list[dict[str, Any]] = []
    for opportunity, result in scored:
        summary, generated_by = result.reason_summary, "deterministic"
        if explain_with_llm:
            summary, generated_by = await service.explain_recommendation(
                opportunity_title=opportunity.title,
                company_name=opportunity.company.name if opportunity.company else "",
                match_score=result.match_score,
                matching_skills=result.matching_skills,
                missing_skills=result.missing_skills,
                deterministic_summary=result.reason_summary,
            )
        rows.append(
            {
                "target_id": opportunity.id,
                "target_title": opportunity.title,
                "opportunity_type": opportunity.opportunity_type.value,
                "company_name": opportunity.company.name if opportunity.company else "",
                "company_id": opportunity.company_id,
                "location_city": opportunity.location_city,
                "work_mode": opportunity.work_mode.value,
                "application_deadline": opportunity.application_deadline,
                "match_score": result.match_score,
                "breakdown": result.breakdown,
                "contributions": result.contributions,
                "matching_skills": result.matching_skills,
                "missing_skills": result.missing_skills,
                "reasons": result.reasons,
                "reason_summary": summary,
                "next_steps": result.next_steps,
                "generated_by": generated_by,
            }
        )

    if persist and rows:
        kind = opportunity_type.value if opportunity_type else "OPPORTUNITY"
        await _publish(db, student.user_id, kind, rows)
    return rows


# ------------------------------------------------------- career targets ----
async def recommend_career_roles(
    db: AsyncSession, student: StudentProfile, *, limit: int = 5, persist: bool = True
) -> list[dict[str, Any]]:
    """Which roles is this student closest to, and what is missing for each."""
    held = await skill_service.load_held_skills(db, student.id)
    roles = (
        await db.execute(
            select(JobRole)
            .where(JobRole.is_active.is_(True))
            .options(selectinload(JobRole.required_skills).selectinload(RoleSkill.skill))
        )
    ).scalars().all()

    rows: list[dict[str, Any]] = []
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
        gap = skill_gap.analyse(
            held, requirements, job_role_id=str(role.id), job_role_title=role.title
        )
        # Blend fit with market demand so we do not steer everyone at a dead end.
        score = round(gap.readiness_score * 0.8 + role.demand_index * 0.2, 1)
        rows.append(
            {
                "target_id": role.id,
                "target_title": role.title,
                "family": role.family,
                "match_score": min(100.0, score),
                "readiness_score": gap.readiness_score,
                "demand_index": role.demand_index,
                "salary_range": [role.avg_salary_min, role.avg_salary_max],
                "breakdown": {
                    "readiness": gap.readiness_score / 100,
                    "market_demand": role.demand_index / 100,
                },
                "matching_skills": [i.skill_name for i in gap.strong],
                "missing_skills": [i.skill_name for i in gap.missing[:6]],
                "reasons": [
                    f"You meet {gap.matched_count} of {gap.total_required} core "
                    f"requirements for {role.title}",
                    f"Market demand for this role is {role.demand_index:.0f}/100",
                ],
                "reason_summary": gap.summary,
                "next_steps": [
                    f"Build {item.skill_name} to {item.required_level.lower()}"
                    for item in gap.priority_skills[:3]
                ],
                "generated_by": "deterministic",
            }
        )

    rows.sort(key=lambda r: -r["match_score"])
    rows = rows[:limit]
    if persist and rows:
        await _publish(db, student.user_id, "CAREER_ROLE", rows)
    return rows


# ------------------------------------------------------------- learning ----
async def recommend_learning(
    db: AsyncSession,
    student: StudentProfile,
    *,
    job_role_id: uuid.UUID | None = None,
    limit: int = DEFAULT_LIMIT,
    persist: bool = True,
) -> list[dict[str, Any]]:
    """Programmes that close the student's highest-priority skill gaps."""
    role_id = job_role_id or student.target_job_role_id
    priority_skill_ids: list[uuid.UUID] = []
    role_title = "your target role"

    if role_id:
        role = await db.get(JobRole, role_id)
        if role is not None:
            role_title = role.title
            gap = await skill_service.compute_skill_gap(db, student, role, persist=False)
            priority_skill_ids = [
                uuid.UUID(item.skill_id) for item in gap.priority_skills
            ]
    if not priority_skill_ids:
        # No target: fall back to the most in-demand skills the student lacks.
        held_ids = set(
            (
                await db.execute(
                    select(StudentSkill.skill_id).where(
                        StudentSkill.student_id == student.id
                    )
                )
            ).scalars()
        )
        priority_skill_ids = [
            s.id
            for s in (
                await db.execute(
                    select(Skill)
                    .where(Skill.is_active.is_(True), Skill.id.notin_(held_ids or [uuid.uuid4()]))
                    .order_by(Skill.demand_score.desc())
                    .limit(8)
                )
            ).scalars()
        ]
    if not priority_skill_ids:
        return []

    programs = (
        await db.execute(
            select(LearningProgram)
            .join(ProgramSkill, ProgramSkill.program_id == LearningProgram.id)
            .where(
                LearningProgram.is_published.is_(True),
                LearningProgram.deleted_at.is_(None),
                ProgramSkill.skill_id.in_(priority_skill_ids),
            )
            .options(
                selectinload(LearningProgram.skills).selectinload(ProgramSkill.skill),
                selectinload(LearningProgram.company),
            )
            .distinct()
            .limit(200)
        )
    ).scalars().all()

    # Already-enrolled programmes are not recommendations.
    from app.models.learning import Enrollment

    enrolled = set(
        (
            await db.execute(
                select(Enrollment.program_id).where(Enrollment.student_id == student.id)
            )
        ).scalars()
    )

    priority_rank = {sid: index for index, sid in enumerate(priority_skill_ids)}
    rows: list[dict[str, Any]] = []
    for program in programs:
        if program.id in enrolled:
            continue
        covered = [
            ps for ps in program.skills if ps.skill_id in priority_rank
        ]
        if not covered:
            continue
        # Earlier priorities are worth more; more coverage is worth more.
        score = 0.0
        for ps in covered:
            rank = priority_rank[ps.skill_id]
            score += max(10.0, 100.0 - rank * 12) * ps.coverage_weight
        score = min(100.0, round(score / max(1, len(priority_skill_ids)) * 2.2, 1))
        names = [ps.skill.name for ps in covered if ps.skill]
        rows.append(
            {
                "target_id": program.id,
                "target_title": program.title,
                "program_type": program.program_type.value,
                "provider": program.provider_name
                or (program.company.name if program.company else ""),
                "duration_hours": program.duration_hours,
                "is_free": program.is_free,
                "difficulty": program.difficulty.value,
                "match_score": score,
                "breakdown": {
                    "gap_coverage": round(len(covered) / max(1, len(priority_skill_ids)), 3)
                },
                "matching_skills": names,
                "missing_skills": [],
                "reasons": [
                    f"Covers {', '.join(names[:3])}, which sits in your top skill "
                    f"gaps for {role_title}",
                    f"About {program.duration_hours} hours"
                    + (" and free to enrol" if program.is_free else ""),
                ],
                "reason_summary": (
                    f"{program.title} directly addresses "
                    f"{', '.join(names[:2])} - among the skills standing between "
                    f"you and {role_title}."
                ),
                "next_steps": [f"Enrol and complete {program.title}"],
                "generated_by": "deterministic",
            }
        )

    rows.sort(key=lambda r: -r["match_score"])
    rows = rows[:limit]
    if persist and rows:
        await _publish(db, student.user_id, "LEARNING", rows)
    return rows


# -------------------------------------------------------------- mentors ----
async def recommend_mentors(
    db: AsyncSession, student: StudentProfile, *, limit: int = 6, persist: bool = True
) -> list[dict[str, Any]]:
    """Mentors whose expertise overlaps the student's gaps and interests."""
    role_id = student.target_job_role_id
    priority_skill_ids: set[str] = set()
    role_title = "your target role"
    if role_id:
        role = await db.get(JobRole, role_id)
        if role is not None:
            role_title = role.title
            gap = await skill_service.compute_skill_gap(db, student, role, persist=False)
            priority_skill_ids = {item.skill_id for item in gap.priority_skills}

    mentors = (
        await db.execute(
            select(MentorProfile)
            .where(MentorProfile.is_accepting_requests.is_(True))
            .options(selectinload(MentorProfile.user))
            .limit(200)
        )
    ).scalars().all()

    interests = {str(i).lower() for i in (student.career_interests or [])}
    interests |= {str(r).lower() for r in (student.preferred_roles or [])}

    rows: list[dict[str, Any]] = []
    for mentor in mentors:
        expertise = {str(s) for s in (mentor.expertise_skill_ids or [])}
        overlap = expertise & priority_skill_ids
        topic_hit = any(
            str(t).lower() in interests or any(i in str(t).lower() for i in interests)
            for t in (mentor.topics or [])
        )
        if not overlap and not topic_hit:
            continue

        score = min(
            100.0,
            len(overlap) * 22
            + (20 if topic_hit else 0)
            + min(20, mentor.experience_years * 2)
            + (10 if mentor.rating >= 4 else 0),
        )
        reasons = []
        if overlap:
            reasons.append(
                f"Their expertise covers {len(overlap)} of the skills you need for "
                f"{role_title}"
            )
        if topic_hit:
            reasons.append("They mentor on topics you said you are interested in")
        if mentor.experience_years:
            reasons.append(f"{mentor.experience_years} years of industry experience")

        rows.append(
            {
                "target_id": mentor.id,
                "target_title": mentor.user.full_name if mentor.user else "Mentor",
                "headline": mentor.headline,
                "designation": mentor.designation,
                "industry": mentor.industry,
                "experience_years": mentor.experience_years,
                "rating": mentor.rating,
                "match_score": round(float(score), 1),
                "breakdown": {
                    "skill_overlap": round(
                        len(overlap) / max(1, len(priority_skill_ids)), 3
                    ),
                    "topic_alignment": 1.0 if topic_hit else 0.0,
                },
                "matching_skills": sorted(overlap),
                "missing_skills": [],
                "reasons": reasons,
                "reason_summary": (
                    f"{mentor.user.full_name if mentor.user else 'This mentor'} works on "
                    f"the exact skills you are trying to build for {role_title}."
                ),
                "next_steps": ["Send a mentorship request with a specific question"],
                "generated_by": "deterministic",
            }
        )

    rows.sort(key=lambda r: -r["match_score"])
    rows = rows[:limit]
    if persist and rows:
        await _publish(db, student.user_id, "MENTOR", rows)
    return rows


# ---------------------------------------------------------------- skills ---
async def recommend_skills(
    db: AsyncSession, student: StudentProfile, *, limit: int = 8
) -> list[dict[str, Any]]:
    """Which skills to build next, weighted by gap priority and market demand."""
    held_ids = set(
        (
            await db.execute(
                select(StudentSkill.skill_id).where(StudentSkill.student_id == student.id)
            )
        ).scalars()
    )

    # Demand across currently published postings is the market signal.
    demand_rows = (
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
    postings_by_skill = dict(demand_rows)

    gap_priority: dict[uuid.UUID, int] = {}
    role_title = None
    if student.target_job_role_id:
        role = await db.get(JobRole, student.target_job_role_id)
        if role is not None:
            role_title = role.title
            gap = await skill_service.compute_skill_gap(db, student, role, persist=False)
            gap_priority = {
                uuid.UUID(item.skill_id): item.priority for item in gap.priority_skills
            }

    candidates = (
        await db.execute(
            select(Skill)
            .where(Skill.is_active.is_(True))
            .options(selectinload(Skill.category))
        )
    ).scalars().all()

    rows: list[dict[str, Any]] = []
    for skill in candidates:
        if skill.id in held_ids and skill.id not in gap_priority:
            continue
        postings = postings_by_skill.get(skill.id, 0)
        priority = gap_priority.get(skill.id)
        score = skill.demand_score * 0.5 + min(40.0, postings * 8)
        if priority is not None:
            score += max(0, 60 - priority * 8)
        if skill.is_trending:
            score += 5
        if not score:
            continue

        reasons = []
        if priority is not None and role_title:
            reasons.append(f"Priority {priority} gap for {role_title}")
        if postings:
            reasons.append(f"Required by {postings} open posting(s) on the platform")
        if skill.is_trending:
            reasons.append("Trending in the wider market")
        if skill.demand_score:
            reasons.append(
                f"Market demand score {skill.demand_score:.0f}/100 for this skill"
            )
        if skill.id in held_ids:
            reasons.append("Already on your profile - deepening it closes a gap")
        # The explainability contract: never surface a recommendation that
        # cannot say why it is there.
        if not reasons:
            continue
        rows.append(
            {
                "skill_id": skill.id,
                "skill_name": skill.name,
                "category": skill.category.name if skill.category else "",
                "demand_score": skill.demand_score,
                "open_postings": postings,
                "gap_priority": priority,
                "already_held": skill.id in held_ids,
                "score": round(min(100.0, score), 1),
                "reasons": reasons,
            }
        )

    rows.sort(key=lambda r: -r["score"])
    return rows[:limit]


# --------------------------------------------------------- learning path ---
async def generate_learning_path(
    db: AsyncSession,
    student: StudentProfile,
    job_role: JobRole,
    *,
    hours_per_week: int = 8,
) -> dict[str, Any]:
    """A concrete, ordered plan to close the gap for a target role."""
    gap = await skill_service.compute_skill_gap(db, student, job_role, persist=False)

    skill_ids = [uuid.UUID(i.skill_id) for i in gap.items if i.status != "STRONG"]
    programs_by_skill: dict[str, list[dict[str, Any]]] = {}
    if skill_ids:
        rows = (
            await db.execute(
                select(ProgramSkill)
                .join(LearningProgram, LearningProgram.id == ProgramSkill.program_id)
                .where(
                    ProgramSkill.skill_id.in_(skill_ids),
                    LearningProgram.is_published.is_(True),
                    LearningProgram.deleted_at.is_(None),
                )
                .options(selectinload(ProgramSkill.program))
            )
        ).scalars().all()
        for row in rows:
            program = row.program
            if program is None:
                continue
            programs_by_skill.setdefault(str(row.skill_id), []).append(
                {
                    "id": str(program.id),
                    "title": program.title,
                    "provider": program.provider_name or "",
                    "duration_hours": program.duration_hours,
                    "is_free": program.is_free,
                    "program_type": program.program_type.value,
                }
            )

    plan = build_plan(gap, programs_by_skill, hours_per_week=hours_per_week)
    return {
        "job_role_id": job_role.id,
        "job_role_title": job_role.title,
        "readiness_score": gap.readiness_score,
        "gap_percentage": gap.gap_percentage,
        **plan.to_dict(),
        "generated_by": "deterministic",
    }
