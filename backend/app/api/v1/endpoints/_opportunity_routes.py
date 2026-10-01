"""Shared CRUD router builder for the concrete opportunity types.

Internships, jobs, live projects and faculty programmes have identical
lifecycle, ownership and publication rules - only their payload schema and
polymorphic type differ. One builder keeps that logic in a single place while
each resource keeps its own path, tag, schema and OpenAPI documentation.
"""
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import (
    DbSession,
    OptionalUser,
    RecruiterCompanyId,
    RecruiterUser,
)
from app.models.enums import AuditAction, OpportunityStatus, OpportunityType, WorkMode
from app.models.opportunity import OpportunitySkill
from app.schemas.common import (
    Envelope,
    ErrorResponse,
    MessageResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.schemas.opportunity import (
    OpportunityDetail,
    OpportunityListItem,
    OpportunityUpdate,
    StatusChange,
)
from app.services import audit
from app.services import opportunity as opportunity_service

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Not allowed in the current state"},
}


def build_router(
    *,
    prefix: str,
    tag: str,
    opportunity_type: OpportunityType,
    create_schema: type,
    label: str,
    list_description: str,
    create_description: str,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    # Imported here to avoid a circular import at module load.
    from app.api.v1.endpoints.opportunities import (
        decorate_for_student,
        to_detail,
        to_list_item,
    )

    @router.get(
        "",
        response_model=Page[OpportunityListItem],
        summary=f"Browse {label}s",
        description=list_description,
    )
    async def list_items(
        db: DbSession,
        page: Annotated[PaginationParams, Depends(pagination)],
        user: OptionalUser = None,
        q: str | None = None,
        company_id: uuid.UUID | None = None,
        job_role_id: uuid.UUID | None = None,
        skill_id: Annotated[list[uuid.UUID] | None, Query()] = None,
        location: str | None = None,
        work_mode: WorkMode | None = None,
        open_only: bool = True,
        sort_by: Annotated[str, Query(pattern="^(recent|deadline|match|applications)$")] = "recent",
    ) -> Page[OpportunityListItem]:
        entity = opportunity_service.polymorphic_opportunity()
        stmt = select(entity).options(
            selectinload(entity.company),
            selectinload(entity.job_role),
            selectinload(entity.skills).selectinload(OpportunitySkill.skill),
        )
        stmt = opportunity_service.apply_filters(
            stmt, entity, q=q, opportunity_type=opportunity_type,
            company_id=company_id, job_role_id=job_role_id, skill_ids=skill_id,
            location=location, work_mode=work_mode, open_only=open_only,
        )
        total = (
            await db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()

        if sort_by == "match" and user is not None:
            rows = (
                await db.execute(
                    stmt.order_by(entity.published_at.desc().nullslast()).limit(200)
                )
            ).scalars().all()
            items = await decorate_for_student(
                db, user, rows, [to_list_item(r) for r in rows]
            )
            items.sort(key=lambda i: -(i.match_score or 0))
            window = items[page.offset : page.offset + page.limit]
            return Page.build(window, min(total, len(items)), page.page, page.page_size)

        order = {
            "recent": entity.published_at.desc().nullslast(),
            "deadline": entity.application_deadline.asc().nullslast(),
            "applications": entity.applications_count.desc(),
        }.get(sort_by, entity.published_at.desc().nullslast())
        rows = (
            await db.execute(stmt.order_by(order).offset(page.offset).limit(page.limit))
        ).scalars().all()
        items = await decorate_for_student(
            db, user, rows, [to_list_item(r) for r in rows]
        )
        return Page.build(items, total, page.page, page.page_size)

    @router.get(
        "/mine",
        response_model=Page[OpportunityListItem],
        responses=ERRORS,
        summary=f"My company's {label}s",
        description="Every posting owned by the recruiter's company, including "
                    "drafts and closed postings.",
    )
    async def list_mine(
        db: DbSession,
        company_id: RecruiterCompanyId,
        page: Annotated[PaginationParams, Depends(pagination)],
        status_filter: Annotated[OpportunityStatus | None, Query(alias="status")] = None,
    ) -> Page[OpportunityListItem]:
        entity = opportunity_service.polymorphic_opportunity()
        stmt = (
            select(entity)
            .where(
                entity.opportunity_type == opportunity_type,
                entity.company_id == company_id,
                entity.deleted_at.is_(None),
            )
            .options(
                selectinload(entity.company),
                selectinload(entity.job_role),
                selectinload(entity.skills).selectinload(OpportunitySkill.skill),
            )
        )
        if status_filter:
            stmt = stmt.where(entity.status == status_filter)
        total = (
            await db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = (
            await db.execute(
                stmt.order_by(entity.created_at.desc())
                .offset(page.offset)
                .limit(page.limit)
            )
        ).scalars().all()
        return Page.build(
            [to_list_item(r) for r in rows], total, page.page, page.page_size
        )

    @router.post(
        "",
        status_code=201,
        response_model=Envelope[OpportunityDetail],
        responses=ERRORS,
        summary=f"Create a {label}",
        description=create_description,
    )
    async def create_item(
        payload: create_schema,
        request: Request,
        db: DbSession,
        user: RecruiterUser,
        company_id: RecruiterCompanyId,
        publish: Annotated[bool, Query(description="Publish immediately")] = False,
    ) -> dict:
        opportunity = await opportunity_service.create_opportunity(
            db, opportunity_type=opportunity_type, payload=payload,
            company_id=company_id, posted_by=user, publish=publish,
        )
        await audit.record(
            db, AuditAction.OPPORTUNITY_CREATE, actor=user,
            resource_type=opportunity_type.value.lower(), resource_id=opportunity.id,
            description=f"Created {label}: {opportunity.title}", request=request,
            meta={"published": publish},
        )
        await db.commit()
        reloaded = await opportunity_service.get_opportunity_or_404(
            db, opportunity.id, include_unpublished=True
        )
        return ok(to_detail(reloaded))

    @router.patch(
        "/{opportunity_id}",
        response_model=Envelope[OpportunityDetail],
        responses=ERRORS,
        summary=f"Update a {label}",
        description="Type-specific fields go in `extra`; unknown keys are "
                    "rejected rather than silently ignored.",
    )
    async def update_item(
        opportunity_id: uuid.UUID,
        payload: OpportunityUpdate,
        request: Request,
        db: DbSession,
        user: RecruiterUser,
        company_id: RecruiterCompanyId,
    ) -> dict:
        opportunity = await opportunity_service.get_opportunity_or_404(
            db, opportunity_id, include_unpublished=True
        )
        opportunity_service.assert_can_manage(opportunity, user, company_id)
        await opportunity_service.update_opportunity(db, opportunity, payload)
        await audit.record(
            db, AuditAction.OPPORTUNITY_UPDATE, actor=user,
            resource_type=opportunity_type.value.lower(), resource_id=opportunity.id,
            description=f"Updated {label}: {opportunity.title}", request=request,
        )
        await db.commit()
        reloaded = await opportunity_service.get_opportunity_or_404(
            db, opportunity.id, include_unpublished=True
        )
        return ok(to_detail(reloaded))

    @router.post(
        "/{opportunity_id}/status",
        response_model=Envelope[OpportunityDetail],
        responses=ERRORS,
        summary=f"Change {label} status",
        description=(
            "Moves a posting between DRAFT, PUBLISHED, PAUSED, CLOSED and "
            "ARCHIVED. Publication is refused unless the posting has a "
            "description and at least one required skill - an unmatched posting "
            "is invisible to the recommendation engine."
        ),
    )
    async def change_status(
        opportunity_id: uuid.UUID,
        payload: StatusChange,
        request: Request,
        db: DbSession,
        user: RecruiterUser,
        company_id: RecruiterCompanyId,
    ) -> dict:
        opportunity = await opportunity_service.get_opportunity_or_404(
            db, opportunity_id, include_unpublished=True
        )
        opportunity_service.assert_can_manage(opportunity, user, company_id)
        await opportunity_service.change_status(db, opportunity, payload.status)
        await audit.record(
            db, AuditAction.OPPORTUNITY_UPDATE, actor=user,
            resource_type=opportunity_type.value.lower(), resource_id=opportunity.id,
            description=f"Status changed to {payload.status.value}", request=request,
        )
        await db.commit()
        reloaded = await opportunity_service.get_opportunity_or_404(
            db, opportunity.id, include_unpublished=True
        )
        return ok(to_detail(reloaded))

    @router.delete(
        "/{opportunity_id}",
        response_model=MessageResponse,
        responses=ERRORS,
        summary=f"Delete a {label}",
        description="Soft delete: the posting disappears from search but "
                    "existing applications and their history are preserved.",
    )
    async def delete_item(
        opportunity_id: uuid.UUID,
        request: Request,
        db: DbSession,
        user: RecruiterUser,
        company_id: RecruiterCompanyId,
    ) -> MessageResponse:
        opportunity = await opportunity_service.get_opportunity_or_404(
            db, opportunity_id, include_unpublished=True
        )
        opportunity_service.assert_can_manage(opportunity, user, company_id)
        opportunity.soft_delete()
        opportunity.status = OpportunityStatus.ARCHIVED
        await audit.record(
            db, AuditAction.OPPORTUNITY_DELETE, actor=user,
            resource_type=opportunity_type.value.lower(), resource_id=opportunity.id,
            description=f"Deleted {label}: {opportunity.title}", request=request,
        )
        await db.commit()
        return MessageResponse(message=f"{label.title()} deleted")

    return router
