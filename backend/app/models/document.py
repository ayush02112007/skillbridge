"""Uploaded documents. Objects are private by default and served via signed URLs."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import DocumentType, ScanStatus, Visibility


class Document(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="document_size_positive"),
        Index("ix_documents_owner_type", "owner_id", "document_type"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, native_enum=False, length=32),
        default=DocumentType.OTHER, nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Opaque storage key - the filesystem/bucket path is never exposed to clients.
    storage_key: Mapped[str] = mapped_column(String(400), unique=True, nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(20), default="local", nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    visibility: Mapped[Visibility] = mapped_column(
        SAEnum(Visibility, native_enum=False, length=24),
        default=Visibility.PRIVATE, nullable=False,
    )
    scan_status: Mapped[ScanStatus] = mapped_column(
        SAEnum(ScanStatus, native_enum=False, length=16),
        default=ScanStatus.PENDING, nullable=False, index=True,
    )
    scan_detail: Mapped[str | None] = mapped_column(String(255))
    is_primary_resume: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Text extracted from a resume, reused by the resume analyser.
    extracted_text: Mapped[str | None] = mapped_column(Text)
    extraction_status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DocumentAccessGrant(UUIDMixin, TimestampMixin, Base):
    """Explicit, revocable access for a non-owner (e.g. a recruiter reviewing a CV)."""

    __tablename__ = "document_access_grants"

    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    granted_to_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    reason: Mapped[str] = mapped_column(String(200), default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
