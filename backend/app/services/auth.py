"""Authentication and account lifecycle."""
from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    InvalidCredentialsError,
    NotFoundError,
    PermissionDeniedError,
    TokenError,
)
from app.core.logging import get_logger
from app.core.rbac import default_home, permissions_for_roles
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
    generate_url_token,
    hash_password,
    hash_token,
    needs_rehash,
    sign_value,
    validate_password_strength,
    verify_password,
)
from app.models.enums import (
    AuditAction,
    NotificationCategory,
    NotificationChannel,
    RoleName,
    UserStatus,
)
from app.models.notification import NotificationPreference
from app.models.organization import Company, Institution
from app.models.profile import AcademicianProfile, RecruiterProfile, StudentProfile
from app.models.user import OneTimeToken, Role, User, UserSession
from app.services import audit
from app.services.email import send_email

log = get_logger("auth")

MAX_FAILED_ATTEMPTS = 8
LOCKOUT_MINUTES = 15


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    """SQLite round-trips naive datetimes; normalise before comparing."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def slugify(value: str, *, max_length: int = 120) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or "item")[:max_length]


async def unique_slug(
    db: AsyncSession, model: Any, base: str, column: str = "slug"
) -> str:
    """Append -2, -3 ... until the slug is free."""
    base = slugify(base)
    candidate, suffix = base, 1
    col = getattr(model, column)
    while True:
        exists = (
            await db.execute(select(model.id).where(col == candidate).limit(1))
        ).first()
        if not exists:
            return candidate
        suffix += 1
        candidate = f"{base}-{suffix}"[:120]


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    stmt = (
        select(User)
        .where(func.lower(User.email) == email.lower().strip(), User.deleted_at.is_(None))
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _get_role(db: AsyncSession, name: RoleName) -> Role:
    role = (
        await db.execute(
            select(Role).where(Role.name == name).options(selectinload(Role.permissions))
        )
    ).scalar_one_or_none()
    if role is None:  # pragma: no cover - bootstrap guarantees roles exist
        raise NotFoundError(f"Role {name} is not configured", code="ROLE_NOT_CONFIGURED")
    return role


async def _seed_notification_preferences(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Opt-in by default for in-app, and for the email categories that matter."""
    email_on = {
        NotificationCategory.APPLICATION, NotificationCategory.MENTORSHIP,
        NotificationCategory.EVENT, NotificationCategory.SYSTEM,
    }
    for category in NotificationCategory:
        db.add(
            NotificationPreference(
                user_id=user_id, category=category,
                channel=NotificationChannel.IN_APP, is_enabled=True,
            )
        )
        db.add(
            NotificationPreference(
                user_id=user_id, category=category,
                channel=NotificationChannel.EMAIL, is_enabled=category in email_on,
            )
        )


# ------------------------------------------------------------- registration --
async def register_user(
    db: AsyncSession, payload: Any, request: Request | None = None
) -> User:
    email = str(payload.email).lower().strip()
    if await get_user_by_email(db, email):
        raise ConflictError(
            "An account with this email already exists", code="EMAIL_ALREADY_REGISTERED"
        )
    validate_password_strength(payload.password, email=email)

    role_name = RoleName(payload.role)
    role = await _get_role(db, role_name)
    if not role.is_assignable_on_signup:
        raise PermissionDeniedError(
            f"{role.label} accounts are created by an administrator",
            code="ROLE_NOT_SELF_ASSIGNABLE",
        )

    institution: Institution | None = None
    if payload.institution_id:
        institution = await db.get(Institution, payload.institution_id)
        if institution is None or institution.deleted_at is not None:
            raise NotFoundError("Institution not found", code="INSTITUTION_NOT_FOUND")

    company: Company | None = None
    if payload.company_id:
        company = await db.get(Company, payload.company_id)
        if company is None or company.deleted_at is not None:
            raise NotFoundError("Company not found", code="COMPANY_NOT_FOUND")
    elif payload.company_name and role_name in (
        RoleName.INDUSTRY_ADMIN, RoleName.INDUSTRY_RECRUITER
    ):
        slug = await unique_slug(db, Company, payload.company_name)
        company = Company(
            name=payload.company_name.strip(), slug=slug,
            contact_email=email, description="",
        )
        db.add(company)
        await db.flush()

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        status=(
            UserStatus.PENDING_VERIFICATION
            if settings.REQUIRE_EMAIL_VERIFICATION
            else UserStatus.ACTIVE
        ),
        institution_id=institution.id if institution else None,
        company_id=company.id if company else None,
        password_changed_at=_now(),
    )
    user.roles = [role]
    db.add(user)
    await db.flush()

    # Role-specific profile, created up front so the dashboard never 404s.
    if role_name == RoleName.STUDENT:
        db.add(
            StudentProfile(
                user_id=user.id,
                institution_id=institution.id if institution else None,
                portfolio_slug=await unique_slug(
                    db, StudentProfile, payload.full_name, "portfolio_slug"
                ),
            )
        )
    elif role_name == RoleName.ACADEMICIAN:
        db.add(
            AcademicianProfile(
                user_id=user.id,
                institution_id=institution.id if institution else None,
            )
        )
    elif role_name in (RoleName.INDUSTRY_RECRUITER, RoleName.INDUSTRY_ADMIN) and company:
        db.add(
            RecruiterProfile(
                user_id=user.id, company_id=company.id,
                is_primary_contact=(role_name == RoleName.INDUSTRY_ADMIN),
            )
        )

    await _seed_notification_preferences(db, user.id)

    raw_token = await issue_one_time_token(db, user, "verify_email")
    await audit.record(
        db, AuditAction.REGISTER, actor=user, resource_type="user",
        resource_id=user.id, description=f"Registered as {role_name.value}",
        request=request,
    )
    await db.commit()
    await db.refresh(user, ["roles"])

    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}"
    await send_email(
        user.email, "verify_email", db=db, user_id=user.id,
        name=user.full_name.split()[0], verify_url=verify_url,
    )
    await send_email(
        user.email, "welcome", db=db, user_id=user.id, name=user.full_name.split()[0]
    )
    await db.commit()
    log.info("auth.registered", user_id=str(user.id), role=role_name.value)
    return user


