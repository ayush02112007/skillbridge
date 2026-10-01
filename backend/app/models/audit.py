"""Append-only audit trail and saved searches."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import GUID, Base, TimestampMixin, UUIDMixin
from app.models.enums import AuditAction


class AuditLog(UUIDMixin, TimestampMixin, Base):
    """Immutable record of a sensitive action. Never updated, never deleted."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor_created", "actor_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    actor_email: Mapped[str | None] = mapped_column(String(255))
    actor_roles: Mapped[list[Any]] = mapped_column(default=list)
    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, native_enum=False, length=40), nullable=False, index=True
    )
    resource_type: Mapped[str | None] = mapped_column(String(60))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(GUID)
    description: Mapped[str] = mapped_column(String(400), default="")
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS", nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)


class SavedSearch(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "saved_searches"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    entity: Mapped[str] = mapped_column(String(40), default="opportunity", nullable=False)
    query: Mapped[str] = mapped_column(String(300), default="")
    filters: Mapped[dict[str, Any]] = mapped_column(default=dict)
    notify_on_new: Mapped[bool] = mapped_column(default=False, nullable=False)
