"""Analytics and report exports for institutions, industry and the platform."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import (
    AdminUser,
    DbSession,
    InstitutionAdminUser,
    RecruiterCompanyId,
    RecruiterUser,
    require_permission,
)
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.application import Application
from app.models.enums import AuditAction, RoleName
from app.models.opportunity import Opportunity
from app.models.organization import Institution
from app.models.profile import StudentProfile
from app.schemas.common import Envelope, ErrorResponse, ok
from app.services import analytics as analytics_service
from app.services import audit

router = APIRouter(prefix="/analytics", tags=["Analytics"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
}


@router.get(
    "/institution",
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Institution analytics",
    description=(
        "Student readiness, placement and internship performance, skill "
        "distribution, the demand-versus-supply gap against live industry "
        "postings, department breakdowns and twelve-month trends.\n\n"
        "Every number is computed from live records; nothing is hard-coded."
    ),
)
async def institution_analytics(
    db: DbSession,
    user: InstitutionAdminUser,
    institution_id: Annotated[
        uuid.UUID | None, Query(description="Platform admins only")
    ] = None,
) -> dict:
    target = institution_id or user.institution_id
    if target is None:
        raise NotFoundError(
            "Your account is not linked to an institution", code="INSTITUTION_NOT_LINKED"
        )
    if (
        institution_id
        and institution_id != user.institution_id
        and RoleName.SUPER_ADMIN.value not in user.role_names
    ):
        raise PermissionDeniedError(
            "You can only view your own institution", code="CROSS_INSTITUTION_ACCESS"
        )
    return ok(await analytics_service.institution_analytics(db, target))


@router.get(
    "/industry",
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Industry analytics",
    description=(
        "Applicant volume and quality, the hiring funnel, time to hire, the "
        "skills applicants hold and the skills they most often lack."
    ),
)
async def industry_analytics(
    db: DbSession, user: RecruiterUser, company_id: RecruiterCompanyId
) -> dict:
    return ok(await analytics_service.industry_analytics(db, company_id))


@router.get(
    "/platform",
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Platform analytics",
    description="Platform-wide totals and growth. Restricted to platform admins.",
)
async def platform_analytics(db: DbSession, _admin: AdminUser) -> dict:
    return ok(await analytics_service.platform_analytics(db))


# ----------------------------------------------------------------- exports
REPORTS = {
    "placement": "Placement Report",
    "internship": "Internship Report",
    "skills": "Skills Report",
    "student-readiness": "Student Readiness Report",
    "industry-demand": "Industry Demand Report",
}


async def _institution_report_rows(
    db, institution_id: uuid.UUID, report: str
) -> list[tuple[str, list[dict[str, Any]]]]:
    data = await analytics_service.institution_analytics(db, institution_id)

    if report == "skills":
        return [
            ("Top skills held by students", data["top_skills"]),
            ("Most common skill gaps", data["skill_gaps"]),
            ("Industry demand vs student supply", data["demand_vs_supply"]),
        ]
    if report == "industry-demand":
        return [
            ("Industry demand vs student supply", data["demand_vs_supply"]),
            ("Top hiring companies", data["top_hiring_companies"]),
        ]
    if report == "student-readiness":
        students = (
            await db.execute(
                select(StudentProfile)
                .where(
                    StudentProfile.institution_id == institution_id,
                    StudentProfile.deleted_at.is_(None),
                )
                .options(selectinload(StudentProfile.user))
                .order_by(StudentProfile.skill_readiness_score.desc())
            )
        ).scalars().all()
        return [
            (
                "Student readiness",
                [
                    {
                        "name": s.user.full_name if s.user else "",
                        "graduation_year": s.graduation_year or "",
                        "cgpa": s.cgpa or "",
                        "readiness_score": s.skill_readiness_score,
                        "profile_completion": s.profile_completion,
                        "placed": "Yes" if s.is_placed else "No",
                    }
                    for s in students
                ],
            ),
            ("Readiness distribution",
             [{"band": k, "students": v} for k, v in data["readiness_distribution"].items()]),
        ]

    # Placement / internship: one row per application.
    from app.models.enums import OpportunityType

    stmt = (
        select(Application)
        .join(Opportunity, Opportunity.id == Application.opportunity_id)
        .join(StudentProfile, StudentProfile.id == Application.student_id)
        .where(StudentProfile.institution_id == institution_id)
        .options(
            selectinload(Application.opportunity).selectinload(Opportunity.company),
            selectinload(Application.student).selectinload(StudentProfile.user),
        )
    )
    if report == "internship":
        stmt = stmt.where(Opportunity.opportunity_type == OpportunityType.INTERNSHIP)
    elif report == "placement":
        stmt = stmt.where(Opportunity.opportunity_type == OpportunityType.JOB)

    rows = (await db.execute(stmt.order_by(Application.created_at.desc()))).scalars().all()
    return [
        (
            REPORTS[report],
            [
                {
                    "student": (
                        r.student.user.full_name if r.student and r.student.user else ""
                    ),
                    "graduation_year": (r.student.graduation_year if r.student else "") or "",
                    "opportunity": r.opportunity.title if r.opportunity else "",
                    "company": (
                        r.opportunity.company.name
                        if r.opportunity and r.opportunity.company
                        else ""
                    ),
                    "status": r.status.value,
                    "match_score": r.match_score,
                    "applied_on": r.submitted_at.strftime("%Y-%m-%d")
                    if r.submitted_at
                    else "",
                    "decided_on": r.decided_at.strftime("%Y-%m-%d") if r.decided_at else "",
                }
                for r in rows
            ],
        ),
        ("Summary", [data["summary"]]),
    ]


@router.get(
    "/reports/{report}",
    responses={
        **ERRORS,
        200: {"content": {"text/csv": {}, "application/pdf": {}}},
    },
    summary="Export a report",
    description=(
        "Exports placement, internship, skills, student-readiness or "
        "industry-demand data as **CSV** or **PDF**.\n\n"
        "Institution admins export their own institution; platform admins may "
        "target any institution. Every export is written to the audit log."
    ),
)
async def export_report(
    report: str,
    request: Request,
    db: DbSession,
    user: Annotated[object, Depends(require_permission("report:export"))],
    fmt: Annotated[str, Query(pattern="^(csv|pdf)$", alias="format")] = "csv",
    institution_id: uuid.UUID | None = None,
) -> Response:
    if report not in REPORTS:
        raise NotFoundError(
            f"Unknown report. Available: {', '.join(sorted(REPORTS))}",
            code="REPORT_NOT_FOUND",
        )
    target = institution_id or user.institution_id
    if target is None:
        raise NotFoundError(
            "Your account is not linked to an institution", code="INSTITUTION_NOT_LINKED"
        )
    if (
        institution_id
        and institution_id != user.institution_id
        and RoleName.SUPER_ADMIN.value not in user.role_names
    ):
        raise PermissionDeniedError(
            "You can only export your own institution", code="CROSS_INSTITUTION_ACCESS"
        )

    sections = await _institution_report_rows(db, target, report)
    institution = await db.get(Institution, target)
    title = f"{REPORTS[report]} — {institution.name if institution else ''}".strip(" —")
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    filename = f"skillbridge-{report}-{stamp}.{fmt}"

    await audit.record(
        db, AuditAction.EXPORT, actor=user, resource_type="report",
        description=f"Exported {report} as {fmt.upper()}", request=request,
        meta={"institution_id": str(target)},
    )
    await db.commit()

    if fmt == "csv":
        body = "\n\n".join(
            f"# {name}\n{analytics_service.to_csv(rows)}" for name, rows in sections
        )
        return Response(
            content=body,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    pdf = analytics_service.to_pdf(title, sections)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
