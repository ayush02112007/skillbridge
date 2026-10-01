"""Platform administration: users, organisations, moderation and the audit trail."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.cache import cache_ping
from app.core.config import settings
from app.core.deps import AdminUser, DbSession
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.rbac import PERMISSIONS, ROLE_PERMISSIONS
from app.core.security import hash_password, validate_password_strength
from app.models.audit import AuditLog
from app.models.enums import (
    AuditAction,
    OpportunityStatus,
    RoleName,
    UserStatus,
    VerificationStatus,
)
from app.models.opportunity import Opportunity
from app.models.organization import Company, Institution
from app.models.profile import AcademicianProfile, RecruiterProfile, StudentProfile
from app.models.user import Role, User
from app.schemas.auth import UserOut
from app.schemas.common import (
    APIModel,
    Envelope,
    ErrorResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.services import analytics as analytics_service
from app.services import audit
from app.services.auth import unique_slug

router = APIRouter(prefix="/admin", tags=["Admin"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Platform admin only"},
    404: {"model": ErrorResponse, "description": "Not found"},
}


class AdminUserCreate(APIModel):
    email: str
    password: str
    full_name: str
    role: RoleName
    institution_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None


class UserStatusChange(APIModel):
    status: UserStatus
    reason: str = ""


class RoleAssignment(APIModel):
    roles: list[RoleName]


class InstitutionCreate(APIModel):
    name: str
    short_name: str | None = None
    institution_type: str = "UNIVERSITY"
    city: str | None = None
    state: str | None = None
    country: str = "India"
    website: str | None = None
    contact_email: str | None = None
    established_year: int | None = None


class VerificationChange(APIModel):
    verification_status: VerificationStatus


class AuditLogOut(APIModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None = None
    actor_email: str | None = None
    actor_roles: list[object] = []
    action: AuditAction
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    description: str = ""
    ip_address: str | None = None
    request_id: str | None = None
    status: str = "SUCCESS"
    meta: dict[str, object] = {}
    created_at: datetime


class SystemHealthOut(APIModel):
    environment: str
    database: str
    cache: str
    storage: str
    ai_provider: str
    email_provider: str
    debug: bool
    match_weights: dict[str, float]
    config_problems: list[str] = []


# ------------------------------------------------------------------ users --
@router.get(
    "/users",
    response_model=Page[UserOut],
    responses=ERRORS,
    summary="List users",
)
async def list_users(
    db: DbSession,
    _admin: AdminUser,
    page: Annotated[PaginationParams, Depends(pagination)],
    q: str | None = None,
    role: RoleName | None = None,
    status_filter: Annotated[UserStatus | None, Query(alias="status")] = None,
) -> Page[UserOut]:
    stmt = (
        select(User)
        .where(User.deleted_at.is_(None))
        .options(selectinload(User.roles))
    )
    if q:
        needle = f"%{q.lower().strip()}%"
        stmt = stmt.where(
            or_(func.lower(User.email).like(needle), func.lower(User.full_name).like(needle))
        )
    if status_filter:
        stmt = stmt.where(User.status == status_filter)
    if role:
        stmt = stmt.where(User.roles.any(Role.name == role))

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(User.created_at.desc()).offset(page.offset).limit(page.limit)
        )
    ).scalars().all()
    return Page.build(
        [UserOut.model_validate(r) for r in rows], total, page.page, page.page_size
    )


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[UserOut],
    responses=ERRORS,
    summary="Provision a user",
    description="Creates accounts that cannot be self-registered, in particular "
                "institution admins and platform admins.",
)
async def create_user(
    payload: AdminUserCreate, request: Request, db: DbSession, admin: AdminUser
) -> dict:
    from app.services.auth import get_user_by_email

    email = payload.email.lower().strip()
    if await get_user_by_email(db, email):
        raise ConflictError("Email already registered", code="EMAIL_ALREADY_REGISTERED")
    validate_password_strength(payload.password, email=email)

    role = (
        await db.execute(
            select(Role)
            .where(Role.name == payload.role)
            .options(selectinload(Role.permissions))
        )
    ).scalar_one_or_none()
    if role is None:
        raise NotFoundError("Role not configured", code="ROLE_NOT_CONFIGURED")

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
        email_verified_at=datetime.now(UTC),
        institution_id=payload.institution_id,
        company_id=payload.company_id,
        password_changed_at=datetime.now(UTC),
    )
    user.roles = [role]
    db.add(user)
    await db.flush()

    if payload.role == RoleName.STUDENT:
        db.add(
            StudentProfile(
                user_id=user.id, institution_id=payload.institution_id,
                portfolio_slug=await unique_slug(
                    db, StudentProfile, payload.full_name, "portfolio_slug"
                ),
            )
        )
    elif payload.role == RoleName.ACADEMICIAN:
        db.add(
            AcademicianProfile(user_id=user.id, institution_id=payload.institution_id)
        )
    elif payload.role in (RoleName.INDUSTRY_RECRUITER, RoleName.INDUSTRY_ADMIN) and payload.company_id:
        db.add(RecruiterProfile(user_id=user.id, company_id=payload.company_id))

    await audit.record(
        db, AuditAction.ADMIN_ACTION, actor=admin, resource_type="user",
        resource_id=user.id, description=f"Provisioned {payload.role.value} account",
        request=request,
    )
    await db.commit()
    await db.refresh(user, ["roles"])
    return ok(UserOut.model_validate(user))


@router.patch(
    "/users/{user_id}/status",
    response_model=Envelope[UserOut],
    responses=ERRORS,
    summary="Suspend or reactivate a user",
)
async def change_user_status(
    user_id: uuid.UUID,
    payload: UserStatusChange,
    request: Request,
    db: DbSession,
    admin: AdminUser,
) -> dict:
    user = (
        await db.execute(
            select(User).where(User.id == user_id).options(selectinload(User.roles))
        )
    ).scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found", code="USER_NOT_FOUND")
    if user.id == admin.id:
        raise BusinessRuleError(
            "You cannot change your own account status", code="SELF_STATUS_CHANGE"
        )
    user.status = payload.status
    if payload.status in (UserStatus.SUSPENDED, UserStatus.DEACTIVATED):
        from sqlalchemy import update

        from app.models.user import UserSession

        await db.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .values(
                revoked_at=datetime.now(UTC),
                revoked_reason=f"admin_{payload.status.value.lower()}",
            )
        )
    await audit.record(
        db, AuditAction.ADMIN_ACTION, actor=admin, resource_type="user",
        resource_id=user.id,
        description=f"Status -> {payload.status.value}: {payload.reason}",
        request=request,
    )
    await db.commit()
    return ok(UserOut.model_validate(user))


@router.put(
    "/users/{user_id}/roles",
    response_model=Envelope[UserOut],
    responses=ERRORS,
    summary="Set a user's roles",
)
async def set_roles(
    user_id: uuid.UUID,
    payload: RoleAssignment,
    request: Request,
    db: DbSession,
    admin: AdminUser,
) -> dict:
    user = (
        await db.execute(
            select(User).where(User.id == user_id).options(selectinload(User.roles))
        )
    ).scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found", code="USER_NOT_FOUND")
    if user.id == admin.id and RoleName.SUPER_ADMIN not in payload.roles:
        raise BusinessRuleError(
            "You cannot remove your own platform-admin role",
            code="SELF_DEMOTION_BLOCKED",
        )
    roles = (
        await db.execute(
            select(Role)
            .where(Role.name.in_(payload.roles))
            .options(selectinload(Role.permissions))
        )
    ).scalars().all()
    if len(roles) != len(set(payload.roles)):
        raise NotFoundError("One or more roles are not configured",
                            code="ROLE_NOT_CONFIGURED")
    user.roles = list(roles)
    await audit.record(
        db, AuditAction.ROLE_CHANGE, actor=admin, resource_type="user",
        resource_id=user.id,
        description="Roles -> " + ", ".join(r.value for r in payload.roles),
        request=request,
    )
    await db.commit()
    await db.refresh(user, ["roles"])
    return ok(UserOut.model_validate(user))


# ---------------------------------------------------------- organisations --
@router.post(
    "/institutions",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Create an institution",
)
async def create_institution(
    payload: InstitutionCreate, request: Request, db: DbSession, admin: AdminUser
) -> dict:
    institution = Institution(
        **payload.model_dump(),
        slug=await unique_slug(db, Institution, payload.name),
        verification_status=VerificationStatus.VERIFIED,
    )
    db.add(institution)
    await audit.record(
        db, AuditAction.ADMIN_ACTION, actor=admin, resource_type="institution",
        description=f"Created institution {payload.name}", request=request,
    )
    await db.commit()
    return ok({"id": str(institution.id), "name": institution.name,
               "slug": institution.slug})


@router.patch(
    "/companies/{company_id}/verification",
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Verify a company",
    description="Verification is the trust signal students see on a posting.",
)
async def verify_company(
    company_id: uuid.UUID,
    payload: VerificationChange,
    request: Request,
    db: DbSession,
    admin: AdminUser,
) -> dict:
    company = await db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Company not found", code="COMPANY_NOT_FOUND")
    company.verification_status = payload.verification_status
    await audit.record(
        db, AuditAction.ADMIN_ACTION, actor=admin, resource_type="company",
        resource_id=company.id,
        description=f"Verification -> {payload.verification_status.value}",
        request=request,
    )
    await db.commit()
    return ok(
        {
            "id": str(company.id),
            "name": company.name,
            "verification_status": company.verification_status.value,
        }
    )


@router.patch(
    "/institutions/{institution_id}/verification",
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Verify an institution",
)
async def verify_institution(
    institution_id: uuid.UUID,
    payload: VerificationChange,
    request: Request,
    db: DbSession,
    admin: AdminUser,
) -> dict:
    institution = await db.get(Institution, institution_id)
    if institution is None:
        raise NotFoundError("Institution not found", code="INSTITUTION_NOT_FOUND")
    institution.verification_status = payload.verification_status
    await audit.record(
        db, AuditAction.ADMIN_ACTION, actor=admin, resource_type="institution",
        resource_id=institution.id,
        description=f"Verification -> {payload.verification_status.value}",
        request=request,
    )
    await db.commit()
    return ok(
        {
            "id": str(institution.id),
            "name": institution.name,
            "verification_status": institution.verification_status.value,
        }
    )


# ----------------------------------------------------------- moderation ----
@router.post(
    "/opportunities/{opportunity_id}/moderate",
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Moderate a posting",
    description="Takes a posting down platform-wide. Used for policy breaches; "
                "the action and its reason are recorded in the audit trail.",
)
async def moderate_opportunity(
    opportunity_id: uuid.UUID,
    request: Request,
    db: DbSession,
    admin: AdminUser,
    reason: Annotated[str, Query(max_length=400)] = "",
    new_status: Annotated[OpportunityStatus, Query(alias="status")] = OpportunityStatus.ARCHIVED,
) -> dict:
    opportunity = await db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise NotFoundError("Opportunity not found", code="OPPORTUNITY_NOT_FOUND")
    opportunity.status = new_status
    await audit.record(
        db, AuditAction.ADMIN_ACTION, actor=admin, resource_type="opportunity",
        resource_id=opportunity.id,
        description=f"Moderated to {new_status.value}: {reason}", request=request,
    )
    await db.commit()
    return ok({"id": str(opportunity.id), "status": opportunity.status.value})


# ---------------------------------------------------------------- audit ----
@router.get(
    "/audit-logs",
    response_model=Page[AuditLogOut],
    responses=ERRORS,
    summary="Audit trail",
    description="Append-only record of sensitive actions: sign-ins, profile and "
                "role changes, postings, applications, document access, exports "
                "and administrative actions.",
)
async def audit_logs(
    db: DbSession,
    _admin: AdminUser,
    page: Annotated[PaginationParams, Depends(pagination)],
    action: AuditAction | None = None,
    actor_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> Page[AuditLogOut]:
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if status_filter:
        stmt = stmt.where(AuditLog.status == status_filter)
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(AuditLog.created_at.desc()).offset(page.offset).limit(page.limit)
        )
    ).scalars().all()
    return Page.build(
        [AuditLogOut.model_validate(r) for r in rows], total, page.page, page.page_size
    )


# --------------------------------------------------------------- system ----
@router.get(
    "/system/health",
    response_model=Envelope[SystemHealthOut],
    responses=ERRORS,
    summary="System health and configuration",
    description="Dependency status and the effective configuration. Secrets are "
                "never included - only which provider is selected.",
)
async def system_health(_admin: AdminUser) -> dict:
    return ok(
        SystemHealthOut(
            environment=settings.ENVIRONMENT,
            database="postgresql" if not settings.is_sqlite else "sqlite",
            cache="redis" if await cache_ping() else "in-memory fallback",
            storage=settings.STORAGE_PROVIDER,
            ai_provider=settings.AI_PROVIDER,
            email_provider=settings.EMAIL_PROVIDER,
            debug=settings.DEBUG,
            match_weights=settings.match_weights,
            config_problems=settings.validate_runtime(),
        )
    )


@router.get(
    "/system/permissions",
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Permission catalogue",
    description="The full RBAC matrix, as enforced by the API.",
)
async def permission_catalogue(_admin: AdminUser) -> dict:
    return ok(
        {
            "permissions": PERMISSIONS,
            "roles": {
                role.value: sorted(codes) for role, codes in ROLE_PERMISSIONS.items()
            },
        }
    )


@router.get(
    "/analytics",
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Platform analytics",
)
async def admin_analytics(db: DbSession, _admin: AdminUser) -> dict:
    return ok(await analytics_service.platform_analytics(db))


@router.post(
    "/maintenance/refresh-skill-demand",
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Recompute skill demand",
    description="Recalculates every skill's demand score from live postings. "
                "Normally run on a schedule by the Celery beat worker.",
)
async def refresh_skill_demand(
    request: Request, db: DbSession, admin: AdminUser
) -> dict:
    from app.services import skill as skill_service

    updated = await skill_service.refresh_skill_demand(db)
    await audit.record(
        db, AuditAction.ADMIN_ACTION, actor=admin, resource_type="skill",
        description=f"Refreshed skill demand ({updated} updated)", request=request,
    )
    await db.commit()
    return ok({"skills_updated": updated})
