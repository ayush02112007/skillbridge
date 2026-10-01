"""Identity, RBAC and session models."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import RoleName, UserStatus

if TYPE_CHECKING:
    from app.models.organization import Company, Institution
    from app.models.profile import AcademicianProfile, StudentProfile

# Many-to-many join tables -----------------------------------------------------
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", GUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", GUID, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("granted_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", GUID, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", GUID, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(UUIDMixin, TimestampMixin, Base):
    """A single capability, named ``resource:action`` (e.g. ``job:create``)."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")

    # Reverse side is never needed at read time; keep it lazy to avoid
    # loading the whole role graph whenever a permission is fetched.
    roles: Mapped[list[Role]] = relationship(
        secondary=role_permissions, back_populates="permissions", lazy="noload"
    )


class Role(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    name: Mapped[RoleName] = mapped_column(
        SAEnum(RoleName, native_enum=False, length=32), unique=True, nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")
    is_assignable_on_signup: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions, back_populates="roles", lazy="selectin"
    )
    users: Mapped[list[User]] = relationship(
        secondary=user_roles, back_populates="roles", lazy="noload"
    )


class User(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email_lower", text("lower(email)"), unique=True),
        CheckConstraint("length(email) >= 5", name="email_min_length"),
        CheckConstraint("failed_login_attempts >= 0", name="failed_attempts_non_negative"),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    avatar_url: Mapped[str | None] = mapped_column(String(512))

    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, native_enum=False, length=32),
        default=UserStatus.PENDING_VERIFICATION, nullable=False, index=True,
    )
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[str | None] = mapped_column(String(64))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    timezone_name: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)

    # Organisation membership (an account belongs to at most one of each).
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("institutions.id", ondelete="SET NULL"), index=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )

    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles, back_populates="users", lazy="selectin"
    )
    institution: Mapped[Institution | None] = relationship(
        back_populates="members", foreign_keys=[institution_id], lazy="selectin"
    )
    company: Mapped[Company | None] = relationship(
        back_populates="members", foreign_keys=[company_id], lazy="selectin"
    )
    student_profile: Mapped[StudentProfile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="noload"
    )
    academician_profile: Mapped[AcademicianProfile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="noload"
    )
    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="noload"
    )

    # ------------------------------------------------------------- helpers --
    @property
    def role_names(self) -> list[str]:
        return [r.name.value for r in self.roles]

    @property
    def primary_role(self) -> str | None:
        return self.roles[0].name.value if self.roles else None

    def has_role(self, *names: RoleName | str) -> bool:
        wanted = {n.value if isinstance(n, RoleName) else str(n) for n in names}
        return bool(wanted & set(self.role_names))

    @property
    def permission_codes(self) -> set[str]:
        return {p.code for role in self.roles for p in role.permissions}

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE and self.deleted_at is None


class UserSession(UUIDMixin, TimestampMixin, Base):
    """One row per refresh-token family; enables rotation + revocation."""

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_active", "user_id", "revoked_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(String(80))
    rotated_from: Mapped[uuid.UUID | None] = mapped_column(GUID)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(64))

    user: Mapped[User] = relationship(back_populates="sessions", lazy="noload")


class OneTimeToken(UUIDMixin, TimestampMixin, Base):
    """Email-verification and password-reset tokens (digest stored, never raw)."""

    __tablename__ = "one_time_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="token_hash_unique"),
        Index("ix_one_time_tokens_user_purpose", "user_id", "purpose"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)
