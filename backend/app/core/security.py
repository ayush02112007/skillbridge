"""Password hashing, JWT issuing/verification and one-time token helpers."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings
from app.core.exceptions import TokenError, ValidationError

TokenType = Literal["access", "refresh", "verify_email", "reset_password"]

# Argon2id - OWASP recommended parameters for interactive logins.
_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)

_COMMON_PASSWORDS = {
    "password", "password1", "12345678", "123456789", "qwertyuiop", "letmein123",
    "welcome123", "admin12345", "changeme123", "iloveyou123", "passw0rd!",
}


# --------------------------------------------------------------- passwords --
def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:  # pragma: no cover
        return True


def validate_password_strength(password: str, *, email: str | None = None) -> None:
    """Server-side password policy. Raises ValidationError with all problems."""
    problems: list[str] = []
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        problems.append(f"must be at least {settings.PASSWORD_MIN_LENGTH} characters")
    if len(password) > 128:
        problems.append("must be at most 128 characters")
    if not any(c.islower() for c in password):
        problems.append("must contain a lowercase letter")
    if not any(c.isupper() for c in password):
        problems.append("must contain an uppercase letter")
    if not any(c.isdigit() for c in password):
        problems.append("must contain a digit")
    if not any(not c.isalnum() for c in password):
        problems.append("must contain a symbol")
    if password.lower() in _COMMON_PASSWORDS:
        problems.append("is too common")
    if email and email.split("@")[0].lower() in password.lower():
        problems.append("must not contain your email address")
    if problems:
        raise ValidationError(
            "Password " + "; ".join(problems),
            code="WEAK_PASSWORD",
            details={"requirements": problems},
        )


# ------------------------------------------------------------------- jwt ----
def _secret_for(token_type: TokenType) -> str:
    # "refresh" here is a token *kind*, not a secret: access and refresh tokens
    # are signed with different keys so one cannot be replayed as the other.
    return settings.JWT_REFRESH_SECRET if token_type == "refresh" else settings.JWT_SECRET  # noqa: S105


def create_token(
    subject: str | uuid.UUID,
    token_type: TokenType,
    expires_delta: timedelta,
    *,
    extra_claims: dict[str, Any] | None = None,
    jti: str | None = None,
) -> tuple[str, str, datetime]:
    """Return ``(token, jti, expires_at)``."""
    now = datetime.now(UTC)
    expires_at = now + expires_delta
    token_id = jti or uuid.uuid4().hex
    payload: dict[str, Any] = {
        "sub": str(subject),
        "typ": token_type,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": token_id,
        "iss": settings.APP_NAME,
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, _secret_for(token_type), algorithm=settings.JWT_ALGORITHM)
    return token, token_id, expires_at


def create_access_token(
    subject: str | uuid.UUID, *, roles: list[str], session_id: str | None = None
) -> tuple[str, datetime]:
    token, _, exp = create_token(
        subject,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"roles": roles, "sid": session_id},
    )
    return token, exp


def create_refresh_token(
    subject: str | uuid.UUID, *, session_id: str
) -> tuple[str, str, datetime]:
    return create_token(
        subject,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        extra_claims={"sid": session_id},
    )


def decode_token(token: str, token_type: TokenType) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            _secret_for(token_type),
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.APP_NAME,
            options={"require": ["exp", "sub", "typ", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired", code="TOKEN_EXPIRED") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError() from exc
    if payload.get("typ") != token_type:
        raise TokenError("Token has the wrong type", code="TOKEN_WRONG_TYPE")
    return payload


# -------------------------------------------------- opaque one-time tokens --
def generate_url_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(raw: str) -> str:
    """Store only a digest of one-time tokens so a DB leak is not exploitable."""
    return hashlib.sha256(raw.encode()).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


# --------------------------------------------------------------- csrf ------
def generate_csrf_token() -> str:
    return secrets.token_urlsafe(24)


def sign_value(value: str) -> str:
    sig = hmac.new(settings.JWT_SECRET.encode(), value.encode(), hashlib.sha256).digest()
    return f"{value}.{base64.urlsafe_b64encode(sig).decode().rstrip('=')}"


def unsign_value(signed: str) -> str | None:
    if "." not in signed:
        return None
    value, _, _sig = signed.rpartition(".")
    if constant_time_compare(sign_value(value), signed):
        return value
    return None
