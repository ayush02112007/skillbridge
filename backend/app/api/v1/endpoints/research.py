"""Research, consultancy and innovation collaborations."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import (
    CurrentAcademician,
    DbSession,
    OptionalUser,
    require_permission,
)
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.enums import (
    CollaborationStatus,
    NotificationCategory,
    ResearchProjectType,
    RoleName,
)
from app.models.profile import AcademicianProfile
from app.models.research import ResearchApplication, ResearchProject
from app.schemas.collaboration import (
    ResearchApplicationIn,
    ResearchApplicationOut,
    ResearchDecisionIn,
    ResearchProjectIn,
    ResearchProjectOut,
)
from app.schemas.common import (
    Envelope,
    ErrorResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.services import notification
from app.services.auth import unique_slug

router = APIRouter(prefix="/research", tags=["Research"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
}


def _now() -> datetime:
    return datetime.now(UTC)


@router.get(
    "/projects",
    response_model=Page[ResearchProjectOut],
    summary="Browse research and consultancy projects",
    description="Collaborations published by industry and institutions: "
                "research, consultancy, joint publications, innovation and "
                "sponsored research.",
)
async def list_projects(
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
    user: OptionalUser = None,
    q: str | None = None,
    project_type: ResearchProjectType | None = None,
    status_filter: Annotated[CollaborationStatus | None, Query(alias="status")] = None,
    company_id: uuid.UUID | None = None,
    institution_id: uuid.UUID | None = None,
) -> Page[ResearchProjectOut]:
    stmt = (
        select(ResearchProject)
        .where(ResearchProject.deleted_at.is_(None))
        .options(selectinload(ResearchProject.applications))
    )
    if q:
        needle = f"%{q.lower().strip()}%"
        stmt = stmt.where(
            or_(
                func.lower(ResearchProject.title).like(needle),
                ResearchProject.search_text.like(needle),
            )
        )
    if project_type:
        stmt = stmt.where(ResearchProject.project_type == project_type)
    stmt = stmt.where(
        ResearchProject.status == status_filter
        if status_filter
        else ResearchProject.status.in_(
            [CollaborationStatus.OPEN, CollaborationStatus.IN_REVIEW,
             CollaborationStatus.ACTIVE]
        )
    )
    if company_id:
        stmt = stmt.where(ResearchProject.company_id == company_id)
    if institution_id:
        stmt = stmt.where(ResearchProject.institution_id == institution_id)

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(ResearchProject.created_at.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
    ).scalars().all()

    applied: set[uuid.UUID] = set()
    if user is not None and rows:
        profile = (
            await db.execute(
                select(AcademicianProfile).where(AcademicianProfile.user_id == user.id)
            )
        ).scalar_one_or_none()
        if profile is not None:
            applied = set(
                (
                    await db.execute(
                        select(ResearchApplication.project_id).where(
                            ResearchApplication.academician_id == profile.id,
                            ResearchApplication.project_id.in_([r.id for r in rows]),
                        )
                    )
                ).scalars()
            )

    items = []
    for row in rows:
        data = ResearchProjectOut.model_validate(row)
        data.application_count = len(row.applications)
        data.has_applied = row.id in applied
        items.append(data)
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/projects/{project_id}",
    response_model=Envelope[ResearchProjectOut],
    responses=ERRORS,
    summary="Project detail",
)
async def get_project(project_id: uuid.UUID, db: DbSession) -> dict:
    row = (
        await db.execute(
            select(ResearchProject)
            .where(ResearchProject.id == project_id, ResearchProject.deleted_at.is_(None))
            .options(selectinload(ResearchProject.applications))
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Project not found", code="RESEARCH_PROJECT_NOT_FOUND")
    data = ResearchProjectOut.model_validate(row)
    data.application_count = len(row.applications)
    return ok(data)


@router.post(
    "/projects",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[ResearchProjectOut],
    responses=ERRORS,
    summary="Publish a collaboration",
    description="Industry admins and institution admins publish research and "
                "consultancy opportunities for academicians to apply to.",
)
async def create_project(
    payload: ResearchProjectIn,
    db: DbSession,
    user: Annotated[object, Depends(require_permission("research:manage"))],
) -> dict:
    project = ResearchProject(
        **payload.model_dump(),
        slug=await unique_slug(db, ResearchProject, payload.title),
        company_id=user.company_id,
        created_by_id=user.id,
        status=CollaborationStatus.OPEN,
    )
    if project.institution_id is None:
        project.institution_id = user.institution_id
    project.search_text = " ".join(
        [
            project.title, project.abstract,
            " ".join(str(a) for a in (project.research_areas or [])),
            " ".join(str(e) for e in (project.required_expertise or [])),
        ]
    ).lower()[:12000]
    db.add(project)
    await db.commit()
    return ok(ResearchProjectOut.model_validate(project))


@router.patch(
    "/projects/{project_id}/status",
    response_model=Envelope[ResearchProjectOut],
    responses=ERRORS,
    summary="Change collaboration status",
)
async def change_project_status(
    project_id: uuid.UUID,
    new_status: Annotated[CollaborationStatus, Query(alias="status")],
    db: DbSession,
    user: Annotated[object, Depends(require_permission("research:manage"))],
) -> dict:
    project = await db.get(ResearchProject, project_id)
    if project is None or project.deleted_at is not None:
        raise NotFoundError("Project not found", code="RESEARCH_PROJECT_NOT_FOUND")
    if (
        project.created_by_id != user.id
        and RoleName.SUPER_ADMIN.value not in user.role_names
    ):
        raise PermissionDeniedError("This project belongs to another organisation",
                                    code="PROJECT_NOT_OWNED")
    project.status = new_status
    await db.commit()
    return ok(ResearchProjectOut.model_validate(project))


@router.post(
    "/projects/{project_id}/apply",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[ResearchApplicationOut],
    responses=ERRORS,
    summary="Apply to a collaboration",
)
async def apply_to_project(
    project_id: uuid.UUID,
    payload: ResearchApplicationIn,
    db: DbSession,
    academician: CurrentAcademician,
) -> dict:
    project = await db.get(ResearchProject, project_id)
    if project is None or project.deleted_at is not None:
        raise NotFoundError("Project not found", code="RESEARCH_PROJECT_NOT_FOUND")
    if project.status not in (CollaborationStatus.OPEN, CollaborationStatus.IN_REVIEW):
        raise BusinessRuleError(
            "This collaboration is not accepting applications",
            code="PROJECT_NOT_OPEN",
        )
    if project.application_deadline and project.application_deadline < _now().replace(
        tzinfo=project.application_deadline.tzinfo
    ):
        raise BusinessRuleError("The deadline has passed", code="DEADLINE_PASSED")

    existing = (
        await db.execute(
            select(ResearchApplication).where(
                ResearchApplication.project_id == project.id,
                ResearchApplication.academician_id == academician.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("You have already applied", code="ALREADY_APPLIED")

    application = ResearchApplication(
        project_id=project.id,
        academician_id=academician.id,
        proposal=payload.proposal,
        relevant_publications=payload.relevant_publications,
    )
    db.add(application)
    if project.created_by_id:
        await notification.notify(
            db, project.created_by_id,
            category=NotificationCategory.SYSTEM,
            title=f"New proposal for {project.title}",
            body="An academician submitted a research proposal.",
            action_url=f"/industry/research/{project.id}",
            icon="flask-conical",
            resource_type="research_application",
        )
    await db.commit()
    data = ResearchApplicationOut.model_validate(application)
    data.project = ResearchProjectOut.model_validate(project)
    return ok(data)


@router.get(
    "/applications/mine",
    response_model=Page[ResearchApplicationOut],
    responses=ERRORS,
    summary="My research applications",
)
async def my_applications(
    db: DbSession,
    academician: CurrentAcademician,
    page: Annotated[PaginationParams, Depends(pagination)],
) -> Page[ResearchApplicationOut]:
    stmt = (
        select(ResearchApplication)
        .where(ResearchApplication.academician_id == academician.id)
        .options(selectinload(ResearchApplication.project))
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(ResearchApplication.created_at.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
    ).scalars().all()
    items = []
    for row in rows:
        data = ResearchApplicationOut.model_validate(row)
        if row.project:
            data.project = ResearchProjectOut.model_validate(row.project)
        items.append(data)
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/projects/{project_id}/applications",
    response_model=Page[ResearchApplicationOut],
    responses=ERRORS,
    summary="Applications received",
)
async def project_applications(
    project_id: uuid.UUID,
    db: DbSession,
    user: Annotated[object, Depends(require_permission("research:manage"))],
    page: Annotated[PaginationParams, Depends(pagination)],
) -> Page[ResearchApplicationOut]:
    project = await db.get(ResearchProject, project_id)
    if project is None:
        raise NotFoundError("Project not found", code="RESEARCH_PROJECT_NOT_FOUND")
    if (
        project.created_by_id != user.id
        and RoleName.SUPER_ADMIN.value not in user.role_names
    ):
        raise PermissionDeniedError("This project belongs to another organisation",
                                    code="PROJECT_NOT_OWNED")

    stmt = select(ResearchApplication).where(
        ResearchApplication.project_id == project_id
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(ResearchApplication.created_at.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
    ).scalars().all()

    items = []
    for row in rows:
        data = ResearchApplicationOut.model_validate(row)
        profile = await db.get(AcademicianProfile, row.academician_id)
        if profile is not None:
            await db.refresh(profile, ["user"])
            data.academician_name = profile.user.full_name if profile.user else ""
        items.append(data)
    return Page.build(items, total, page.page, page.page_size)


@router.patch(
    "/applications/{application_id}",
    response_model=Envelope[ResearchApplicationOut],
    responses=ERRORS,
    summary="Decide on a research application",
)
async def decide_application(
    application_id: uuid.UUID,
    payload: ResearchDecisionIn,
    db: DbSession,
    user: Annotated[object, Depends(require_permission("research:manage"))],
) -> dict:
    application = (
        await db.execute(
            select(ResearchApplication)
            .where(ResearchApplication.id == application_id)
            .options(selectinload(ResearchApplication.project))
        )
    ).scalar_one_or_none()
    if application is None:
        raise NotFoundError("Application not found", code="APPLICATION_NOT_FOUND")
    project = application.project
    if project is None or (
        project.created_by_id != user.id
        and RoleName.SUPER_ADMIN.value not in user.role_names
    ):
        raise PermissionDeniedError("This project belongs to another organisation",
                                    code="PROJECT_NOT_OWNED")

    application.status = payload.status
    application.reviewer_notes = payload.reviewer_notes
    if payload.status in ("ACCEPTED", "REJECTED"):
        application.decided_at = _now()
    if payload.status == "ACCEPTED":
        project.principal_investigator_id = application.academician_id
        project.status = CollaborationStatus.ACTIVE

    profile = await db.get(AcademicianProfile, application.academician_id)
    if profile is not None:
        await notification.notify(
            db, profile.user_id,
            category=NotificationCategory.SYSTEM,
            title=f"Research application {payload.status.lower()}",
            body=project.title,
            action_url="/academician/research",
            icon="flask-conical",
            resource_type="research_application",
            resource_id=application.id,
        )
    await db.commit()
    return ok(ResearchApplicationOut.model_validate(application))
