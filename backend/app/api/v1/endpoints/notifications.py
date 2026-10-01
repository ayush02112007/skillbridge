"""Notification centre and delivery preferences."""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.deps import ActiveUser, DbSession
from app.models.enums import NotificationCategory, NotificationChannel
from app.models.notification import Notification, NotificationPreference
from app.schemas.common import (
    APIModel,
    Envelope,
    ErrorResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.services import notification as notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])

ERRORS: dict[int | str, dict[str, Any]] = {401: {"model": ErrorResponse, "description": "Not authenticated"}}


class NotificationOut(APIModel):
    id: uuid.UUID
    category: NotificationCategory
    title: str
    body: str = ""
    action_url: str | None = None
    action_label: str | None = None
    icon: str | None = None
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    read_at: object | None = None
    created_at: object


class NotificationSummary(APIModel):
    unread: int
    by_category: dict[str, int]


class MarkReadIn(APIModel):
    notification_ids: list[uuid.UUID] | None = None


class PreferenceIn(APIModel):
    category: NotificationCategory
    channel: NotificationChannel
    is_enabled: bool


class PreferencesIn(APIModel):
    preferences: list[PreferenceIn]


class PreferenceOut(APIModel):
    category: NotificationCategory
    channel: NotificationChannel
    is_enabled: bool


@router.get(
    "",
    response_model=Page[NotificationOut],
    responses=ERRORS,
    summary="My notifications",
)
async def list_notifications(
    db: DbSession,
    user: ActiveUser,
    page: Annotated[PaginationParams, Depends(pagination)],
    category: NotificationCategory | None = None,
    unread_only: bool = False,
) -> Page[NotificationOut]:
    stmt = select(Notification).where(Notification.user_id == user.id)
    if category:
        stmt = stmt.where(Notification.category == category)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Notification.created_at.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
    ).scalars().all()
    return Page.build(
        [NotificationOut.model_validate(r) for r in rows], total, page.page, page.page_size
    )


@router.get(
    "/summary",
    response_model=Envelope[NotificationSummary],
    responses=ERRORS,
    summary="Unread summary",
    description="Drives the badge on the notification bell.",
)
async def summary(db: DbSession, user: ActiveUser) -> dict:
    rows = (
        await db.execute(
            select(Notification.category, func.count())
            .where(Notification.user_id == user.id, Notification.read_at.is_(None))
            .group_by(Notification.category)
        )
    ).all()
    by_category = {c.value: n for c, n in rows}
    return ok(
        NotificationSummary(unread=sum(by_category.values()), by_category=by_category)
    )


@router.post(
    "/read",
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Mark notifications read",
    description="Marks the listed notifications read, or all of them when the "
                "list is omitted.",
)
async def mark_read(payload: MarkReadIn, db: DbSession, user: ActiveUser) -> dict:
    count = await notification_service.mark_read(db, user.id, payload.notification_ids)
    await db.commit()
    return ok({"marked_read": count})


@router.get(
    "/preferences",
    response_model=Envelope[list[PreferenceOut]],
    responses=ERRORS,
    summary="My notification preferences",
)
async def get_preferences(db: DbSession, user: ActiveUser) -> dict:
    rows = (
        await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user.id)
        )
    ).scalars().all()
    return ok([PreferenceOut.model_validate(r) for r in rows])


@router.put(
    "/preferences",
    response_model=Envelope[list[PreferenceOut]],
    responses=ERRORS,
    summary="Update notification preferences",
    description="Per category and channel. Disabling a channel stops delivery "
                "for that category immediately.",
)
async def update_preferences(
    payload: PreferencesIn, db: DbSession, user: ActiveUser
) -> dict:
    existing = {
        (p.category, p.channel): p
        for p in (
            await db.execute(
                select(NotificationPreference).where(
                    NotificationPreference.user_id == user.id
                )
            )
        ).scalars()
    }
    for entry in payload.preferences:
        row = existing.get((entry.category, entry.channel))
        if row is None:
            row = NotificationPreference(
                user_id=user.id, category=entry.category, channel=entry.channel
            )
            db.add(row)
        row.is_enabled = entry.is_enabled
    await db.commit()
    rows = (
        await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user.id)
        )
    ).scalars().all()
    return ok([PreferenceOut.model_validate(r) for r in rows])
