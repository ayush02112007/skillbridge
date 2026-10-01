"""Student portal endpoints: profile, skills, skill gaps and dashboard.

Note: this module intentionally does NOT use ``from __future__ import
annotations``. The sub-resource route factory at the bottom passes schema
classes as closure variables, and FastAPI must resolve them to real types at
registration time rather than to deferred strings.
"""
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.ai.service import get_ai_service
from app.core.deps import (
    CurrentStudent,
    DbSession,
    require_permission,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import AuditAction, SkillSource
from app.models.organization import Department, Institution
from app.models.profile import (
    Achievement,
    EducationRecord,
    ExperienceRecord,
    StudentProfile,
    StudentProject,
)
from app.models.skill import (
    JobRole,
    StudentSkill,
)
from app.models.user import User
from app.schemas.common import Envelope, ErrorResponse, MessageResponse, ok
from app.schemas.skill import (
    GapItemOut,
    RoleReadinessOut,
    SkillGapOut,
    StudentSkillBulkInput,
    StudentSkillOut,
)
from app.schemas.student import (
    AchievementIn,
    AchievementOut,
    EducationIn,
    EducationOut,
    ExperienceIn,
    ExperienceOut,
    ProfileCompletionOut,
    ProjectIn,
    ProjectOut,
    StudentDashboardOut,
    StudentProfileOut,
    StudentProfileUpdate,
)
from app.services import audit
from app.services import skill as skill_service
from app.services import student as student_service

router = APIRouter(prefix="/students", tags=["Students"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
    422: {"model": ErrorResponse, "description": "Validation error"},
}


async def _profile_payload(db, student: StudentProfile) -> StudentProfileOut:
    """Flatten the profile with the related names the UI needs."""
    user = student.user or await db.get(User, student.user_id)
    institution = (
        await db.get(Institution, student.institution_id)
        if student.institution_id
        else None
    )
    department = (
        await db.get(Department, student.department_id)
        if student.department_id
        else None
    )
    role = (
        await db.get(JobRole, student.target_job_role_id)
        if student.target_job_role_id
        else None
    )
    data = StudentProfileOut.model_validate(student)
    data.full_name = user.full_name if user else ""
    data.email = user.email if user else None
    data.phone = user.phone if user else None
    data.avatar_url = user.avatar_url if user else None
    data.institution_name = institution.name if institution else None
    data.department_name = department.name if department else None
    data.target_job_role_title = role.title if role else None
    return data


# ------------------------------------------------------------- profile -----
@router.get(
    "/me",
    response_model=Envelope[StudentProfileOut],
    responses=ERRORS,
    summary="My student profile",
    description="The signed-in student's full profile, with institution, "
                "department and target-role names resolved.",
)
async def get_my_profile(student: CurrentStudent, db: DbSession) -> dict:
    return ok(await _profile_payload(db, student))


@router.patch(
    "/me",
    response_model=Envelope[StudentProfileOut],
    responses=ERRORS,
    summary="Update my student profile",
    description=(
        "Partial update. Changing `target_job_role_id` immediately recomputes "
        "the skill-gap analysis and readiness score for the new target."
    ),
)
async def update_my_profile(
    payload: StudentProfileUpdate, request: Request, student: CurrentStudent, db: DbSession
) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("institution_id"):
        if await db.get(Institution, changes["institution_id"]) is None:
            raise NotFoundError("Institution not found", code="INSTITUTION_NOT_FOUND")
    if changes.get("department_id"):
        if await db.get(Department, changes["department_id"]) is None:
            raise NotFoundError("Department not found", code="DEPARTMENT_NOT_FOUND")

    target_changed = False
    if changes.get("target_job_role_id"):
        role = await db.get(JobRole, changes["target_job_role_id"])
        if role is None:
            raise NotFoundError("Job role not found", code="JOB_ROLE_NOT_FOUND")
        target_changed = student.target_job_role_id != role.id

    for field, value in changes.items():
        setattr(student, field, value)
    await db.flush()

    if target_changed and student.target_job_role_id:
        role = await db.get(JobRole, student.target_job_role_id)
        if role:
            await skill_service.compute_skill_gap(db, student, role)

    await student_service.compute_profile_completion(db, student)
    await student_service.evaluate_badges(db, student)
    await audit.record(
        db, AuditAction.PROFILE_UPDATE, actor=student.user, resource_type="student_profile",
        resource_id=student.id, description="Student profile updated",
        request=request, meta={"fields": sorted(changes)},
    )
    await db.commit()
    await db.refresh(student)
    return ok(await _profile_payload(db, student))


@router.get(
    "/me/completion",
    response_model=Envelope[ProfileCompletionOut],
    responses=ERRORS,
    summary="Profile completion breakdown",
    description="Section-by-section scoring plus the highest-impact actions to "
                "raise it.",
)
async def my_completion(student: CurrentStudent, db: DbSession) -> dict:
    data = await student_service.compute_profile_completion(db, student)
    await db.commit()
    return ok(ProfileCompletionOut.model_validate(data))


@router.get(
    "/me/dashboard",
    response_model=Envelope[StudentDashboardOut],
    responses=ERRORS,
    summary="Student dashboard",
    description=(
        "Everything the dashboard renders: readiness, top skills, the current "
        "skill gap, application funnel, deadlines, learning progress, "
        "assessments and badges."
    ),
)
async def my_dashboard(student: CurrentStudent, db: DbSession) -> dict:
    data = await student_service.build_dashboard(db, student)
    await student_service.evaluate_badges(db, student)
    await db.commit()
    return ok(StudentDashboardOut.model_validate(data))


# -------------------------------------------------------------- skills -----
@router.get(
    "/me/skills",
    response_model=Envelope[list[StudentSkillOut]],
    responses=ERRORS,
    summary="My skill profile",
    description="Every skill on the profile with its level, score, evidence "
                "source and confidence.",
)
async def my_skills(student: CurrentStudent, db: DbSession) -> dict:
    rows = (
        await db.execute(
            select(StudentSkill)
            .where(StudentSkill.student_id == student.id)
            .options(selectinload(StudentSkill.skill))
            .order_by(StudentSkill.score.desc())
        )
    ).scalars().all()
    return ok([StudentSkillOut.model_validate(r) for r in rows])


@router.put(
    "/me/skills",
    response_model=Envelope[list[StudentSkillOut]],
    responses=ERRORS,
    summary="Add or update skills",
    description=(
        "Upserts a batch of self-reported skills. Self-reports are merged with "
        "existing evidence rather than overwriting it - an assessed level is "
        "never silently replaced by a self-claim."
    ),
)
async def upsert_my_skills(
    payload: StudentSkillBulkInput, request: Request, student: CurrentStudent, db: DbSession
) -> dict:
    skill_ids = [entry.skill_id for entry in payload.skills]
    known = await skill_service.resolve_skills(db, skill_ids)
    missing = [str(sid) for sid in skill_ids if sid not in known]
    if missing:
        raise NotFoundError(
            "One or more skills do not exist", code="SKILL_NOT_FOUND",
            details={"unknown_skill_ids": missing},
        )
    for entry in payload.skills:
        await skill_service.upsert_student_skill(
            db, student.id, entry.skill_id, level=entry.level,
            source=SkillSource.SELF_REPORTED,
            years_of_experience=entry.years_of_experience,
        )
    await skill_service.refresh_student_readiness(db, student)
    await student_service.compute_profile_completion(db, student)
    await student_service.evaluate_badges(db, student)
    await audit.record(
        db, AuditAction.PROFILE_UPDATE, actor=student.user, resource_type="student_skills",
        resource_id=student.id, description=f"{len(payload.skills)} skill(s) updated",
        request=request,
    )
    await db.commit()
    rows = (
        await db.execute(
            select(StudentSkill)
            .where(StudentSkill.student_id == student.id)
            .options(selectinload(StudentSkill.skill))
            .order_by(StudentSkill.score.desc())
        )
    ).scalars().all()
    return ok([StudentSkillOut.model_validate(r) for r in rows])


@router.delete(
    "/me/skills/{skill_id}",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Remove a skill",
)
async def delete_my_skill(
    skill_id: uuid.UUID, student: CurrentStudent, db: DbSession
) -> MessageResponse:
    await skill_service.remove_student_skill(db, student.id, skill_id)
    await skill_service.refresh_student_readiness(db, student)
    await student_service.compute_profile_completion(db, student)
    await db.commit()
    return MessageResponse(message="Skill removed")


# ----------------------------------------------------------- skill gap -----
def _gap_out(result, *, computed_at=None, generated_by="deterministic") -> SkillGapOut:
    # GapItem is a slots dataclass, so asdict() rather than vars().
    items = [GapItemOut.model_validate(asdict(i)) for i in result.items]
    return SkillGapOut(
        job_role_id=result.job_role_id,
        job_role_title=result.job_role_title,
        readiness_score=result.readiness_score,
        gap_percentage=result.gap_percentage,
        matched_count=result.matched_count,
        total_required=result.total_required,
        summary=result.summary,
        computed_at=computed_at,
        generated_by=generated_by,
        items=items,
        missing_skills=[i for i in items if i.status == "MISSING"],
        weak_skills=[i for i in items if i.status == "WEAK"],
        strong_skills=[i for i in items if i.status == "STRONG"],
        priority_skills=[i for i in items if i.status != "STRONG"][:5],
    )


@router.get(
    "/me/skill-gap",
    response_model=Envelope[SkillGapOut],
    responses=ERRORS,
    summary="Skill gap for a target role",
    description=(
        "Compares the student's evidenced skills against the industry-expected "
        "profile for a role and returns a prioritised plan.\n\n"
        "Omit `job_role_id` to analyse the student's chosen target role. Every "
        "item states the current level, the required level, the size of the gap "
        "and what to do about it."
    ),
)
async def my_skill_gap(
    student: CurrentStudent,
    db: DbSession,
    job_role_id: Annotated[uuid.UUID | None, Query(description="Defaults to your target role")] = None,
    explain: Annotated[bool, Query(description="Include an AI-written narrative")] = False,
) -> dict:
    role_id = job_role_id or student.target_job_role_id
    if role_id is None:
        raise ValidationError(
            "Choose a target role first, or pass job_role_id",
            code="NO_TARGET_ROLE",
        )
    role = await db.get(JobRole, role_id)
    if role is None:
        raise NotFoundError("Job role not found", code="JOB_ROLE_NOT_FOUND")

    result = await skill_service.compute_skill_gap(db, student, role)
    generated_by = "deterministic"
    if explain:
        narrative, generated_by = await get_ai_service().explain_skill_gap(result)
        result.summary = narrative
    await db.commit()
    return ok(
        _gap_out(result, computed_at=datetime.now(UTC), generated_by=generated_by)
    )


@router.get(
    "/me/role-readiness",
    response_model=Envelope[list[RoleReadinessOut]],
    responses=ERRORS,
    summary="Readiness across all roles",
    description="Scores the student against every role in the taxonomy, best "
                "first - the basis for 'careers you are closest to'.",
)
async def my_role_readiness(
    student: CurrentStudent,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=30)] = 8,
) -> dict:
    data = await skill_service.compute_all_role_readiness(db, student, limit=limit)
    return ok([RoleReadinessOut.model_validate(row) for row in data])


