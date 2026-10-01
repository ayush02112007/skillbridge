"""Async SQLAlchemy engine, session factory and declarative base.

The mapping layer is deliberately dialect-portable: PostgreSQL is the target for
Docker/production, while SQLite is supported so the test-suite and a zero-infra
local run work identically.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, event, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON, TypeDecorator, Uuid

from app.core.config import settings


# Portable column types -------------------------------------------------------
class JSONB(TypeDecorator):
    """JSONB on PostgreSQL, plain JSON everywhere else.

    Declared as a ``TypeDecorator`` rather than ``JSON().with_variant(...)`` so
    Alembic renders it as a single importable symbol in migrations.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.JSONB())
        return dialect.type_descriptor(JSON())


JSONType = JSONB()
# Native uuid on PostgreSQL, CHAR(32) elsewhere - handled by SQLAlchemy's Uuid.
GUID = Uuid(as_uuid=True)

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata_obj = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(AsyncAttrs, DeclarativeBase):
    metadata = metadata_obj
    type_annotation_map = {dict[str, Any]: JSONType, list[Any]: JSONType}

    def to_dict(self) -> dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        pk = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={pk}>"


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4, sort_order=-100
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow,
        nullable=False, index=True, sort_order=100,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow,
        onupdate=utcnow, nullable=False, sort_order=101,
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True, sort_order=102
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = utcnow()


# Engine ----------------------------------------------------------------------
def _engine_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "echo": settings.DB_ECHO,
        "future": True,
        "pool_pre_ping": True,
    }
    if not settings.is_sqlite:
        kwargs.update(
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
        )
    return kwargs


engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs())

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@event.listens_for(engine.sync_engine, "connect")
def _sqlite_pragmas(dbapi_connection: Any, _record: Any) -> None:
    """Enforce foreign keys on SQLite (off by default) so constraints behave
    the same way they do on PostgreSQL."""
    if settings.is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def ping_database() -> bool:
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # pragma: no cover - health probe
        return False


async def dispose_engine() -> None:
    await engine.dispose()
