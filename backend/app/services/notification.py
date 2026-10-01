"""Notification fan-out across in-app and email channels.

One call site per domain event; this module decides which channels the
recipient has enabled and records the result.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.enums import NotificationCategory, NotificationChannel
from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.services.email import send_email

log = get_logger("notifications")


def _now() -> datetime:
    return datetime.now(UTC)


async def _channel_enabled(
    db: AsyncSession, user_id: uuid.UUID, category: NotificationCategory,
    channel: NotificationChannel,
) -> bool:
    row = (
        await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.category == category,
                NotificationPreference.channel == channel,
            )
        )
    ).scalar_one_or_none()
    if row is not None:
        return row.is_enabled
    # No stored preference: in-app on, email on only for high-signal categories.
    return channel == NotificationChannel.IN_APP or category in (
        NotificationCategory.APPLICATION,
        NotificationCategory.MENTORSHIP,
        NotificationCategory.SYSTEM,
    )


async def notify(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    category: NotificationCategory,
    title: str,
    body: str = "",
    action_url: str | None = None,
    action_label: str | None = None,
    icon: str | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    email_template: str | None = None,
    email_context: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> Notification | None:
    """Create an in-app notification and, if enabled, send the email too."""
    notification: Notification | None = None
    if await _channel_enabled(db, user_id, category, NotificationChannel.IN_APP):
        notification = Notification(
            user_id=user_id, category=category, title=title[:200], body=body,
            action_url=action_url, action_label=action_label, icon=icon,
            resource_type=resource_type, resource_id=resource_id, meta=meta or {},
        )
        db.add(notification)
        await db.flush()

    if email_template and await _channel_enabled(
        db, user_id, category, NotificationChannel.EMAIL
    ):
        user = await db.get(User, user_id)
        if user and user.email:
            sent = await send_email(
                user.email, email_template, db=db, user_id=user.id,
                name=user.full_name.split()[0] if user.full_name else "there",
                **(email_context or {}),
            )
            if notification is not None and sent:
                notification.emailed_at = _now()
    return notification


async def notify_many(
    db: AsyncSession, user_ids: Iterable[uuid.UUID], **kwargs: Any
) -> int:
    count = 0
    for user_id in set(user_ids):
        if await notify(db, user_id, **kwargs):
            count += 1
    return count


async def unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
    ).scalar_one()


async def mark_read(
    db: AsyncSession, user_id: uuid.UUID, notification_ids: Sequence[uuid.UUID] | None
) -> int:
    stmt = (
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=_now())
    )
    if notification_ids:
        stmt = stmt.where(Notification.id.in_(list(notification_ids)))
    result = await db.execute(stmt)
    return result.rowcount or 0
