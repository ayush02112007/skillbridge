"""Skill assessment endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import ActiveUser, AdminUser, CurrentStudent, DbSession
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.assessment import (
    Assessment,
    AssessmentAttempt,
    AssessmentOption,
    AssessmentQuestion,
)
from app.models.enums import AssessmentType, AttemptStatus, AuditAction
from app.models.skill import JobRole, Skill
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentListItem,
    AssessmentOut,
    AssessmentUpdate,
    AttemptResultOut,
    AttemptStartOut,
    AttemptSubmitIn,
    AttemptSummaryOut,
    OptionForAttempt,
    QuestionForAttempt,
)
from app.schemas.common import (
    Envelope,
    ErrorResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.schemas.skill import SkillBrief
from app.services import assessment as assessment_service
from app.services import audit
from app.services import student as student_service
from app.services.auth import unique_slug

router = APIRouter(prefix="/assessments", tags=["Assessments"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Not allowed in the current state"},
}


@router.get(
    "",
    response_model=Page[AssessmentListItem],
    summary="Browse assessments",
    description=(
        "Available assessments, filterable by type, domain or target role. "
        "For a signed-in student each row also reports attempts used, best "
        "score so far and whether another attempt is allowed."
    ),
)
async def list_assessments(
    db: DbSession,
    user: ActiveUser,
    page: Annotated[PaginationParams, Depends(pagination)],
    q: str | None = None,
    assessment_type: AssessmentType | None = None,
    domain: str | None = None,
    job_role_id: uuid.UUID | None = None,
    skill_id: uuid.UUID | None = None,
) -> Page[AssessmentListItem]:
    stmt = (
        select(Assessment)
        .where(Assessment.is_published.is_(True))
        .options(
            selectinload(Assessment.questions), selectinload(Assessment.job_role)
        )
    )
    if q:
        stmt = stmt.where(func.lower(Assessment.title).like(f"%{q.lower().strip()}%"))
    if assessment_type:
        stmt = stmt.where(Assessment.assessment_type == assessment_type)
    if domain:
        stmt = stmt.where(Assessment.domain == domain)
    if job_role_id:
        stmt = stmt.where(Assessment.job_role_id == job_role_id)
    if skill_id:
        stmt = stmt.where(
            Assessment.id.in_(
                select(AssessmentQuestion.assessment_id).where(
                    AssessmentQuestion.skill_id == skill_id
                )
            )
        )

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Assessment.title).offset(page.offset).limit(page.limit)
        )
    ).scalars().all()

    # Attempt history for the signed-in student, if they are one.
    history: dict[uuid.UUID, list[AssessmentAttempt]] = {}
    from app.models.profile import StudentProfile

    profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == user.id))
    ).scalar_one_or_none()
    if profile is not None and rows:
        attempts = (
            await db.execute(
                select(AssessmentAttempt).where(
                    AssessmentAttempt.student_id == profile.id,
                    AssessmentAttempt.assessment_id.in_([r.id for r in rows]),
                )
            )
        ).scalars().all()
        for attempt in attempts:
            history.setdefault(attempt.assessment_id, []).append(attempt)

    items = []
    for row in rows:
        attempts = history.get(row.id, [])
        finished = [a for a in attempts if a.status != AttemptStatus.IN_PROGRESS]
        best = max((a.percentage for a in finished), default=None)
        items.append(
            AssessmentListItem(
                id=row.id, title=row.title, slug=row.slug, description=row.description,
                assessment_type=row.assessment_type, domain=row.domain,
                duration_minutes=row.duration_minutes, passing_score=row.passing_score,
                question_count=len([q for q in row.questions if q.is_active]),
                job_role_title=row.job_role.title if row.job_role else None,
                attempts_used=len(finished), max_attempts=row.max_attempts,
                best_percentage=best,
                can_attempt=len(finished) < row.max_attempts,
            )
        )
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/my-attempts",
    response_model=Page[AttemptSummaryOut],
    responses=ERRORS,
    summary="My assessment history",
)
async def my_attempts(
    student: CurrentStudent,
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
) -> Page[AttemptSummaryOut]:
    stmt = (
        select(AssessmentAttempt)
        .where(AssessmentAttempt.student_id == student.id)
        .options(selectinload(AssessmentAttempt.assessment))
        .order_by(AssessmentAttempt.created_at.desc())
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(stmt.offset(page.offset).limit(page.limit))
    ).scalars().all()
    return Page.build(
        [
            AttemptSummaryOut(
                id=r.id, assessment_id=r.assessment_id,
                assessment_title=r.assessment.title if r.assessment else "",
                attempt_number=r.attempt_number, status=r.status,
                percentage=r.percentage, is_passed=r.is_passed,
                started_at=r.started_at, submitted_at=r.submitted_at,
            )
            for r in rows
        ],
        total, page.page, page.page_size,
    )


@router.get(
    "/{assessment_id}",
    response_model=Envelope[AssessmentOut],
    responses=ERRORS,
    summary="Assessment detail",
    description="Metadata and the skills covered. Questions are only served "
                "once an attempt has been started.",
)
async def get_assessment(assessment_id: uuid.UUID, db: DbSession, _user: ActiveUser) -> dict:
    row = await assessment_service.get_assessment_or_404(
        db, assessment_id, with_questions=True
    )
    covered = {q.skill.id: q.skill for q in row.questions if q.skill}
    data = AssessmentOut.model_validate(row)
    data.question_count = len([q for q in row.questions if q.is_active])
    data.skills_covered = [SkillBrief.model_validate(s) for s in covered.values()]
    return ok(data)


@router.post(
    "/{assessment_id}/attempts",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[AttemptStartOut],
    responses=ERRORS,
    summary="Start an attempt",
    description=(
        "Creates an attempt and returns the questions in a fixed order, without "
        "correct answers. Re-calling while an attempt is live returns the same "
        "attempt instead of creating a second one, so a refresh never costs an "
        "attempt."
    ),
)
async def start_attempt(
    assessment_id: uuid.UUID, student: CurrentStudent, db: DbSession
) -> dict:
    assessment = await assessment_service.get_assessment_or_404(
        db, assessment_id, with_questions=True
    )
    attempt, questions = await assessment_service.start_attempt(db, assessment, student)
    await db.commit()
    return ok(
        AttemptStartOut(
            attempt_id=attempt.id,
            assessment_id=assessment.id,
            assessment_title=assessment.title,
            attempt_number=attempt.attempt_number,
            status=attempt.status,
            started_at=attempt.started_at,
            expires_at=attempt.expires_at,
            duration_minutes=assessment.duration_minutes,
            total_questions=len(questions),
            questions=[
                QuestionForAttempt(
                    id=q.id, prompt=q.prompt, code_snippet=q.code_snippet,
                    question_type=q.question_type, difficulty=q.difficulty,
                    skill_id=q.skill_id, skill_name=q.skill.name if q.skill else "",
                    subskill=q.subskill, weight=q.weight, display_order=index,
                    options=[
                        OptionForAttempt(
                            id=o.id, label=o.label, display_order=o.display_order
                        )
                        for o in sorted(q.options, key=lambda o: o.display_order)
                    ],
                )
                for index, q in enumerate(questions)
            ],
        )
    )


@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=Envelope[AttemptResultOut],
    responses=ERRORS,
    summary="Submit an attempt",
    description=(
        "Scores the attempt, returns a per-skill breakdown with explanations, "
        "and writes the measured levels back into the student's skill profile "
        "(which in turn refreshes readiness and recommendations).\n\n"
        "Submissions after the time limit are recorded but score zero and do "
        "not alter the skill profile."
    ),
)
async def submit_attempt(
    attempt_id: uuid.UUID,
    payload: AttemptSubmitIn,
    request: Request,
    student: CurrentStudent,
    db: DbSession,
) -> dict:
    attempt = (
        await db.execute(
            select(AssessmentAttempt)
            .where(AssessmentAttempt.id == attempt_id)
            .options(selectinload(AssessmentAttempt.assessment))
        )
    ).scalar_one_or_none()
    if attempt is None:
        raise NotFoundError("Attempt not found", code="ATTEMPT_NOT_FOUND")
    if attempt.student_id != student.id:
        raise PermissionDeniedError(
            "This attempt belongs to another student", code="ATTEMPT_NOT_OWNED"
        )

    await assessment_service.submit_attempt(
        db, attempt, [a.model_dump() for a in payload.answers], student
    )
    await student_service.compute_profile_completion(db, student)
    await student_service.evaluate_badges(db, student)
    await audit.record(
        db, AuditAction.ASSESSMENT_SUBMIT, actor=student.user, resource_type="assessment_attempt",
        resource_id=attempt.id,
        description=f"Scored {attempt.percentage}% on {attempt.assessment.title}",
        request=request,
    )
    await db.commit()
    report = await assessment_service.attempt_report(db, attempt)
    return ok(AttemptResultOut.model_validate(report))


@router.get(
    "/attempts/{attempt_id}",
    response_model=Envelope[AttemptResultOut],
    responses=ERRORS,
    summary="Attempt result",
    description="The full result, including which answers were wrong and why.",
)
async def get_attempt(
    attempt_id: uuid.UUID, student: CurrentStudent, db: DbSession
) -> dict:
    attempt = (
        await db.execute(
            select(AssessmentAttempt)
            .where(AssessmentAttempt.id == attempt_id)
            .options(selectinload(AssessmentAttempt.assessment))
        )
    ).scalar_one_or_none()
    if attempt is None:
        raise NotFoundError("Attempt not found", code="ATTEMPT_NOT_FOUND")
    if attempt.student_id != student.id:
        raise PermissionDeniedError(
            "This attempt belongs to another student", code="ATTEMPT_NOT_OWNED"
        )
    report = await assessment_service.attempt_report(db, attempt)
    return ok(AttemptResultOut.model_validate(report))


# ------------------------------------------------------------- authoring ---
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[AssessmentOut],
    responses=ERRORS,
    summary="Create an assessment",
    description="Platform administrators author assessments, questions and "
                "options in one call.",
)
async def create_assessment(
    payload: AssessmentCreate, db: DbSession, admin: AdminUser
) -> dict:
    if payload.job_role_id and await db.get(JobRole, payload.job_role_id) is None:
        raise NotFoundError("Job role not found", code="JOB_ROLE_NOT_FOUND")

    assessment = Assessment(
        title=payload.title.strip(),
        slug=await unique_slug(db, Assessment, payload.title),
        description=payload.description,
        assessment_type=payload.assessment_type,
        job_role_id=payload.job_role_id,
        primary_skill_id=payload.primary_skill_id,
        domain=payload.domain,
        duration_minutes=payload.duration_minutes,
        passing_score=payload.passing_score,
        max_attempts=payload.max_attempts,
        cooldown_hours=payload.cooldown_hours,
        shuffle_questions=payload.shuffle_questions,
        is_published=payload.is_published,
        created_by_id=admin.id,
    )
    db.add(assessment)
    await db.flush()

    for order, question in enumerate(payload.questions):
        if await db.get(Skill, question.skill_id) is None:
            raise NotFoundError(
                f"Skill {question.skill_id} not found", code="SKILL_NOT_FOUND"
            )
        row = AssessmentQuestion(
            assessment_id=assessment.id,
            skill_id=question.skill_id,
            subskill=question.subskill,
            question_type=question.question_type,
            prompt=question.prompt,
            code_snippet=question.code_snippet,
            difficulty=question.difficulty,
            weight=question.weight,
            explanation=question.explanation,
            display_order=question.display_order or order,
        )
        db.add(row)
        await db.flush()
        for option_order, option in enumerate(question.options):
            db.add(
                AssessmentOption(
                    question_id=row.id, label=option.label, is_correct=option.is_correct,
                    proficiency_value=option.proficiency_value,
                    display_order=option.display_order or option_order,
                )
            )
    await db.commit()

    reloaded = await assessment_service.get_assessment_or_404(
        db, assessment.id, with_questions=True
    )
    data = AssessmentOut.model_validate(reloaded)
    data.question_count = len(reloaded.questions)
    return ok(data)


@router.patch(
    "/{assessment_id}",
    response_model=Envelope[AssessmentOut],
    responses=ERRORS,
    summary="Update an assessment",
)
async def update_assessment(
    assessment_id: uuid.UUID, payload: AssessmentUpdate, db: DbSession, _admin: AdminUser
) -> dict:
    row = await assessment_service.get_assessment_or_404(db, assessment_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await db.commit()
    reloaded = await assessment_service.get_assessment_or_404(
        db, assessment_id, with_questions=True
    )
    data = AssessmentOut.model_validate(reloaded)
    data.question_count = len(reloaded.questions)
    return ok(data)
