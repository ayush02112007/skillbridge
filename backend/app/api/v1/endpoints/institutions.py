"""Institution administration: directory, students, departments and oversight."""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import DbSession, InstitutionAdminUser
from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import VerificationStatus
from app.models.learning import StudentCertification
from app.models.organization import Department, IndustryPartnership, Institution
from app.models.profile import StudentProfile
from app.models.skill import StudentSkill
from app.models.user import User
from app.schemas.common import (
    APIModel,
    Envelope,
    ErrorResponse,
    MessageResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.schemas.student import StudentSummaryOut

router = APIRouter(prefix="/institutions", tags=["Institutions"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
}


class InstitutionOut(APIModel):
    id: uuid.UUID
    name: str
    slug: str
    short_name: str | None = None
    institution_type: str = "UNIVERSITY"
    accreditation: str | None = None
    website: str | None = None
    logo_url: str | None = None
    description: str = ""
    city: str | None = None
    state: str | None = None
    country: str = "India"
    established_year: int | None = None
    verification_status: VerificationStatus
    is_demo: bool = False
    student_count: int = 0


class InstitutionUpdate(APIModel):
    name: str | None = None
    short_name: str | None = None
    institution_type: str | None = None
    accreditation: str | None = None
    website: str | None = None
    logo_url: str | None = None
    description: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    established_year: int | None = None


class DepartmentIn(APIModel):
    name: str
    code: str
    hod_name: str | None = None


class DepartmentOut(APIModel):
    id: uuid.UUID
    name: str
    code: str
    hod_name: str | None = None
    student_count: int = 0


class PartnershipOut(APIModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    partnership_type: str
    status: str
    summary: str = ""
    started_on: str | None = None
    engagement_score: int = 0


@router.get(
    "",
    response_model=Page[InstitutionOut],
    summary="Browse institutions",
    description="Public directory, used by the registration form to let "
                "students pick their college.",
)
async def list_institutions(
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
    q: str | None = None,
    city: str | None = None,
) -> Page[InstitutionOut]:
    stmt = select(Institution).where(Institution.deleted_at.is_(None))
    if q:
        needle = f"%{q.lower().strip()}%"
        stmt = stmt.where(
            or_(
                func.lower(Institution.name).like(needle),
                func.lower(Institution.short_name).like(needle),
            )
        )
    if city:
        stmt = stmt.where(func.lower(Institution.city) == city.lower())
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Institution.name).offset(page.offset).limit(page.limit)
        )
    ).scalars().all()

    counts = dict(
        (
            await db.execute(
                select(StudentProfile.institution_id, func.count())
                .where(
                    StudentProfile.institution_id.in_([r.id for r in rows] or [uuid.uuid4()]),
                    StudentProfile.deleted_at.is_(None),
                )
                .group_by(StudentProfile.institution_id)
            )
        ).all()
    )
    items = []
    for row in rows:
        data = InstitutionOut.model_validate(row)
        data.student_count = counts.get(row.id, 0)
        items.append(data)
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/me",
    response_model=Envelope[InstitutionOut],
    responses=ERRORS,
    summary="My institution",
)
async def my_institution(db: DbSession, user: InstitutionAdminUser) -> dict:
    if user.institution_id is None:
        raise NotFoundError(
            "Your account is not linked to an institution", code="INSTITUTION_NOT_LINKED"
        )
    institution = await db.get(Institution, user.institution_id)
    if institution is None:
        raise NotFoundError("Institution not found", code="INSTITUTION_NOT_FOUND")
    count = (
        await db.execute(
            select(func.count())
            .select_from(StudentProfile)
            .where(
                StudentProfile.institution_id == institution.id,
                StudentProfile.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    data = InstitutionOut.model_validate(institution)
    data.student_count = count
    return ok(data)


@router.patch(
    "/me",
    response_model=Envelope[InstitutionOut],
    responses=ERRORS,
    summary="Update my institution",
)
async def update_my_institution(
    payload: InstitutionUpdate, db: DbSession, user: InstitutionAdminUser
) -> dict:
    institution = await db.get(Institution, user.institution_id)
    if institution is None:
        raise NotFoundError("Institution not found", code="INSTITUTION_NOT_FOUND")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(institution, field, value)
    await db.commit()
    return ok(InstitutionOut.model_validate(institution))


@router.get(
    "/me/students",
    response_model=Page[StudentSummaryOut],
    responses=ERRORS,
    summary="My students",
    description="Every student at the institution, filterable by graduation "
                "year, placement status and readiness.",
)
async def my_students(
    db: DbSession,
    user: InstitutionAdminUser,
    page: Annotated[PaginationParams, Depends(pagination)],
    q: str | None = None,
    graduation_year: int | None = None,
    department_id: uuid.UUID | None = None,
    is_placed: bool | None = None,
    min_readiness: Annotated[float | None, Query(ge=0, le=100)] = None,
    sort_by: Annotated[str, Query(pattern="^(readiness|name|completion)$")] = "readiness",
) -> Page[StudentSummaryOut]:
    if user.institution_id is None:
        raise NotFoundError(
            "Your account is not linked to an institution", code="INSTITUTION_NOT_LINKED"
        )
    stmt = (
        select(StudentProfile)
        .where(
            StudentProfile.institution_id == user.institution_id,
            StudentProfile.deleted_at.is_(None),
        )
        .options(selectinload(StudentProfile.user))
    )
    if graduation_year:
        stmt = stmt.where(StudentProfile.graduation_year == graduation_year)
    if department_id:
        stmt = stmt.where(StudentProfile.department_id == department_id)
    if is_placed is not None:
        stmt = stmt.where(StudentProfile.is_placed.is_(is_placed))
    if min_readiness is not None:
        stmt = stmt.where(StudentProfile.skill_readiness_score >= min_readiness)
    if q:
        stmt = stmt.join(User, User.id == StudentProfile.user_id).where(
            func.lower(User.full_name).like(f"%{q.lower().strip()}%")
        )

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    order = {
        "readiness": StudentProfile.skill_readiness_score.desc(),
        "completion": StudentProfile.profile_completion.desc(),
    }.get(sort_by, StudentProfile.skill_readiness_score.desc())
    rows = (
        await db.execute(stmt.order_by(order).offset(page.offset).limit(page.limit))
    ).scalars().all()

    top_skills: dict[uuid.UUID, list[str]] = {}
    if rows:

        skill_rows = (
            await db.execute(
                select(StudentSkill)
                .where(StudentSkill.student_id.in_([r.id for r in rows]))
                .options(selectinload(StudentSkill.skill))
                .order_by(StudentSkill.score.desc())
            )
        ).scalars().all()
        for entry in skill_rows:
            bucket = top_skills.setdefault(entry.student_id, [])
            if len(bucket) < 5 and entry.skill:
                bucket.append(entry.skill.name)

    items = []
    for row in rows:
        data = StudentSummaryOut.model_validate(row)
        data.full_name = row.user.full_name if row.user else ""
        data.avatar_url = row.user.avatar_url if row.user else None
        data.top_skills = top_skills.get(row.id, [])
        items.append(data)
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/me/departments",
    response_model=Envelope[list[DepartmentOut]],
    responses=ERRORS,
    summary="My departments",
)
async def list_departments(db: DbSession, user: InstitutionAdminUser) -> dict:
    rows = (
        await db.execute(
            select(Department)
            .where(Department.institution_id == user.institution_id)
            .order_by(Department.name)
        )
    ).scalars().all()
    counts = dict(
        (
            await db.execute(
                select(StudentProfile.department_id, func.count())
                .where(StudentProfile.institution_id == user.institution_id)
                .group_by(StudentProfile.department_id)
            )
        ).all()
    )
    return ok(
        [
            DepartmentOut(
                id=r.id, name=r.name, code=r.code, hod_name=r.hod_name,
                student_count=counts.get(r.id, 0),
            )
            for r in rows
        ]
    )


@router.post(
    "/me/departments",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[DepartmentOut],
    responses=ERRORS,
    summary="Create a department",
)
async def create_department(
    payload: DepartmentIn, db: DbSession, user: InstitutionAdminUser
) -> dict:
    existing = (
        await db.execute(
            select(Department).where(
                Department.institution_id == user.institution_id,
                func.lower(Department.code) == payload.code.lower(),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("A department with this code already exists",
                            code="DEPARTMENT_EXISTS")
    row = Department(
        institution_id=user.institution_id, name=payload.name,
        code=payload.code.upper(), hod_name=payload.hod_name,
    )
    db.add(row)
    await db.commit()
    return ok(DepartmentOut(id=row.id, name=row.name, code=row.code, hod_name=row.hod_name))


@router.get(
    "/me/partnerships",
    response_model=Envelope[list[PartnershipOut]],
    responses=ERRORS,
    summary="Industry partnerships",
)
async def list_partnerships(db: DbSession, user: InstitutionAdminUser) -> dict:
    rows = (
        await db.execute(
            select(IndustryPartnership)
            .where(IndustryPartnership.institution_id == user.institution_id)
            .options(selectinload(IndustryPartnership.company))
            .order_by(IndustryPartnership.engagement_score.desc())
        )
    ).scalars().all()
    return ok(
        [
            PartnershipOut(
                id=r.id, company_id=r.company_id,
                company_name=r.company.name if r.company else "",
                partnership_type=r.partnership_type, status=r.status,
                summary=r.summary, started_on=r.started_on,
                engagement_score=r.engagement_score,
            )
            for r in rows
        ]
    )


@router.post(
    "/me/students/{student_id}/verify",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Verify a student's credentials",
    description="Marks a student's education records and certifications as "
                "institution-verified. Verified credentials are badged on the "
                "portfolio so viewers can tell claims from confirmed facts.",
)
async def verify_student(
    student_id: uuid.UUID, db: DbSession, user: InstitutionAdminUser
) -> MessageResponse:
    student = await db.get(StudentProfile, student_id)
    if student is None or student.institution_id != user.institution_id:
        raise NotFoundError("Student not found at your institution",
                            code="STUDENT_NOT_FOUND")

    from app.models.profile import EducationRecord

    education = (
        await db.execute(
            select(EducationRecord).where(EducationRecord.student_id == student.id)
        )
    ).scalars().all()
    for record in education:
        record.is_verified = True
    certifications = (
        await db.execute(
            select(StudentCertification).where(
                StudentCertification.student_id == student.id
            )
        )
    ).scalars().all()
    for certification in certifications:
        certification.verification_status = VerificationStatus.VERIFIED
        certification.verified_by_id = user.id
    await db.commit()
    return MessageResponse(
        message=f"Verified {len(education)} education record(s) and "
                f"{len(certifications)} certification(s)"
    )


@router.get(
    "/{institution_id}",
    response_model=Envelope[InstitutionOut],
    responses=ERRORS,
    summary="Institution profile",
)
async def get_institution(institution_id: uuid.UUID, db: DbSession) -> dict:
    institution = await db.get(Institution, institution_id)
    if institution is None or institution.deleted_at is not None:
        raise NotFoundError("Institution not found", code="INSTITUTION_NOT_FOUND")
    return ok(InstitutionOut.model_validate(institution))
