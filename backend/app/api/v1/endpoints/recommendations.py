"""Explainable recommendation endpoints.

Design commitments enforced here:

* every response carries `match_score`, `matching_skills`, `missing_skills`,
  `reasons` and a plain-language `reason_summary`;
* scores are produced by the deterministic engine, so they are reproducible and
  auditable - an LLM, when configured, only rewords the summary;
* recommendations never gate access to anything. A student can apply to any
  posting they are eligible for regardless of score.
"""
from __future__ import annotations

import uuid
from datetime import UTC
from typing import Annotated, Any

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.ai import recommender
from app.ai.service import get_ai_service
from app.core.deps import CurrentStudent, DbSession
from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import OpportunityType
from app.models.learning import LearningPath
from app.models.recommendation import Recommendation, RecommendationFeedback
from app.models.skill import JobRole, StudentSkill
from app.schemas.common import Envelope, ErrorResponse, MessageResponse, ok
from app.schemas.recommendation import (
    CareerGuidanceOut,
    CareerRoleRecommendation,
    InterviewPrepOut,
    InterviewQuestionOut,
    LearningPathOut,
    LearningRecommendation,
    MentorRecommendation,
    OpportunityRecommendation,
    RecommendationFeedbackIn,
    SkillRecommendation,
)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
}

EXPLAIN_NOTE = (
    "\n\n**Why this is explainable:** the score is a weighted sum of skill "
    "compatibility, education fit, stated interest, relevant experience, "
    "location preference, certifications and project relevance. The weights are "
    "configuration, not a learned black box, and each factor's contribution is "
    "returned alongside the total."
)


async def _opportunity_recs(
    db, student, opportunity_type: OpportunityType | None, limit: int, explain: bool
) -> list[OpportunityRecommendation]:
    rows = await recommender.recommend_opportunities(
        db, student, opportunity_type=opportunity_type, limit=limit,
        explain_with_llm=explain,
    )
    await db.commit()
    return [OpportunityRecommendation.model_validate(r) for r in rows]


@router.get(
    "/internships",
    response_model=Envelope[list[OpportunityRecommendation]],
    responses=ERRORS,
    summary="Recommended internships",
    description="Open internships ranked by fit for the signed-in student."
                + EXPLAIN_NOTE,
)
async def recommend_internships(
    student: CurrentStudent,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    explain: Annotated[bool, Query(description="Use the configured LLM for the summary")] = False,
) -> dict:
    return ok(
        await _opportunity_recs(db, student, OpportunityType.INTERNSHIP, limit, explain)
    )


@router.get(
    "/jobs",
    response_model=Envelope[list[OpportunityRecommendation]],
    responses=ERRORS,
    summary="Recommended jobs",
    description="Open jobs ranked by fit for the signed-in student." + EXPLAIN_NOTE,
)
async def recommend_jobs(
    student: CurrentStudent,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    explain: bool = False,
) -> dict:
    return ok(await _opportunity_recs(db, student, OpportunityType.JOB, limit, explain))


@router.get(
    "/projects",
    response_model=Envelope[list[OpportunityRecommendation]],
    responses=ERRORS,
    summary="Recommended live projects",
)
async def recommend_projects(
    student: CurrentStudent,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> dict:
    return ok(
        await _opportunity_recs(db, student, OpportunityType.LIVE_PROJECT, limit, False)
    )


@router.get(
    "/careers",
    response_model=Envelope[list[CareerRoleRecommendation]],
    responses=ERRORS,
    summary="Recommended career roles",
    description=(
        "Which roles the student is closest to. Blends readiness (80%) with "
        "market demand (20%) so guidance does not push everyone toward a role "
        "nobody is hiring for."
    ),
)
async def recommend_careers(
    student: CurrentStudent, db: DbSession, limit: Annotated[int, Query(ge=1, le=20)] = 5
) -> dict:
    rows = await recommender.recommend_career_roles(db, student, limit=limit)
    await db.commit()
    return ok([CareerRoleRecommendation.model_validate(r) for r in rows])


@router.get(
    "/learning",
    response_model=Envelope[list[LearningRecommendation]],
    responses=ERRORS,
    summary="Recommended learning programmes",
    description="Programmes chosen because they cover the student's highest "
                "priority skill gaps, not because they are popular.",
)
async def recommend_learning(
    student: CurrentStudent,
    db: DbSession,
    job_role_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=30)] = 10,
) -> dict:
    rows = await recommender.recommend_learning(
        db, student, job_role_id=job_role_id, limit=limit
    )
    await db.commit()
    return ok([LearningRecommendation.model_validate(r) for r in rows])


