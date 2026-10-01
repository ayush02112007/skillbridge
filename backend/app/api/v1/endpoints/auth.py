"""Authentication endpoints."""
from __future__ import annotations

import uuid
from datetime import UTC
from typing import Any

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.exceptions import TokenError
from app.models.enums import AuditAction
from app.models.user import UserSession
from app.schemas.auth import (
    AuthenticatedUser,
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SessionOut,
    TokenPair,
    UpdateMeRequest,
    UserOut,
    VerifyEmailRequest,
)
from app.schemas.common import Envelope, ErrorResponse, MessageResponse, ok
from app.services import audit
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Invalid request"},
    401: {"model": ErrorResponse, "description": "Authentication failed"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    422: {"model": ErrorResponse, "description": "Validation error"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
}

REFRESH_COOKIE = "refresh_token"
ACCESS_COOKIE = "access_token"
CSRF_COOKIE = "csrf_token"


def _set_auth_cookies(response: Response, tokens: TokenPair, csrf: str | None) -> None:
    """Cookies are a convenience for browser clients; the API also accepts bearer."""
    common = {
        "httponly": True,
        "secure": settings.SECURE_COOKIES,
        "samesite": "lax",
        "domain": settings.COOKIE_DOMAIN,
        "path": "/",
    }
    response.set_cookie(
        ACCESS_COOKIE, tokens.access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, **common,
    )
    response.set_cookie(
        REFRESH_COOKIE, tokens.refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, **common,
    )
    if csrf:
        # Readable by JS on purpose: the double-submit pattern needs it echoed
        # back in the X-CSRF-Token header.
        response.set_cookie(
            CSRF_COOKIE, csrf, max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            httponly=False, secure=settings.SECURE_COOKIES, samesite="lax",
            domain=settings.COOKIE_DOMAIN, path="/",
        )


def _clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/", domain=settings.COOKIE_DOMAIN)


def _token_pair(access: str, refresh: str, expires_at) -> TokenPair:
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires_at=expires_at,
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[AuthResponse],
    responses=ERRORS,
    summary="Create an account",
    description=(
        "Registers a student, academician, recruiter or company admin and returns a "
        "token pair. A role-specific profile is created at the same time, so the "
        "dashboard is usable immediately.\n\n"
        "Institution and platform administrator accounts are provisioned by an "
        "existing administrator and cannot be self-registered."
    ),
)
async def register(
    payload: RegisterRequest, request: Request, response: Response, db: DbSession
) -> dict:
    user = await auth_service.register_user(db, payload, request)
    access, refresh, expires_at, _ = await auth_service.create_session(db, user, request)
    session_payload = await auth_service.build_authenticated_user(db, user)
    await db.commit()
    tokens = _token_pair(access, refresh, expires_at)
    _set_auth_cookies(response, tokens, session_payload["csrf_token"])
    return ok(
        AuthResponse(
            tokens=tokens, session=AuthenticatedUser.model_validate(session_payload)
        )
    )


@router.post(
    "/login",
    response_model=Envelope[AuthResponse],
    responses=ERRORS,
    summary="Sign in",
    description=(
        "Exchanges email and password for an access/refresh token pair.\n\n"
        "Repeated failures lock the account temporarily. The response also carries "
        "the caller's roles, permissions and landing route so the client can render "
        "the right dashboard without a second round trip."
    ),
)
async def login(
    payload: LoginRequest, request: Request, response: Response, db: DbSession
) -> dict:
    user = await auth_service.authenticate(db, payload.email, payload.password, request)
    access, refresh, expires_at, _ = await auth_service.create_session(db, user, request)
    await audit.record(
        db, AuditAction.LOGIN, actor=user, resource_type="user", resource_id=user.id,
        description="Signed in", request=request,
    )
    session_payload = await auth_service.build_authenticated_user(db, user)
    await db.commit()
    tokens = _token_pair(access, refresh, expires_at)
    _set_auth_cookies(response, tokens, session_payload["csrf_token"])
    return ok(
        AuthResponse(
            tokens=tokens, session=AuthenticatedUser.model_validate(session_payload)
        )
    )


@router.post(
    "/refresh",
    response_model=Envelope[TokenPair],
    responses=ERRORS,
    summary="Rotate tokens",
    description=(
        "Exchanges a refresh token for a fresh pair. Tokens are single-use: the old "
        "one is revoked on every call. Replaying a rotated token is treated as theft "
        "and revokes every session for that account."
    ),
)
async def refresh(
    request: Request, response: Response, db: DbSession, payload: RefreshRequest | None = None
) -> dict:
    raw = (payload.refresh_token if payload else None) or request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise TokenError("No refresh token supplied", code="REFRESH_TOKEN_MISSING")
    access, new_refresh, expires_at, _user = await auth_service.rotate_refresh_token(
        db, raw, request
    )
    await db.commit()
    tokens = _token_pair(access, new_refresh, expires_at)
    _set_auth_cookies(response, tokens, None)
    return ok(tokens)


