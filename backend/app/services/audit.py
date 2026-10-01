"""Audit trail writer.

Sensitive actions are recorded append-only. Writing an audit entry must never
break the action it describes, so failures are logged and swallowed.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit import AuditAction, AuditLog
from app.models.user import User

log = get_logger("audit")

_SENSITIVE_META_KEYS = {"password", "token", "secret", "api_key", "hashed_password"}


def _clean(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not meta:
        return {}
    return {
        k: ("***" if k.lower() in _SENSITIVE_META_KEYS else v)
        for k, v in meta.items()
    }


async def record(
    db: AsyncSession,
    action: AuditAction,
    *,
    actor: User | None = None,
    actor_email: str | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    description: str = "",
    request: Request | None = None,
    status: str = "SUCCESS",
    meta: dict[str, Any] | None = None,
) -> None:
    try:
        ip = user_agent = request_id = None
        if request is not None:
            forwarded = request.headers.get("x-forwarded-for")
            ip = (
                forwarded.split(",")[0].strip()[:64]
                if forwarded
                else (request.client.host if request.client else None)
            )
            ua = request.headers.get("user-agent")
            user_agent = ua[:300] if ua else None
            request_id = getattr(request.state, "request_id", None)

        db.add(
            AuditLog(
                actor_id=actor.id if actor else None,
                actor_email=(actor.email if actor else actor_email),
                actor_roles=(actor.role_names if actor else []),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description[:400],
                ip_address=ip,
                user_agent=user_agent,
                request_id=request_id,
                status=status,
                meta=_clean(meta),
            )
        )
    except Exception as exc:  # pragma: no cover - never break the caller
        log.error("audit.write_failed", action=str(action), error=str(exc)[:200])