# -------------------------------------------------------- sub-resources ----
def _subresource_routes(
    path: str, model, schema_in, schema_out, label: str, description: str
) -> None:
    """Register list/create/update/delete for a student-owned sub-resource.

    These five resources have identical ownership and lifecycle rules, so they
    share one implementation instead of five near-copies.
    """

    @router.get(
        f"/me/{path}",
        response_model=Envelope[list[schema_out]],
        responses=ERRORS,
        summary=f"List my {label}",
        description=description,
        name=f"list_my_{path}",
    )
    async def _list(student: CurrentStudent, db: DbSession) -> dict:
        rows = (
            await db.execute(
                select(model).where(model.student_id == student.id).order_by(
                    model.created_at.desc()
                )
            )
        ).scalars().all()
        return ok([schema_out.model_validate(r) for r in rows])

    @router.post(
        f"/me/{path}",
        status_code=status.HTTP_201_CREATED,
        response_model=Envelope[schema_out],
        responses=ERRORS,
        summary=f"Add {label}",
        name=f"create_my_{path}",
    )
    async def _create(
        payload: schema_in, student: CurrentStudent, db: DbSession
    ) -> dict:
        row = model(student_id=student.id, **payload.model_dump())
        db.add(row)
        await db.flush()
        await student_service.compute_profile_completion(db, student)
        await student_service.evaluate_badges(db, student)
        await db.commit()
        return ok(schema_out.model_validate(row))

    @router.patch(
        f"/me/{path}/{{item_id}}",
        response_model=Envelope[schema_out],
        responses=ERRORS,
        summary=f"Update {label}",
        name=f"update_my_{path}",
    )
    async def _update(
        item_id: uuid.UUID, payload: schema_in, student: CurrentStudent, db: DbSession
    ) -> dict:
        row = (
            await db.execute(
                select(model).where(model.id == item_id, model.student_id == student.id)
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"{label.title()} entry not found", code="ENTRY_NOT_FOUND")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        await db.commit()
        return ok(schema_out.model_validate(row))

    @router.delete(
        f"/me/{path}/{{item_id}}",
        response_model=MessageResponse,
        responses=ERRORS,
        summary=f"Delete {label}",
        name=f"delete_my_{path}",
    )
    async def _delete(
        item_id: uuid.UUID, student: CurrentStudent, db: DbSession
    ) -> MessageResponse:
        result = await db.execute(
            delete(model).where(model.id == item_id, model.student_id == student.id)
        )
        if not result.rowcount:
            raise NotFoundError(f"{label.title()} entry not found", code="ENTRY_NOT_FOUND")
        await student_service.compute_profile_completion(db, student)
        await db.commit()
        return MessageResponse(message=f"{label.title()} entry deleted")


_subresource_routes(
    "education", EducationRecord, EducationIn, EducationOut, "education",
    "Academic records from secondary school through to the current degree.",
)
_subresource_routes(
    "experience", ExperienceRecord, ExperienceIn, ExperienceOut, "experience",
    "Internships, jobs, research and volunteering. Entries created from a "
    "completed SkillBridge placement are marked verified and cannot be edited "
    "into something else.",
)
_subresource_routes(
    "projects", StudentProject, ProjectIn, ProjectOut, "projects",
    "Projects the student built. These feed the portfolio and the project "
    "relevance factor in matching.",
)
_subresource_routes(
    "achievements", Achievement, AchievementIn, AchievementOut, "achievements",
    "Competitions, hackathons, awards and leadership positions.",
)


# ------------------------------------------------- directory (staff view) --
@router.get(
    "/{student_id}",
    response_model=Envelope[StudentProfileOut],
    responses=ERRORS,
    summary="View a student profile",
    description=(
        "Staff view of a single student. Institution admins see their own "
        "students; recruiters see students who applied to their company's "
        "postings; platform admins see everyone."
    ),
)
async def get_student(
    student_id: uuid.UUID,
    db: DbSession,
    user: Annotated[Any, Depends(require_permission("user:read_any"))] = None,
) -> dict:
    from app.models.enums import RoleName

    student = await student_service.get_student_or_404(db, student_id)
    if (
        RoleName.INSTITUTION_ADMIN.value in user.role_names
        and RoleName.SUPER_ADMIN.value not in user.role_names
        and student.institution_id != user.institution_id
    ):
        from app.core.exceptions import PermissionDeniedError

        raise PermissionDeniedError(
            "This student belongs to another institution", code="CROSS_INSTITUTION_ACCESS"
        )
    return ok(await _profile_payload(db, student))