# --------------------------------------------------------------- one-time ---
async def issue_one_time_token(
    db: AsyncSession, user: User, purpose: str, ttl: timedelta | None = None
) -> str:
    """Create a single-use token, invalidating any previous one for the purpose."""
    await db.execute(
        update(OneTimeToken)
        .where(
            OneTimeToken.user_id == user.id,
            OneTimeToken.purpose == purpose,
            OneTimeToken.used_at.is_(None),
        )
        .values(used_at=_now())
    )
    if ttl is None:
        ttl = (
            timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS)
            if purpose == "verify_email"
            else timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)
        )
    raw = generate_url_token()
    db.add(
        OneTimeToken(
            user_id=user.id, token_hash=hash_token(raw), purpose=purpose,
            expires_at=_now() + ttl,
        )
    )
    await db.flush()
    return raw


async def consume_one_time_token(
    db: AsyncSession, raw_token: str, purpose: str
) -> User:
    record = (
        await db.execute(
            select(OneTimeToken).where(
                OneTimeToken.token_hash == hash_token(raw_token),
                OneTimeToken.purpose == purpose,
            )
        )
    ).scalar_one_or_none()
    if record is None or record.used_at is not None:
        raise TokenError("This link is invalid or has already been used",
                         code="TOKEN_INVALID_OR_USED")
    if (_aware(record.expires_at) or _now()) < _now():
        raise TokenError("This link has expired", code="TOKEN_EXPIRED")
    record.used_at = _now()
    user = (
        await db.execute(
            select(User)
            .where(User.id == record.user_id)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
    ).scalar_one_or_none()
    if user is None:
        raise NotFoundError("Account not found", code="ACCOUNT_NOT_FOUND")
    return user


# ------------------------------------------------------------------ login ---
async def authenticate(
    db: AsyncSession, email: str, password: str, request: Request | None = None
) -> User:
    user = await get_user_by_email(db, email)
    if user is None:
        # Same error and comparable timing whether or not the account exists.
        hash_password(password)
        await audit.record(
            db, AuditAction.LOGIN_FAILED, actor_email=email, status="FAILURE",
            description="Unknown account", request=request,
        )
        await db.commit()
        raise InvalidCredentialsError()

    locked_until = _aware(user.locked_until)
    if locked_until and locked_until > _now():
        minutes = max(1, int((locked_until - _now()).total_seconds() // 60) + 1)
        raise PermissionDeniedError(
            f"Too many failed attempts. Try again in {minutes} minute(s).",
            code="ACCOUNT_LOCKED",
        )

    if not verify_password(password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = _now() + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_attempts = 0
            log.warning("auth.account_locked", user_id=str(user.id))
        await audit.record(
            db, AuditAction.LOGIN_FAILED, actor=user, status="FAILURE",
            description="Incorrect password", request=request,
        )
        await db.commit()
        raise InvalidCredentialsError()

    if user.status == UserStatus.SUSPENDED:
        raise PermissionDeniedError("This account is suspended", code="ACCOUNT_SUSPENDED")
    if user.status == UserStatus.DEACTIVATED:
        raise AuthenticationError("This account is deactivated", code="ACCOUNT_DEACTIVATED")
    if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_email_verified:
        raise PermissionDeniedError(
            "Please verify your email address before signing in",
            code="EMAIL_NOT_VERIFIED",
        )

    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = _now()
    if request is not None:
        forwarded = request.headers.get("x-forwarded-for")
        user.last_login_ip = (
            forwarded.split(",")[0].strip()[:64]
            if forwarded
            else (request.client.host if request.client else None)
        )
    return user


async def create_session(
    db: AsyncSession, user: User, request: Request | None = None
) -> tuple[str, str, datetime, UserSession]:
    """Issue an access/refresh pair bound to a new session row."""
    session_id = uuid.uuid4()
    refresh_raw, _, refresh_exp = create_refresh_token(user.id, session_id=str(session_id))
    access, access_exp = create_access_token(
        user.id, roles=user.role_names, session_id=str(session_id)
    )
    session = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_raw),
        expires_at=refresh_exp,
        user_agent=(request.headers.get("user-agent", "")[:255] if request else None),
        ip_address=(
            request.client.host if request and request.client else None
        ),
    )
    db.add(session)

    # Cap concurrent sessions: revoke the oldest beyond the limit.
    active = (
        await db.execute(
            select(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .order_by(UserSession.created_at.desc())
        )
    ).scalars().all()
    for stale in active[settings.MAX_ACTIVE_SESSIONS - 1:]:
        stale.revoked_at = _now()
        stale.revoked_reason = "session_limit"

    await db.flush()
    return access, refresh_raw, access_exp, session


async def rotate_refresh_token(
    db: AsyncSession, raw_refresh: str, request: Request | None = None
) -> tuple[str, str, datetime, User]:
    """Verify + rotate. Reuse of an already-rotated token revokes the family."""
    payload = decode_token(raw_refresh, "refresh")
    token_hash = hash_token(raw_refresh)
    session = (
        await db.execute(
            select(UserSession).where(UserSession.refresh_token_hash == token_hash)
        )
    ).scalar_one_or_none()

    if session is None:
        raise TokenError("Refresh token is not recognised", code="REFRESH_TOKEN_UNKNOWN")

    if session.revoked_at is not None:
        # Replay of a rotated token: treat the whole family as compromised.
        await db.execute(
            update(UserSession)
            .where(UserSession.user_id == session.user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=_now(), revoked_reason="token_reuse_detected")
        )
        await db.commit()
        log.warning("auth.refresh_reuse_detected", user_id=str(session.user_id))
        raise TokenError(
            "This session has been revoked. Please sign in again.",
            code="REFRESH_TOKEN_REUSED",
        )

    if (_aware(session.expires_at) or _now()) < _now():
        raise TokenError("Session has expired, please sign in again",
                         code="REFRESH_TOKEN_EXPIRED")

    user = (
        await db.execute(
            select(User)
            .where(User.id == session.user_id, User.deleted_at.is_(None))
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
    ).scalar_one_or_none()
    if user is None or user.status in (UserStatus.SUSPENDED, UserStatus.DEACTIVATED):
        raise AuthenticationError("Account is not active", code="ACCOUNT_INACTIVE")

    session.revoked_at = _now()
    session.revoked_reason = "rotated"

    new_session_id = uuid.uuid4()
    new_refresh, _, refresh_exp = create_refresh_token(
        user.id, session_id=str(new_session_id)
    )
    access, access_exp = create_access_token(
        user.id, roles=user.role_names, session_id=str(new_session_id)
    )
    db.add(
        UserSession(
            id=new_session_id,
            user_id=user.id,
            refresh_token_hash=hash_token(new_refresh),
            expires_at=refresh_exp,
            rotated_from=session.id,
            user_agent=session.user_agent,
            ip_address=session.ip_address,
        )
    )
    await db.flush()
    _ = payload  # claims already validated by decode_token
    return access, new_refresh, access_exp, user


async def revoke_session(
    db: AsyncSession, raw_refresh: str | None, user: User, *, all_sessions: bool
) -> int:
    if all_sessions:
        result = await db.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .values(revoked_at=_now(), revoked_reason="logout_all")
        )
        return result.rowcount or 0
    if not raw_refresh:
        return 0
    result = await db.execute(
        update(UserSession)
        .where(
            UserSession.refresh_token_hash == hash_token(raw_refresh),
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
        )
        .values(revoked_at=_now(), revoked_reason="logout")
    )
    return result.rowcount or 0


# --------------------------------------------------------------- passwords --
async def request_password_reset(
    db: AsyncSession, email: str, request: Request | None = None
) -> None:
    """Always succeeds from the caller's perspective (no account enumeration)."""
    user = await get_user_by_email(db, email)
    if user is None or user.status == UserStatus.DEACTIVATED:
        log.info("auth.reset_requested_unknown", email_domain=email.split("@")[-1])
        return
    raw = await issue_one_time_token(db, user, "reset_password")
    await db.commit()
    await send_email(
        user.email, "reset_password", db=db, user_id=user.id,
        name=user.full_name.split()[0],
        reset_url=f"{settings.FRONTEND_URL}/reset-password?token={raw}",
    )
    await db.commit()


async def reset_password(
    db: AsyncSession, token: str, new_password: str, request: Request | None = None
) -> User:
    user = await consume_one_time_token(db, token, "reset_password")
    validate_password_strength(new_password, email=user.email)
    user.hashed_password = hash_password(new_password)
    user.password_changed_at = _now()
    user.failed_login_attempts = 0
    user.locked_until = None
    if user.status == UserStatus.PENDING_VERIFICATION:
        # Proving control of the mailbox also verifies the address.
        user.status = UserStatus.ACTIVE
        user.is_email_verified = True
        user.email_verified_at = _now()
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=_now(), revoked_reason="password_reset")
    )
    await audit.record(
        db, AuditAction.PASSWORD_RESET, actor=user, resource_type="user",
        resource_id=user.id, description="Password reset via email link", request=request,
    )
    await db.commit()
    await send_email(
        user.email, "password_changed", db=db, user_id=user.id,
        name=user.full_name.split()[0],
    )
    await db.commit()
    return user


async def change_password(
    db: AsyncSession, user: User, current: str, new: str, request: Request | None = None
) -> None:
    if not verify_password(current, user.hashed_password):
        raise InvalidCredentialsError(
            "Current password is incorrect", code="CURRENT_PASSWORD_INCORRECT"
        )
    validate_password_strength(new, email=user.email)
    user.hashed_password = hash_password(new)
    user.password_changed_at = _now()
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=_now(), revoked_reason="password_change")
    )
    await audit.record(
        db, AuditAction.PASSWORD_CHANGE, actor=user, resource_type="user",
        resource_id=user.id, description="Password changed", request=request,
    )
    await db.commit()
    await send_email(
        user.email, "password_changed", db=db, user_id=user.id,
        name=user.full_name.split()[0],
    )
    await db.commit()