@router.get(
    "/skills",
    response_model=Envelope[list[SkillRecommendation]],
    responses=ERRORS,
    summary="Recommended skills to build next",
    description="Ranked by gap priority for the target role and by live demand "
                "measured from published postings.",
)
async def recommend_skills(
    student: CurrentStudent, db: DbSession, limit: Annotated[int, Query(ge=1, le=30)] = 8
) -> dict:
    rows = await recommender.recommend_skills(db, student, limit=limit)
    return ok([SkillRecommendation.model_validate(r) for r in rows])


@router.get(
    "/mentors",
    response_model=Envelope[list[MentorRecommendation]],
    responses=ERRORS,
    summary="Recommended mentors",
)
async def recommend_mentors(
    student: CurrentStudent, db: DbSession, limit: Annotated[int, Query(ge=1, le=20)] = 6
) -> dict:
    rows = await recommender.recommend_mentors(db, student, limit=limit)
    await db.commit()
    return ok([MentorRecommendation.model_validate(r) for r in rows])


@router.get(
    "/learning-path",
    response_model=Envelope[LearningPathOut],
    responses=ERRORS,
    summary="Personalised learning path",
    description=(
        "An ordered plan to close the gap for a target role: what to learn, in "
        "what order, why, how long it should take, and which available "
        "programmes cover each step.\n\n"
        "Ordering respects real prerequisites - you are never told to learn "
        "React before JavaScript."
    ),
)
async def learning_path(
    student: CurrentStudent,
    db: DbSession,
    job_role_id: uuid.UUID | None = None,
    hours_per_week: Annotated[int, Query(ge=1, le=60)] = 8,
    save: Annotated[bool, Query(description="Persist the plan to the profile")] = True,
) -> dict:
    role_id = job_role_id or student.target_job_role_id
    if role_id is None:
        raise ValidationError(
            "Choose a target role first, or pass job_role_id", code="NO_TARGET_ROLE"
        )
    role = await db.get(JobRole, role_id)
    if role is None:
        raise NotFoundError("Job role not found", code="JOB_ROLE_NOT_FOUND")

    plan = await recommender.generate_learning_path(
        db, student, role, hours_per_week=hours_per_week
    )

    if save:
        from datetime import datetime

        existing = (
            await db.execute(
                select(LearningPath).where(
                    LearningPath.student_id == student.id,
                    LearningPath.job_role_id == role.id,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            existing = LearningPath(student_id=student.id, job_role_id=role.id)
            db.add(existing)
        existing.title = plan["title"]
        existing.summary = plan["summary"]
        existing.estimated_weeks = plan["estimated_weeks"]
        existing.steps = plan["steps"]
        existing.generated_by = plan["generated_by"]
        existing.generated_at = datetime.now(UTC)
    await db.commit()
    return ok(LearningPathOut.model_validate(plan))


@router.get(
    "/career-guidance",
    response_model=Envelope[CareerGuidanceOut],
    responses=ERRORS,
    summary="Career guidance",
    description="Short, specific guidance for the next month. Uses the "
                "configured LLM when available and a rule-based writer otherwise.",
)
async def career_guidance(student: CurrentStudent, db: DbSession) -> dict:
    from sqlalchemy.orm import selectinload

    top = (
        await db.execute(
            select(StudentSkill)
            .where(StudentSkill.student_id == student.id)
            .options(selectinload(StudentSkill.skill))
            .order_by(StudentSkill.score.desc())
            .limit(6)
        )
    ).scalars().all()
    top_skills = [s.skill.name for s in top if s.skill]

    role_title = None
    readiness = None
    if student.target_job_role_id:
        role = await db.get(JobRole, student.target_job_role_id)
        if role:
            role_title = role.title
            readiness = student.skill_readiness_score

    text, generated_by = await get_ai_service().career_guidance(
        student_name=student.user.full_name if student.user else "",
        top_skills=top_skills,
        interests=list(student.career_interests or []),
        target_role=role_title,
        readiness=readiness,
    )
    return ok(
        CareerGuidanceOut(
            guidance=text, generated_by=generated_by, top_skills=top_skills,
            target_role=role_title, readiness_score=readiness,
        )
    )


@router.get(
    "/interview-prep",
    response_model=Envelope[InterviewPrepOut],
    responses=ERRORS,
    summary="Interview preparation questions",
    description="Practice questions built around the student's strongest skills "
                "and their target role.",
)
async def interview_prep(
    student: CurrentStudent,
    db: DbSession,
    job_role_id: uuid.UUID | None = None,
    count: Annotated[int, Query(ge=3, le=20)] = 8,
) -> dict:
    from sqlalchemy.orm import selectinload

    role_id = job_role_id or student.target_job_role_id
    role = await db.get(JobRole, role_id) if role_id else None
    role_title = role.title if role else "a graduate engineering role"

    top = (
        await db.execute(
            select(StudentSkill)
            .where(StudentSkill.student_id == student.id)
            .options(selectinload(StudentSkill.skill))
            .order_by(StudentSkill.score.desc())
            .limit(6)
        )
    ).scalars().all()
    skills = [s.skill.name for s in top if s.skill]
    if not skills and role is not None:
        skills = [rs.skill.name for rs in role.required_skills[:5] if rs.skill]

    questions, generated_by = await get_ai_service().interview_questions(
        role_title=role_title, skills=skills, count=count
    )
    return ok(
        InterviewPrepOut(
            role_title=role_title,
            questions=[InterviewQuestionOut(**q) for q in questions],
            focus_skills=skills[:6],
            generated_by=generated_by,
        )
    )


@router.post(
    "/{recommendation_id}/feedback",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Give feedback on a recommendation",
    description=(
        "Records an outcome signal (VIEWED, CLICKED, APPLIED, DISMISSED, "
        "IRRELEVANT, HIRED). These signals are what let the engine learn from "
        "real outcomes over time rather than from assumptions."
    ),
)
async def recommendation_feedback(
    recommendation_id: uuid.UUID,
    payload: RecommendationFeedbackIn,
    student: CurrentStudent,
    db: DbSession,
) -> MessageResponse:
    allowed = {"VIEWED", "CLICKED", "APPLIED", "DISMISSED", "IRRELEVANT", "HIRED"}
    signal = payload.signal.upper()
    if signal not in allowed:
        raise ValidationError(
            f"Signal must be one of {', '.join(sorted(allowed))}", code="INVALID_SIGNAL"
        )
    record = await db.get(Recommendation, recommendation_id)
    if record is None or record.user_id != student.user_id:
        raise NotFoundError("Recommendation not found", code="RECOMMENDATION_NOT_FOUND")

    if signal == "DISMISSED":
        record.is_dismissed = True
    if signal == "CLICKED":
        from datetime import datetime

        record.clicked_at = datetime.now(UTC)

    db.add(
        RecommendationFeedback(
            recommendation_id=record.id, user_id=student.user_id, signal=signal,
            comment=payload.comment[:400],
            meta={"recommendation_type": record.recommendation_type},
        )
    )
    await db.commit()
    return MessageResponse(message="Feedback recorded")