@router.post(
    "/logout",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Sign out",
    description="Revokes the current session, or every session when "
                "`all_sessions` is true.",
)
async def logout(
    request: Request, response: Response, user: CurrentUser, db: DbSession,
    payload: LogoutRequest | None = None,
) -> MessageResponse:
    raw = (payload.refresh_token if payload else None) or request.cookies.get(REFRESH_COOKIE)
    all_sessions = bool(payload and payload.all_sessions)
    count = await auth_service.revoke_session(db, raw, user, all_sessions=all_sessions)
    await audit.record(
        db, AuditAction.LOGOUT, actor=user, resource_type="user", resource_id=user.id,
        description=f"Signed out ({count} session(s) revoked)", request=request,
    )
    await db.commit()
    _clear_auth_cookies(response)
    return MessageResponse(message="Signed out")


@router.get(
    "/me",
    response_model=Envelope[AuthenticatedUser],
    responses=ERRORS,
    summary="Current session",
    description="Returns the authenticated user together with their roles, "
                "effective permissions and profile completion.",
)
async def me(user: CurrentUser, db: DbSession) -> dict:
    payload = await auth_service.build_authenticated_user(db, user)
    return ok(AuthenticatedUser.model_validate(payload))


@router.patch(
    "/me",
    response_model=Envelope[UserOut],
    responses=ERRORS,
    summary="Update account details",
    description="Updates the account-level fields shared by every role. "
                "Role-specific fields live under `/students/me` and `/academicians/me`.",
)
async def update_me(
    payload: UpdateMeRequest, request: Request, user: CurrentUser, db: DbSession
) -> dict:
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(user, field, value)
    if changes:
        await audit.record(
            db, AuditAction.PROFILE_UPDATE, actor=user, resource_type="user",
            resource_id=user.id, description="Account details updated",
            request=request, meta={"fields": sorted(changes)},
        )
    await db.commit()
    await db.refresh(user, ["roles"])
    return ok(UserOut.model_validate(user))


@router.get(
    "/sessions",
    response_model=Envelope[list[SessionOut]],
    responses=ERRORS,
    summary="List active sessions",
    description="Every device currently holding a valid refresh token.",
)
async def list_sessions(request: Request, user: CurrentUser, db: DbSession) -> dict:
    from app.core.security import hash_token

    rows = (
        await db.execute(
            select(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .order_by(UserSession.created_at.desc())
        )
    ).scalars().all()
    current_hash = (
        hash_token(request.cookies[REFRESH_COOKIE])
        if request.cookies.get(REFRESH_COOKIE)
        else None
    )
    return ok(
        [
            SessionOut(
                id=s.id, user_agent=s.user_agent, ip_address=s.ip_address,
                created_at=s.created_at, expires_at=s.expires_at,
                is_current=(s.refresh_token_hash == current_hash),
            )
            for s in rows
        ]
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Revoke a session",
    description="Signs out one device. Useful after losing a laptop or phone.",
)
async def revoke_one_session(
    session_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> MessageResponse:
    from datetime import datetime

    from app.core.exceptions import NotFoundError

    row = (
        await db.execute(
            select(UserSession).where(
                UserSession.id == session_id, UserSession.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Session not found", code="SESSION_NOT_FOUND")
    row.revoked_at = datetime.now(UTC)
    row.revoked_reason = "revoked_by_user"
    await db.commit()
    return MessageResponse(message="Session revoked")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Request a password reset",
    description="Always returns the same response whether or not the address is "
                "registered, so the endpoint cannot be used to enumerate accounts.",
)
async def forgot_password(
    payload: ForgotPasswordRequest, request: Request, db: DbSession
) -> MessageResponse:
    await auth_service.request_password_reset(db, payload.email, request)
    return MessageResponse(
        message="If that email is registered, a reset link is on its way."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Complete a password reset",
    description="Consumes the emailed token, sets the new password and signs out "
                "every existing session.",
)
async def reset_password(
    payload: ResetPasswordRequest, request: Request, db: DbSession
) -> MessageResponse:
    await auth_service.reset_password(db, payload.token, payload.new_password, request)
    return MessageResponse(message="Password updated. Please sign in.")


@router.post(
    "/change-password",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Change password",
    description="Requires the current password. All other sessions are signed out.",
)
async def change_password(
    payload: ChangePasswordRequest, request: Request, response: Response,
    user: CurrentUser, db: DbSession,
) -> MessageResponse:
    await auth_service.change_password(
        db, user, payload.current_password, payload.new_password, request
    )
    _clear_auth_cookies(response)
    return MessageResponse(message="Password changed. Please sign in again.")


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Verify an email address",
    description="Consumes the token from the verification email and activates the account.",
)
async def verify_email(payload: VerifyEmailRequest, db: DbSession) -> MessageResponse:
    await auth_service.verify_email(db, payload.token)
    return MessageResponse(message="Email verified")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Resend the verification email",
    description="Silently does nothing for unknown or already-verified addresses.",
)
async def resend_verification(
    payload: ResendVerificationRequest, db: DbSession
) -> MessageResponse:
    await auth_service.resend_verification(db, payload.email)
    return MessageResponse(message="If verification is pending, a new link has been sent.")