async def verify_email(db: AsyncSession, token: str) -> User:
    user = await consume_one_time_token(db, token, "verify_email")
    if not user.is_email_verified:
        user.is_email_verified = True
        user.email_verified_at = _now()
        if user.status == UserStatus.PENDING_VERIFICATION:
            user.status = UserStatus.ACTIVE
    await db.commit()
    return user


async def resend_verification(db: AsyncSession, email: str) -> None:
    user = await get_user_by_email(db, email)
    if user is None or user.is_email_verified:
        return
    raw = await issue_one_time_token(db, user, "verify_email")
    await db.commit()
    await send_email(
        user.email, "verify_email", db=db, user_id=user.id,
        name=user.full_name.split()[0],
        verify_url=f"{settings.FRONTEND_URL}/verify-email?token={raw}",
    )
    await db.commit()


# ----------------------------------------------------------------- session --
async def build_authenticated_user(db: AsyncSession, user: User) -> dict[str, Any]:
    """Assemble the post-login payload the frontend bootstraps from."""
    roles = user.role_names
    permissions = sorted(user.permission_codes or permissions_for_roles(roles))
    profile_id: uuid.UUID | None = None
    completion = 0
    requires_onboarding = False

    if RoleName.STUDENT.value in roles:
        profile = (
            await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user.id)
            )
        ).scalar_one_or_none()
        if profile:
            profile_id, completion = profile.id, profile.profile_completion
            requires_onboarding = profile.profile_completion < 40
    elif RoleName.ACADEMICIAN.value in roles:
        profile = (
            await db.execute(
                select(AcademicianProfile).where(AcademicianProfile.user_id == user.id)
            )
        ).scalar_one_or_none()
        if profile:
            profile_id, completion = profile.id, profile.profile_completion
            requires_onboarding = profile.profile_completion < 40

    return {
        "user": user,
        "roles": roles,
        "permissions": permissions,
        "home_route": default_home(roles),
        "profile_id": profile_id,
        "profile_completion": completion,
        "requires_onboarding": requires_onboarding,
        "csrf_token": sign_value(generate_csrf_token()),
    }
