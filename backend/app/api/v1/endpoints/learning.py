"""Learning programmes, enrolments, progress and certifications."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import (
    CurrentStudent,
    DbSession,
    OptionalUser,
    RecruiterCompanyId,
    RecruiterUser,
)
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.enums import (
    Difficulty,
    EnrollmentStatus,
    ProficiencyLevel,
    ProgramType,
    SkillSource,
)
from app.models.learning import (
    CourseModule,
    Enrollment,
    LearningProgram,
    ModuleProgress,
    ProgramSkill,
    StudentCertification,
)
from app.models.skill import Skill
from app.schemas.common import (
    Envelope,
    ErrorResponse,
    MessageResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.schemas.learning import (
    CertificationIn,
    CertificationOut,
    EnrollmentOut,
    ModuleCompleteIn,
    ModuleOut,
    ProgramCreate,
    ProgramDetail,
    ProgramListItem,
    ProgramUpdate,
)
from app.services import skill as skill_service
from app.services import student as student_service
from app.services.auth import unique_slug

router = APIRouter(prefix="/learning", tags=["Learning"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
}


def _now() -> datetime:
    return datetime.now(UTC)


async def _get_program(db, program_id: uuid.UUID, *, published_only=True) -> LearningProgram:
    row = (
        await db.execute(
            select(LearningProgram)
            .where(LearningProgram.id == program_id, LearningProgram.deleted_at.is_(None))
            .options(
                selectinload(LearningProgram.skills).selectinload(ProgramSkill.skill),
                selectinload(LearningProgram.modules),
                selectinload(LearningProgram.company),
            )
        )
    ).scalar_one_or_none()
    if row is None or (published_only and not row.is_published):
        raise NotFoundError("Programme not found", code="PROGRAM_NOT_FOUND")
    return row


@router.get(
    "/programs",
    response_model=Page[ProgramListItem],
    summary="Browse learning programmes",
    description="Courses, certifications, workshops, bootcamps and training "
                "published by industry partners.",
)
async def list_programs(
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
    user: OptionalUser = None,
    q: str | None = None,
    program_type: ProgramType | None = None,
    difficulty: Difficulty | None = None,
    skill_id: Annotated[list[uuid.UUID] | None, Query()] = None,
    free_only: bool = False,
    company_id: uuid.UUID | None = None,
) -> Page[ProgramListItem]:
    stmt = (
        select(LearningProgram)
        .where(
            LearningProgram.is_published.is_(True),
            LearningProgram.deleted_at.is_(None),
        )
        .options(
            selectinload(LearningProgram.skills).selectinload(ProgramSkill.skill),
            selectinload(LearningProgram.company),
        )
    )
    if q:
        needle = f"%{q.lower().strip()}%"
        stmt = stmt.where(
            or_(
                func.lower(LearningProgram.title).like(needle),
                LearningProgram.search_text.like(needle),
            )
        )
    if program_type:
        stmt = stmt.where(LearningProgram.program_type == program_type)
    if difficulty:
        stmt = stmt.where(LearningProgram.difficulty == difficulty)
    if free_only:
        stmt = stmt.where(LearningProgram.is_free.is_(True))
    if company_id:
        stmt = stmt.where(LearningProgram.provider_company_id == company_id)
    if skill_id:
        stmt = stmt.where(
            LearningProgram.id.in_(
                select(ProgramSkill.program_id).where(
                    ProgramSkill.skill_id.in_(list(skill_id))
                )
            )
        )

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(LearningProgram.enrollment_count.desc(), LearningProgram.title)
            .offset(page.offset)
            .limit(page.limit)
        )
    ).scalars().all()

    enrolled: set[uuid.UUID] = set()
    if user is not None:
        from app.models.profile import StudentProfile

        profile = (
            await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user.id)
            )
        ).scalar_one_or_none()
        if profile is not None and rows:
            enrolled = set(
                (
                    await db.execute(
                        select(Enrollment.program_id).where(
                            Enrollment.student_id == profile.id,
                            Enrollment.program_id.in_([r.id for r in rows]),
                        )
                    )
                ).scalars()
            )

    items = []
    for row in rows:
        item = ProgramListItem.model_validate(row)
        item.is_enrolled = row.id in enrolled
        items.append(item)
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/programs/{program_id}",
    response_model=Envelope[ProgramDetail],
    responses=ERRORS,
    summary="Programme detail",
)
async def get_program(
    program_id: uuid.UUID, db: DbSession, user: OptionalUser = None
) -> dict:
    program = await _get_program(db, program_id)
    detail = ProgramDetail.model_validate(program)
    detail.modules = [ModuleOut.model_validate(m) for m in program.modules]
    return ok(detail)


@router.post(
    "/programs",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[ProgramDetail],
    responses=ERRORS,
    summary="Publish a learning programme",
    description="Industry partners publish training. Tagging the skills a "
                "programme teaches is what lets it be recommended to the "
                "students whose gaps it actually closes.",
)
async def create_program(
    payload: ProgramCreate,
    db: DbSession,
    user: RecruiterUser,
    company_id: RecruiterCompanyId,
) -> dict:
    program = LearningProgram(
        title=payload.title.strip(),
        slug=await unique_slug(db, LearningProgram, payload.title),
        summary=payload.summary,
        description=payload.description,
        program_type=payload.program_type,
        provider_company_id=company_id,
        provider_name=payload.provider_name,
        created_by_id=user.id,
        difficulty=payload.difficulty,
        duration_hours=payload.duration_hours,
        mode=payload.mode,
        price_amount=payload.price_amount,
        currency=payload.currency,
        is_free=payload.price_amount == 0,
        external_url=payload.external_url,
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
        seats=payload.seats,
        grants_certificate=payload.grants_certificate,
        outcomes=payload.outcomes,
        prerequisites=payload.prerequisites,
        is_published=payload.is_published,
    )
    db.add(program)
    await db.flush()

    for entry in payload.skills:
        if await db.get(Skill, entry.skill_id) is None:
            raise NotFoundError(f"Skill {entry.skill_id} not found", code="SKILL_NOT_FOUND")
        db.add(
            ProgramSkill(
                program_id=program.id, skill_id=entry.skill_id,
                target_level=entry.target_level, coverage_weight=entry.coverage_weight,
            )
        )
    for order, module in enumerate(payload.modules):
        db.add(
            CourseModule(
                program_id=program.id, **{**module.model_dump(),
                                          "display_order": module.display_order or order}
            )
        )
    await db.flush()

    skill_names = [
        s.name
        for s in (
            await db.execute(
                select(Skill).where(
                    Skill.id.in_([e.skill_id for e in payload.skills] or [uuid.uuid4()])
                )
            )
        ).scalars()
    ]
    program.search_text = " ".join(
        [program.title, program.summary, program.description, *skill_names]
    ).lower()[:12000]
    await db.commit()

    reloaded = await _get_program(db, program.id, published_only=False)
    detail = ProgramDetail.model_validate(reloaded)
    detail.modules = [ModuleOut.model_validate(m) for m in reloaded.modules]
    return ok(detail)


@router.patch(
    "/programs/{program_id}",
    response_model=Envelope[ProgramDetail],
    responses=ERRORS,
    summary="Update a programme",
)
async def update_program(
    program_id: uuid.UUID,
    payload: ProgramUpdate,
    db: DbSession,
    user: RecruiterUser,
    company_id: RecruiterCompanyId,
) -> dict:
    program = await _get_program(db, program_id, published_only=False)
    from app.models.enums import RoleName

    if (
        program.provider_company_id != company_id
        and RoleName.SUPER_ADMIN.value not in user.role_names
    ):
        raise PermissionDeniedError(
            "This programme belongs to another company", code="CROSS_COMPANY_ACCESS"
        )
    changes = payload.model_dump(exclude_unset=True)
    skills = changes.pop("skills", None)
    for field, value in changes.items():
        setattr(program, field, value)
    if "price_amount" in changes:
        program.is_free = program.price_amount == 0
    if skills is not None:
        await db.execute(delete(ProgramSkill).where(ProgramSkill.program_id == program.id))
        for entry in skills:
            db.add(
                ProgramSkill(
                    program_id=program.id, skill_id=entry["skill_id"],
                    target_level=entry["target_level"],
                    coverage_weight=entry["coverage_weight"],
                )
            )
    await db.commit()
    reloaded = await _get_program(db, program.id, published_only=False)
    detail = ProgramDetail.model_validate(reloaded)
    detail.modules = [ModuleOut.model_validate(m) for m in reloaded.modules]
    return ok(detail)


# ----------------------------------------------------------- enrolments ----
@router.post(
    "/programs/{program_id}/enroll",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[EnrollmentOut],
    responses=ERRORS,
    summary="Enrol in a programme",
)
async def enroll(
    program_id: uuid.UUID, student: CurrentStudent, db: DbSession
) -> dict:
    program = await _get_program(db, program_id)
    existing = (
        await db.execute(
            select(Enrollment).where(
                Enrollment.program_id == program.id, Enrollment.student_id == student.id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("You are already enrolled", code="ALREADY_ENROLLED")
    if program.seats is not None and program.enrollment_count >= program.seats:
        raise BusinessRuleError("This programme is full", code="PROGRAM_FULL")

    enrollment = Enrollment(
        program_id=program.id, student_id=student.id, enrolled_at=_now(),
        status=EnrollmentStatus.ENROLLED,
    )
    db.add(enrollment)
    program.enrollment_count += 1
    await db.commit()
    reloaded = (
        await db.execute(
            select(Enrollment)
            .where(Enrollment.id == enrollment.id)
            .options(
                selectinload(Enrollment.program).selectinload(LearningProgram.skills),
                selectinload(Enrollment.module_progress),
            )
        )
    ).scalar_one()
    return ok(EnrollmentOut.model_validate(reloaded))


@router.get(
    "/enrollments",
    response_model=Page[EnrollmentOut],
    responses=ERRORS,
    summary="My enrolments",
)
async def my_enrollments(
    student: CurrentStudent,
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
    status_filter: Annotated[EnrollmentStatus | None, Query(alias="status")] = None,
) -> Page[EnrollmentOut]:
    stmt = (
        select(Enrollment)
        .where(Enrollment.student_id == student.id)
        .options(
            selectinload(Enrollment.program).selectinload(LearningProgram.skills),
            selectinload(Enrollment.module_progress),
        )
    )
    if status_filter:
        stmt = stmt.where(Enrollment.status == status_filter)
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Enrollment.created_at.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
    ).scalars().all()
    return Page.build(
        [EnrollmentOut.model_validate(r) for r in rows], total, page.page, page.page_size
    )


@router.post(
    "/enrollments/{enrollment_id}/modules/{module_id}",
    response_model=Envelope[EnrollmentOut],
    responses=ERRORS,
    summary="Mark a module complete",
    description=(
        "Records module progress and recomputes overall completion. Finishing "
        "every mandatory module completes the enrolment, issues a certification "
        "when the programme grants one, and credits the skills it teaches to "
        "the student's profile."
    ),
)
async def complete_module(
    enrollment_id: uuid.UUID,
    module_id: uuid.UUID,
    payload: ModuleCompleteIn,
    student: CurrentStudent,
    db: DbSession,
) -> dict:
    enrollment = (
        await db.execute(
            select(Enrollment)
            .where(Enrollment.id == enrollment_id, Enrollment.student_id == student.id)
            .options(selectinload(Enrollment.module_progress))
        )
    ).scalar_one_or_none()
    if enrollment is None:
        raise NotFoundError("Enrolment not found", code="ENROLLMENT_NOT_FOUND")

    program = await _get_program(db, enrollment.program_id, published_only=False)
    module = next((m for m in program.modules if m.id == module_id), None)
    if module is None:
        raise NotFoundError("Module not found", code="MODULE_NOT_FOUND")

    progress = next(
        (p for p in enrollment.module_progress if p.module_id == module_id), None
    )
    if progress is None:
        progress = ModuleProgress(enrollment_id=enrollment.id, module_id=module_id)
        db.add(progress)
    progress.is_completed = payload.is_completed
    progress.completed_at = _now() if payload.is_completed else None
    progress.time_spent_minutes += payload.time_spent_minutes
    await db.flush()

    mandatory = [m for m in program.modules if m.is_mandatory] or program.modules
    done = {
        p.module_id
        for p in (
            await db.execute(
                select(ModuleProgress).where(
                    ModuleProgress.enrollment_id == enrollment.id,
                    ModuleProgress.is_completed.is_(True),
                )
            )
        ).scalars()
    }
    completed_mandatory = sum(1 for m in mandatory if m.id in done)
    enrollment.progress_percentage = (
        round(completed_mandatory / len(mandatory) * 100, 1) if mandatory else 0.0
    )
    enrollment.last_activity_at = _now()
    if enrollment.started_at is None:
        enrollment.started_at = _now()
    if enrollment.progress_percentage >= 100 and enrollment.status != EnrollmentStatus.COMPLETED:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = _now()
        await _award_completion(db, enrollment, program, student)
    elif enrollment.status == EnrollmentStatus.ENROLLED:
        enrollment.status = EnrollmentStatus.IN_PROGRESS

    await student_service.compute_profile_completion(db, student)
    await student_service.evaluate_badges(db, student)
    await db.commit()

    reloaded = (
        await db.execute(
            select(Enrollment)
            .where(Enrollment.id == enrollment.id)
            .options(
                selectinload(Enrollment.program).selectinload(LearningProgram.skills),
                selectinload(Enrollment.module_progress),
            )
        )
    ).scalar_one()
    return ok(EnrollmentOut.model_validate(reloaded))


async def _award_completion(db, enrollment, program, student) -> None:
    """Issue the certification and credit the skills the programme teaches."""
    if program.grants_certificate:
        db.add(
            StudentCertification(
                student_id=student.id,
                enrollment_id=enrollment.id,
                name=program.title,
                issuer=program.provider_name
                or (program.company.name if program.company else "SkillBridge"),
                issued_on=_now().date(),
                skill_ids=[str(s.skill_id) for s in program.skills],
                verification_status="VERIFIED",
            )
        )
    for program_skill in program.skills:
        await skill_service.upsert_student_skill(
            db, student.id, program_skill.skill_id,
            level=ProficiencyLevel(program_skill.target_level),
            source=SkillSource.CERTIFICATION,
            evidence={
                "program_id": str(program.id),
                "program_title": program.title,
                "completed_at": _now().isoformat(),
            },
        )
    await skill_service.refresh_student_readiness(db, student)


# ------------------------------------------------------ certifications ----
@router.get(
    "/certifications",
    response_model=Envelope[list[CertificationOut]],
    responses=ERRORS,
    summary="My certifications",
)
async def list_certifications(student: CurrentStudent, db: DbSession) -> dict:
    rows = (
        await db.execute(
            select(StudentCertification)
            .where(StudentCertification.student_id == student.id)
            .order_by(StudentCertification.issued_on.desc().nullslast())
        )
    ).scalars().all()
    return ok([CertificationOut.model_validate(r) for r in rows])


@router.post(
    "/certifications",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[CertificationOut],
    responses=ERRORS,
    summary="Add a certification",
    description="Self-added certifications start as UNVERIFIED. Linking the "
                "certificate document lets an institution admin verify it.",
)
async def add_certification(
    payload: CertificationIn, student: CurrentStudent, db: DbSession
) -> dict:
    row = StudentCertification(
        student_id=student.id,
        name=payload.name,
        issuer=payload.issuer,
        credential_id=payload.credential_id,
        credential_url=payload.credential_url,
        issued_on=payload.issued_on,
        expires_on=payload.expires_on,
        document_id=payload.document_id,
        skill_ids=[str(s) for s in payload.skill_ids],
    )
    db.add(row)
    await db.flush()

    for skill_id in payload.skill_ids:
        await skill_service.upsert_student_skill(
            db, student.id, skill_id, level=ProficiencyLevel.INTERMEDIATE,
            source=SkillSource.CERTIFICATION,
            evidence={"certification": payload.name, "issuer": payload.issuer},
        )
    await skill_service.refresh_student_readiness(db, student)
    await student_service.compute_profile_completion(db, student)
    await student_service.evaluate_badges(db, student)
    await db.commit()
    return ok(CertificationOut.model_validate(row))


@router.delete(
    "/certifications/{certification_id}",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Remove a certification",
)
async def delete_certification(
    certification_id: uuid.UUID, student: CurrentStudent, db: DbSession
) -> MessageResponse:
    result = await db.execute(
        delete(StudentCertification).where(
            StudentCertification.id == certification_id,
            StudentCertification.student_id == student.id,
        )
    )
    if not result.rowcount:
        raise NotFoundError("Certification not found", code="CERTIFICATION_NOT_FOUND")
    await student_service.compute_profile_completion(db, student)
    await db.commit()
    return MessageResponse(message="Certification removed")
