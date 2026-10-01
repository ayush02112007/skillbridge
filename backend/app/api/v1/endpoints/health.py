"""Liveness and readiness probes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response, status

from app.core.cache import cache_ping
from app.core.config import settings
from app.core.database import ping_database

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    summary="Liveness probe",
    description="Returns 200 whenever the process is running. Never touches "
                "dependencies, so it is safe as a container liveness check.",
)
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
    }


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Verifies the database and cache. Returns 503 when a hard "
                "dependency (the database) is unreachable.",
)
async def ready(response: Response) -> dict[str, Any]:
    db_ok = await ping_database()
    cache_ok = await cache_ping()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if db_ok else "degraded",
        "checks": {
            "database": "ok" if db_ok else "unavailable",
            # Redis is optional: the app falls back to an in-process cache.
            "cache": "ok" if cache_ok else "fallback:in-memory",
        },
    }
