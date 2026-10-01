"""FastAPI dependencies: authentication, authorisation and request context."""
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError, TokenError
from app.core.logging import user_id_ctx
from app.core.rbac import permissions_for_roles
from app.core.security import decode_token
from app.models.enums import RoleName, UserStatus
from app.models.profile import AcademicianProfile, RecruiterProfile, StudentProfile
from app.models.user import Role, User

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

DbSession = Annotated[AsyncSession, Depends(get_db)]
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def client_ip(request: Request) -> str | None:
    """Best-effort client IP, honouring a single proxy hop."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


def user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    return ua[:300] if ua else None


async def _load_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    stmt = (
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_current_user(
    request: Request, db: DbSession, credentials: Credentials = None
) -> User:
    """Resolve the authenticated user from the bearer token.

    Falls back to the ``access_token`` cookie so browser clients that prefer
    cookie storage work without a second auth path.
    """
    token: str | None = None
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")
    if not token:
        raise AuthenticationError()

    payload = decode_token(token, "access")
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise TokenError() from exc

    user = await _load_user(db, user_id)
    if user is None:
        raise AuthenticationError("Account no longer exists", code="ACCOUNT_NOT_FOUND")
    if user.status == UserStatus.SUSPENDED:
        raise PermissionDeniedError("This account is suspended", code="ACCOUNT_SUSPENDED")
    if user.status == UserStatus.DEACTIVATED:
        raise AuthenticationError("This account is deactivated", code="ACCOUNT_DEACTIVATED")

    request.state.user = user
    user_id_ctx.set(str(user.id))
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_verified_user(user: CurrentUser) -> User:
    """Active user; blocks unverified accounts when verification is mandatory."""
    from app.core.config import settings

    if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_email_verified:
        raise PermissionDeniedError(
            "Please verify your email address to continue", code="EMAIL_NOT_VERIFIED"
        )
    return user


ActiveUser = Annotated[User, Depends(get_verified_user)]


async def get_optional_user(
    request: Request, db: DbSession, credentials: Credentials = None
) -> User | None:
    """For endpoints with public + personalised behaviour (e.g. portfolios)."""
    try:
        return await get_current_user(request, db, credentials)
    except Exception:
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_roles(*roles: RoleName) -> Callable[[User], Awaitable[User]]:
    """Dependency factory asserting the user holds at least one of ``roles``."""
    wanted = {r.value for r in roles}

    async def _dep(user: ActiveUser) -> User:
        if RoleName.SUPER_ADMIN.value in user.role_names:
            return user
        if not wanted & set(user.role_names):
            raise PermissionDeniedError(
                "This area requires one of: " + ", ".join(sorted(wanted)),
                code="ROLE_REQUIRED",
                details={"required_roles": sorted(wanted)},
            )
        return user

    return _dep


def require_permission(*codes: str) -> Callable[[User], Awaitable[User]]:
    """Dependency factory asserting the user holds every permission in ``codes``."""
    required = set(codes)

    async def _dep(user: ActiveUser) -> User:
        granted = user.permission_codes or permissions_for_roles(user.role_names)
        missing = required - granted
        if missing:
            raise PermissionDeniedError(
                "Missing permission: " + ", ".join(sorted(missing)),
                code="PERMISSION_DENIED",
                details={"missing_permissions": sorted(missing)},
            )
        return user

    return _dep


# ------------------------------------------------- role-scoped shortcuts ----
StudentUser = Annotated[User, Depends(require_roles(RoleName.STUDENT))]
AcademicianUser = Annotated[User, Depends(require_roles(RoleName.ACADEMICIAN))]
RecruiterUser = Annotated[
    User, Depends(require_roles(RoleName.INDUSTRY_RECRUITER, RoleName.INDUSTRY_ADMIN))
]
CompanyAdminUser = Annotated[User, Depends(require_roles(RoleName.INDUSTRY_ADMIN))]
InstitutionAdminUser = Annotated[User, Depends(require_roles(RoleName.INSTITUTION_ADMIN))]
AdminUser = Annotated[User, Depends(require_roles(RoleName.SUPER_ADMIN))]


async def get_student_profile(user: StudentUser, db: DbSession) -> StudentProfile:
    profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == user.id))
    ).scalar_one_or_none()
    if profile is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(
            "Student profile has not been created yet", code="STUDENT_PROFILE_NOT_FOUND"
        )
    return profile


CurrentStudent = Annotated[StudentProfile, Depends(get_student_profile)]


async def get_academician_profile(
    user: AcademicianUser, db: DbSession
) -> AcademicianProfile:
    profile = (
        await db.execute(
            select(AcademicianProfile).where(AcademicianProfile.user_id == user.id)
        )
    ).scalar_one_or_none()
    if profile is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(
            "Academician profile has not been created yet",
            code="ACADEMICIAN_PROFILE_NOT_FOUND",
        )
    return profile


CurrentAcademician = Annotated[AcademicianProfile, Depends(get_academician_profile)]


async def get_recruiter_company_id(user: RecruiterUser, db: DbSession) -> uuid.UUID:
    """The company a recruiter acts on behalf of. Every write is scoped to it."""
    if user.company_id:
        return user.company_id
    recruiter = (
        await db.execute(
            select(RecruiterProfile).where(RecruiterProfile.user_id == user.id)
        )
    ).scalar_one_or_none()
    if recruiter is None:
        raise PermissionDeniedError(
            "Your account is not linked to a company", code="COMPANY_NOT_LINKED"
        )
    return recruiter.company_id


RecruiterCompanyId = Annotated[uuid.UUID, Depends(get_recruiter_company_id)]
