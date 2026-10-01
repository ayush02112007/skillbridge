"""Student profile, completion scoring, badges and dashboard assembly."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.application import Application
from app.models.document import Document
from app.models.enums import (
    ApplicationStatus,
    BadgeCode,
    DocumentType,
    EnrollmentStatus,
    OpportunityStatus,
)
from app.models.learning import Enrollment, StudentCertification
from app.models.opportunity import Opportunity
from app.models.portfolio import Badge, StudentBadge
from app.models.profile import (
    EducationRecord,
    ExperienceRecord,
    StudentProfile,
    StudentProject,
)
from app.models.skill import JobRole, SkillGapAnalysis, StudentSkill
from app.models.user import User
from app.services import skill as skill_service

log = get_logger("students")

# Profile completion weights (must total 100).
COMPLETION_WEIGHTS: dict[str, int] = {
    "basic": 20,
    "education": 20,
    "skills": 20,
    "projects": 15,
    "certifications": 10,
    "experience": 10,
    "resume": 5,
}


def _now() -> datetime:
    return datetime.now(UTC)


async def get_student_or_404(db: AsyncSession, student_id: uuid.UUID) -> StudentProfile:
    profile = (
        await db.execute(
            select(StudentProfile)
            .where(StudentProfile.id == student_id, StudentProfile.deleted_at.is_(None))
            .options(selectinload(StudentProfile.user))
        )
    ).scalar_one_or_none()
    if profile is None:
        raise NotFoundError("Student not found", code="STUDENT_NOT_FOUND")
    return profile


# ------------------------------------------------------ profile completion --
async def compute_profile_completion(
    db: AsyncSession, student: StudentProfile
) -> dict[str, Any]:
    """Score completion and return actionable next steps, not just a number."""
    user = student.user or await db.get(User, student.user_id)

    basic_fields = [
        bool(user and user.full_name),
        bool(user and user.phone),
        bool(student.headline),
        bool(student.bio and len(student.bio) > 40),
        bool(student.city),
        bool(user and user.avatar_url),
    ]
    basic_ratio = sum(basic_fields) / len(basic_fields)

    academic_fields = [
        bool(student.institution_id),
        bool(student.degree),
        bool(student.program_name),
        student.cgpa is not None,
        bool(student.graduation_year),
    ]
    education_count = (
        await db.execute(
            select(func.count())
            .select_from(EducationRecord)
            .where(EducationRecord.student_id == student.id)
        )
    ).scalar_one()
    education_ratio = min(
        1.0,
        (sum(academic_fields) / len(academic_fields)) * 0.6
        + min(1.0, education_count / 2) * 0.4,
    )

    skill_count = (
        await db.execute(
            select(func.count())
            .select_from(StudentSkill)
            .where(StudentSkill.student_id == student.id)
        )
    ).scalar_one()
    # Eight skills is a credible profile; beyond that it is diminishing returns.
    skills_ratio = min(1.0, skill_count / 8)

    project_count = (
        await db.execute(
            select(func.count())
            .select_from(StudentProject)
            .where(StudentProject.student_id == student.id)
        )
    ).scalar_one()
    projects_ratio = min(1.0, project_count / 2)

    certification_count = (
        await db.execute(
            select(func.count())
            .select_from(StudentCertification)
            .where(StudentCertification.student_id == student.id)
        )
    ).scalar_one()
    certifications_ratio = min(1.0, certification_count / 1)

    experience_count = (
        await db.execute(
            select(func.count())
            .select_from(ExperienceRecord)
            .where(ExperienceRecord.student_id == student.id)
        )
    ).scalar_one()
    experience_ratio = min(1.0, experience_count / 1)

    resume_count = (
        await db.execute(
            select(func.count())
            .select_from(Document)
            .where(
                Document.owner_id == student.user_id,
                Document.document_type == DocumentType.RESUME,
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    resume_ratio = 1.0 if resume_count else 0.0

    ratios = {
        "basic": basic_ratio,
        "education": education_ratio,
        "skills": skills_ratio,
        "projects": projects_ratio,
        "certifications": certifications_ratio,
        "experience": experience_ratio,
        "resume": resume_ratio,
    }
    sections = [
        {
            "key": key,
            "label": key.replace("_", " ").title(),
            "weight": weight,
            "earned": round(ratios[key] * weight, 1),
            "percentage": round(ratios[key] * 100),
            "is_complete": ratios[key] >= 0.999,
        }
        for key, weight in COMPLETION_WEIGHTS.items()
    ]
    total = round(sum(s["earned"] for s in sections))

    suggestions: list[dict[str, Any]] = []
    if ratios["skills"] < 1:
        suggestions.append(
            {
                "action": f"Add {max(1, 8 - skill_count)} more skills to your profile",
                "impact": round((1 - ratios["skills"]) * COMPLETION_WEIGHTS["skills"]),
                "url": "/student/skills",
            }
        )
    if ratios["resume"] < 1:
        suggestions.append(
            {"action": "Upload your resume", "impact": COMPLETION_WEIGHTS["resume"],
             "url": "/student/documents"}
        )
    if ratios["projects"] < 1:
        suggestions.append(
            {
                "action": "Add a project with what you built and the outcome",
                "impact": round((1 - ratios["projects"]) * COMPLETION_WEIGHTS["projects"]),
                "url": "/student/projects",
            }
        )
    if ratios["experience"] < 1:
        suggestions.append(
            {"action": "Add an internship or work experience",
             "impact": COMPLETION_WEIGHTS["experience"], "url": "/student/profile"}
        )
    if ratios["certifications"] < 1:
        suggestions.append(
            {"action": "Add a certification you have earned",
             "impact": COMPLETION_WEIGHTS["certifications"], "url": "/student/certifications"}
        )
    if ratios["education"] < 1:
        suggestions.append(
            {"action": "Complete your academic details",
             "impact": round((1 - ratios["education"]) * COMPLETION_WEIGHTS["education"]),
             "url": "/student/profile"}
        )
    if ratios["basic"] < 1:
        suggestions.append(
            {"action": "Finish your basic information and headline",
             "impact": round((1 - ratios["basic"]) * COMPLETION_WEIGHTS["basic"]),
             "url": "/student/profile"}
        )
    suggestions.sort(key=lambda s: -s["impact"])

    student.profile_completion = total
    await db.flush()
    return {
        "percentage": total,
        "sections": sections,
        "suggestions": suggestions[:4],
        "counts": {
            "skills": skill_count, "projects": project_count,
            "certifications": certification_count, "experience": experience_count,
            "education": education_count, "documents": resume_count,
        },
    }


# ------------------------------------------------------------------ badges --
async def evaluate_badges(db: AsyncSession, student: StudentProfile) -> list[str]:
    """Award any badge whose criteria are now met. Returns newly awarded codes."""
    awarded_rows = (
        await db.execute(
            select(StudentBadge)
            .where(StudentBadge.student_id == student.id)
            .options(selectinload(StudentBadge.badge))
        )
    ).scalars().all()
    already = {row.badge.code for row in awarded_rows if row.badge}
    catalogue = {b.code: b for b in (await db.execute(select(Badge))).scalars()}
    newly: list[str] = []

    async def _count(model, *where) -> int:
        return (
            await db.execute(select(func.count()).select_from(model).where(*where))
        ).scalar_one()

    checks: dict[BadgeCode, bool] = {}

    checks[BadgeCode.PROFILE_COMPLETE] = student.profile_completion >= 100

    from app.models.assessment import AssessmentAttempt
    from app.models.enums import AttemptStatus

    evaluated = (
        await db.execute(
            select(AssessmentAttempt).where(
                AssessmentAttempt.student_id == student.id,
                AssessmentAttempt.status == AttemptStatus.EVALUATED,
            )
        )
    ).scalars().all()
    checks[BadgeCode.ASSESSMENT_COMPLETED] = bool(evaluated)
    checks[BadgeCode.TOP_SKILL_PERFORMER] = any(a.percentage >= 90 for a in evaluated)

    checks[BadgeCode.FIRST_CERTIFICATION] = bool(
        await _count(StudentCertification, StudentCertification.student_id == student.id)
    )
    checks[BadgeCode.PROJECT_BUILDER] = (
        await _count(StudentProject, StudentProject.student_id == student.id) >= 3
    )
    checks[BadgeCode.INDUSTRY_READY] = student.skill_readiness_score >= 80


    checks[BadgeCode.FIRST_INTERNSHIP] = bool(
        (
            await db.execute(
                select(func.count())
                .select_from(Application)
                .join(Opportunity, Opportunity.id == Application.opportunity_id)
                .where(
                    Application.student_id == student.id,
                    Application.status == ApplicationStatus.SELECTED,
                    Opportunity.opportunity_type == "INTERNSHIP",
                )
            )
        ).scalar_one()
    )

    from app.models.mentorship import MentorshipRequest, MentorshipSession

    completed_sessions = (
        await db.execute(
            select(func.count())
            .select_from(MentorshipSession)
            .join(
                MentorshipRequest,
                MentorshipRequest.id == MentorshipSession.request_id,
            )
            .where(
                MentorshipRequest.student_id == student.id,
                MentorshipSession.status == "COMPLETED",
            )
        )
    ).scalar_one()
    checks[BadgeCode.MENTORSHIP_GRADUATE] = completed_sessions >= 3

    for code, earned in checks.items():
        if earned and code not in already and code in catalogue:
            db.add(
                StudentBadge(
                    student_id=student.id, badge_id=catalogue[code].id, awarded_at=_now()
                )
            )
            newly.append(code.value)
    if newly:
        await db.flush()
        log.info("students.badges_awarded", student_id=str(student.id), badges=newly)
    return newly


# --------------------------------------------------------------- dashboard --
async def build_dashboard(db: AsyncSession, student: StudentProfile) -> dict[str, Any]:
    """Everything the student dashboard shows, in one query batch."""
    completion = await compute_profile_completion(db, student)

    top_skills = (
        await db.execute(
            select(StudentSkill)
            .where(StudentSkill.student_id == student.id)
            .options(selectinload(StudentSkill.skill))
            .order_by(StudentSkill.score.desc())
            .limit(6)
        )
    ).scalars().all()

    gap: dict[str, Any] | None = None
    target_role: JobRole | None = None
    if student.target_job_role_id:
        target_role = await db.get(JobRole, student.target_job_role_id)
        analysis = (
            await db.execute(
                select(SkillGapAnalysis)
                .where(
                    SkillGapAnalysis.student_id == student.id,
                    SkillGapAnalysis.job_role_id == student.target_job_role_id,
                )
                .options(
                    selectinload(SkillGapAnalysis.items),
                    selectinload(SkillGapAnalysis.job_role),
                )
            )
        ).scalar_one_or_none()
        if analysis is None and target_role is not None:
            await skill_service.compute_skill_gap(db, student, target_role)
            await db.flush()
            analysis = (
                await db.execute(
                    select(SkillGapAnalysis)
                    .where(
                        SkillGapAnalysis.student_id == student.id,
                        SkillGapAnalysis.job_role_id == target_role.id,
                    )
                    .options(
                        selectinload(SkillGapAnalysis.items),
                        selectinload(SkillGapAnalysis.job_role),
                    )
                )
            ).scalar_one_or_none()
        if analysis:
            items = sorted(analysis.items, key=lambda i: i.priority)
            gap = {
                "job_role_id": analysis.job_role_id,
                "job_role_title": analysis.job_role.title if analysis.job_role else "",
                "readiness_score": analysis.readiness_score,
                "gap_percentage": analysis.gap_percentage,
                "matched_count": analysis.matched_count,
                "total_required": analysis.total_required,
                "summary": analysis.summary,
                "priority_skills": [
                    {
                        "skill_id": i.skill_id,
                        "skill_name": i.skill.name if i.skill else "",
                        "status": i.status,
                        "current_level": i.current_level.value,
                        "required_level": i.required_level.value,
                        "priority": i.priority,
                    }
                    for i in items
                    if i.status != "STRONG"
                ][:5],
            }

    # Applications by status, for the funnel widget.
    status_rows = (
        await db.execute(
            select(Application.status, func.count())
            .where(Application.student_id == student.id)
            .group_by(Application.status)
        )
    ).all()
    applications_by_status = {
        (s.value if hasattr(s, "value") else str(s)): c for s, c in status_rows
    }

    recent_applications = (
        await db.execute(
            select(Application)
            .where(Application.student_id == student.id)
            .options(
                selectinload(Application.opportunity).selectinload(Opportunity.company)
            )
            .order_by(Application.created_at.desc())
            .limit(5)
        )
    ).scalars().all()

    # Deadlines the student can still act on.
    horizon = _now() + timedelta(days=30)
    applied_ids = (
        await db.execute(
            select(Application.opportunity_id).where(Application.student_id == student.id)
        )
    ).scalars().all()
    deadline_stmt = (
        select(Opportunity)
        .where(
            Opportunity.status == OpportunityStatus.PUBLISHED,
            Opportunity.deleted_at.is_(None),
            Opportunity.application_deadline.isnot(None),
            Opportunity.application_deadline <= horizon,
            Opportunity.application_deadline >= _now(),
        )
        .options(selectinload(Opportunity.company))
        .order_by(Opportunity.application_deadline)
        .limit(5)
    )
    if applied_ids:
        deadline_stmt = deadline_stmt.where(Opportunity.id.notin_(applied_ids))
    upcoming_deadlines = (await db.execute(deadline_stmt)).scalars().all()

    enrollments = (
        await db.execute(
            select(Enrollment)
            .where(Enrollment.student_id == student.id)
            .options(selectinload(Enrollment.program))
            .order_by(Enrollment.last_activity_at.desc().nullslast())
            .limit(4)
        )
    ).scalars().all()

    certification_count = (
        await db.execute(
            select(func.count())
            .select_from(StudentCertification)
            .where(StudentCertification.student_id == student.id)
        )
    ).scalar_one()

    from app.models.assessment import AssessmentAttempt
    from app.models.enums import AttemptStatus

    attempts = (
        await db.execute(
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.student_id == student.id,
                AssessmentAttempt.status == AttemptStatus.EVALUATED,
            )
            .options(selectinload(AssessmentAttempt.assessment))
            .order_by(AssessmentAttempt.submitted_at.desc())
            .limit(5)
        )
    ).scalars().all()

    badges = (
        await db.execute(
            select(StudentBadge)
            .where(StudentBadge.student_id == student.id)
            .options(selectinload(StudentBadge.badge))
            .order_by(StudentBadge.awarded_at.desc())
        )
    ).scalars().all()

    interviews_scheduled = (
        await db.execute(
            select(func.count())
            .select_from(Application)
            .where(
                Application.student_id == student.id,
                Application.status == ApplicationStatus.INTERVIEW,
            )
        )
    ).scalar_one()

    return {
        "profile_completion": completion,
        "skill_readiness_score": student.skill_readiness_score,
        "readiness_computed_at": student.readiness_computed_at,
        "target_role": (
            {"id": target_role.id, "title": target_role.title} if target_role else None
        ),
        "top_skills": [
            {
                "skill_id": s.skill_id,
                "name": s.skill.name if s.skill else "",
                "level": s.level.value,
                "score": s.score,
                "confidence": s.confidence,
                "source": s.source.value,
            }
            for s in top_skills
        ],
        "skill_gap": gap,
        "applications": {
            "total": sum(applications_by_status.values()),
            "by_status": applications_by_status,
            "interviews_scheduled": interviews_scheduled,
            "recent": [
                {
                    "id": a.id,
                    "status": a.status.value,
                    "match_score": a.match_score,
                    "submitted_at": a.submitted_at,
                    "opportunity_id": a.opportunity_id,
                    "opportunity_title": a.opportunity.title if a.opportunity else "",
                    "company_name": (
                        a.opportunity.company.name
                        if a.opportunity and a.opportunity.company
                        else ""
                    ),
                }
                for a in recent_applications
            ],
        },
        "upcoming_deadlines": [
            {
                "id": o.id,
                "title": o.title,
                "company_name": o.company.name if o.company else "",
                "type": o.opportunity_type.value,
                "deadline": o.application_deadline,
            }
            for o in upcoming_deadlines
        ],
        "learning": {
            "active_enrollments": sum(
                1
                for e in enrollments
                if e.status in (EnrollmentStatus.ENROLLED, EnrollmentStatus.IN_PROGRESS)
            ),
            "completed": sum(
                1 for e in enrollments if e.status == EnrollmentStatus.COMPLETED
            ),
            "certifications": certification_count,
            "recent": [
                {
                    "id": e.id,
                    "program_id": e.program_id,
                    "title": e.program.title if e.program else "",
                    "progress": e.progress_percentage,
                    "status": e.status.value,
                }
                for e in enrollments
            ],
        },
        "assessments": {
            "completed": len(attempts),
            "recent": [
                {
                    "id": a.id,
                    "assessment_id": a.assessment_id,
                    "title": a.assessment.title if a.assessment else "",
                    "percentage": a.percentage,
                    "is_passed": a.is_passed,
                    "submitted_at": a.submitted_at,
                }
                for a in attempts
            ],
        },
        "badges": [
            {
                "code": b.badge.code.value if b.badge else "",
                "name": b.badge.name if b.badge else "",
                "icon": b.badge.icon if b.badge else "award",
                "awarded_at": b.awarded_at,
            }
            for b in badges
        ],
        "portfolio": {
            "slug": student.portfolio_slug,
            "visibility": student.portfolio_visibility.value,
            "is_published": bool(student.portfolio_slug),
        },
    }
