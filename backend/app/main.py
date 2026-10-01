"""SkillBridge API entry point."""
from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import dispose_engine
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    CSRFMiddleware,
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)

configure_logging()
log = get_logger("startup")

DESCRIPTION = """
**SkillBridge** is an academia-industry collaboration and employability platform.

It connects **students**, **academicians**, **companies**, **institutions** and
**platform administrators** around one flow: assess skills -> find the gap to a
target role -> follow a learning path -> get matched to real opportunities ->
apply -> build verified experience.

### Authentication
Obtain a token pair from `POST /api/v1/auth/login`, then send
`Authorization: Bearer <access_token>`. Access tokens are short lived; rotate
them with `POST /api/v1/auth/refresh`.

### Conventions
* Every successful response is `{"success": true, "data": ...}`.
* Every list endpoint is paginated: `{"data": [...], "meta": {page, page_size, total, ...}}`.
* Every error is `{"success": false, "error": {"code": "...", "message": "..."}}`.

### Responsible use of recommendations
Match scores are decision *support*. They are explainable by construction - every
recommendation carries its contributing factors - and they never make an
autonomous hiring decision. Protected characteristics are excluded from ranking.
"""

TAGS_METADATA: list[dict[str, Any]] = [
    {"name": "Authentication", "description": "Registration, login, tokens, password and email flows."},
    {"name": "Students", "description": "Student profile, skills, skill gaps and dashboard."},
    {"name": "Academicians", "description": "Faculty profile, opportunities and collaborations."},
    {"name": "Skills", "description": "Skill taxonomy, job roles and role requirements."},
    {"name": "Assessments", "description": "Skill assessment engine: browse, attempt, score."},
    {"name": "Opportunities", "description": "Cross-type opportunity search."},
    {"name": "Internships", "description": "Internship postings and applications."},
    {"name": "Jobs", "description": "Job postings and placement pipeline."},
    {"name": "Live Projects", "description": "Industry projects, teams, milestones and submissions."},
    {"name": "Applications", "description": "Application tracking and recruiter review."},
    {"name": "Recommendations", "description": "Explainable AI recommendations."},
    {"name": "Learning", "description": "Programmes, enrolments, certifications and learning paths."},
    {"name": "Mentorship", "description": "Mentors, requests and sessions."},
    {"name": "Events", "description": "Workshops, webinars, hackathons and registrations."},
    {"name": "Research", "description": "Research, consultancy and innovation collaborations."},
    {"name": "Companies", "description": "Company profiles and industry portal."},
    {"name": "Institutions", "description": "Institution administration and student oversight."},
    {"name": "Documents", "description": "Secure upload, access control and download."},
    {"name": "Portfolio", "description": "Digital portfolio, resume builder and resume analysis."},
    {"name": "Notifications", "description": "Notification centre and preferences."},
    {"name": "Messaging", "description": "Permissioned conversations."},
    {"name": "Search", "description": "Global and entity-scoped search."},
    {"name": "Analytics", "description": "Institution, industry and platform analytics + exports."},
    {"name": "Admin", "description": "Platform administration, moderation and audit."},
    {"name": "System", "description": "Health and readiness probes."},
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    problems = settings.validate_runtime()
    if problems:
        for problem in problems:
            log.error("config.invalid", problem=problem)
        if settings.is_production:
            sys.exit("Refusing to start with an insecure configuration")
    log.info(
        "app.starting",
        environment=settings.ENVIRONMENT,
        database="postgresql" if not settings.is_sqlite else "sqlite",
        ai_provider=settings.AI_PROVIDER,
        storage=settings.STORAGE_PROVIDER,
    )
    # Keep the permission catalogue in the database in step with the code.
    from app.services.bootstrap import sync_rbac_catalogue

    await sync_rbac_catalogue()
    log.info("app.started")
    yield
    await dispose_engine()
    log.info("app.stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        summary=settings.APP_SUBTITLE,
        description=DESCRIPTION,
        version="1.0.0",
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        swagger_ui_parameters={"persistAuthorization": True, "docExpansion": "none"},
        contact={"name": "SkillBridge Engineering", "url": settings.FRONTEND_URL},
        license_info={"name": "MIT"},
    )

    # Order matters: the outermost middleware is added last.
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Total-Count", "Content-Disposition"],
        max_age=600,
    )
    if settings.TRUSTED_HOSTS and settings.TRUSTED_HOSTS != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    # Probes are also mounted unprefixed for container orchestrators.
    from app.api.v1.endpoints import health as health_module

    app.include_router(health_module.router, include_in_schema=False)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, Any]:
        return {
            "name": settings.APP_NAME,
            "subtitle": settings.APP_SUBTITLE,
            "version": "1.0.0",
            "docs": "/docs",
            "api": settings.API_V1_PREFIX,
        }

    return app


app = create_app()
