"""In-app + email notifications and per-user delivery preferences."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import GUID, Base, TimestampMixin, UUIDMixin
from app.models.enums import NotificationCategory, NotificationChannel


class Notification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "read_at"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[NotificationCategory] = mapped_column(
        SAEnum(NotificationCategory, native_enum=False, length=24),
        default=NotificationCategory.SYSTEM, nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    action_url: Mapped[str | None] = mapped_column(String(400))
    action_label: Mapped[str | None] = mapped_column(String(80))
    icon: Mapped[str | None] = mapped_column(String(40))
    # Where this notification came from, e.g. ("application", <uuid>).
    resource_type: Mapped[str | None] = mapped_column(String(60))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(GUID, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)

    @property
    def is_read(self) -> bool:
        return self.read_at is not None


class NotificationPreference(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "category", "channel", name="notification_preference_unique"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[NotificationCategory] = mapped_column(
        SAEnum(NotificationCategory, native_enum=False, length=24), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        SAEnum(NotificationChannel, native_enum=False, length=16), nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EmailLog(UUIDMixin, TimestampMixin, Base):
    """Every outbound email, for support and deliverability debugging."""

    __tablename__ = "email_logs"

    to_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    template: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), default="console", nullable=False)
    # QUEUED | SENT | FAILED
    status: Mapped[str] = mapped_column(String(20), default="QUEUED", nullable=False, index=True)
    error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL")
    )
