"""Analytics aggregation for institution, industry and platform dashboards.

Every figure here is computed from live rows - there are no hard-coded numbers
anywhere in the product. Where a metric cannot be computed (no data yet), the
API returns zero or an empty series rather than an invented value.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.application import Application
from app.models.assessment import AssessmentAttempt
from app.models.enums import (
    ApplicationStatus,
    AttemptStatus,
    OpportunityStatus,
    OpportunityType,
)
from app.models.event import Event
from app.models.learning import Enrollment, StudentCertification
from app.models.opportunity import Opportunity, OpportunitySkill
from app.models.organization import Company, Department, IndustryPartnership, Institution
from app.models.profile import StudentProfile
from app.models.skill import Skill, SkillGapAnalysis, SkillGapItem, StudentSkill
from app.models.user import User

log = get_logger("analytics")


def _now() -> datetime:
    return datetime.now(UTC)


async def _scalar(db: AsyncSession, stmt: Select) -> int:
    return (await db.execute(stmt)).scalar_one() or 0


def _month_key(value: datetime | None) -> str:
    return (value or _now()).strftime("%Y-%m")


def _last_months(count: int = 12) -> list[str]:
    today = _now().replace(day=1)
    months: list[str] = []
    for offset in range(count - 1, -1, -1):
        month = today
        for _ in range(offset):
            month = (month - timedelta(days=1)).replace(day=1)
        months.append(month.strftime("%Y-%m"))
    return months


# =============================================================== institution
async def institution_analytics(
    db: AsyncSession, institution_id: uuid.UUID
) -> dict[str, Any]:
    student_ids_stmt = select(StudentProfile.id).where(
        StudentProfile.institution_id == institution_id,
        StudentProfile.deleted_at.is_(None),
    )

    total_students = await _scalar(
        db, select(func.count()).select_from(student_ids_stmt.subquery())
    )
    placed = await _scalar(
        db,
        select(func.count())
        .select_from(StudentProfile)
        .where(
            StudentProfile.institution_id == institution_id,
            StudentProfile.is_placed.is_(True),
            StudentProfile.deleted_at.is_(None),
        ),
    )
    avg_readiness = (
        await db.execute(
            select(func.avg(StudentProfile.skill_readiness_score)).where(
                StudentProfile.institution_id == institution_id,
                StudentProfile.deleted_at.is_(None),
            )
        )
    ).scalar() or 0.0
    avg_completion = (
        await db.execute(
            select(func.avg(StudentProfile.profile_completion)).where(
                StudentProfile.institution_id == institution_id,
                StudentProfile.deleted_at.is_(None),
            )
        )
    ).scalar() or 0.0

    # ------------------------------------------------------ applications --
    application_rows = (
        await db.execute(
            select(Application.status, func.count())
            .where(Application.student_id.in_(student_ids_stmt))
            .group_by(Application.status)
        )
    ).all()
    by_status = {s.value: c for s, c in application_rows}
    total_applications = sum(by_status.values())

    internship_participants = await _scalar(
        db,
        select(func.count(func.distinct(Application.student_id)))
        .select_from(Application)
        .join(Opportunity, Opportunity.id == Application.opportunity_id)
        .where(
            Application.student_id.in_(student_ids_stmt),
            Opportunity.opportunity_type == OpportunityType.INTERNSHIP,
        ),
    )
    internships_secured = await _scalar(
        db,
        select(func.count())
        .select_from(Application)
        .join(Opportunity, Opportunity.id == Application.opportunity_id)
        .where(
            Application.student_id.in_(student_ids_stmt),
            Opportunity.opportunity_type == OpportunityType.INTERNSHIP,
            Application.status == ApplicationStatus.SELECTED,
        ),
    )

    # ------------------------------------------------------- skill supply --
    supply_rows = (
        await db.execute(
            select(Skill.id, Skill.name, func.count(StudentSkill.id))
            .join(StudentSkill, StudentSkill.skill_id == Skill.id)
            .where(StudentSkill.student_id.in_(student_ids_stmt))
            .group_by(Skill.id, Skill.name)
            .order_by(func.count(StudentSkill.id).desc())
            .limit(40)
        )
    ).all()
    supply = {sid: (name, count) for sid, name, count in supply_rows}

    demand_rows = (
        await db.execute(
            select(Skill.id, Skill.name, func.count(OpportunitySkill.id))
            .join(OpportunitySkill, OpportunitySkill.skill_id == Skill.id)
            .join(Opportunity, Opportunity.id == OpportunitySkill.opportunity_id)
            .where(
                Opportunity.status == OpportunityStatus.PUBLISHED,
                Opportunity.deleted_at.is_(None),
            )
            .group_by(Skill.id, Skill.name)
            .order_by(func.count(OpportunitySkill.id).desc())
            .limit(40)
        )
    ).all()
    demand = {sid: (name, count) for sid, name, count in demand_rows}

    # Demand vs supply: where the institution's cohort is short of the market.
    demand_vs_supply = []
    for skill_id, (name, demand_count) in demand.items():
        supply_count = supply.get(skill_id, (name, 0))[1]
        coverage = (
            round(supply_count / total_students * 100, 1) if total_students else 0.0
        )
        demand_vs_supply.append(
            {
                "skill_id": str(skill_id),
                "skill": name,
                "industry_demand": demand_count,
                "student_supply": supply_count,
                "coverage_percentage": coverage,
                "shortfall": max(0, demand_count - supply_count),
            }
        )
    demand_vs_supply.sort(key=lambda r: -r["shortfall"])

    # --------------------------------------------------------- skill gaps --
    gap_rows = (
        await db.execute(
            select(Skill.name, func.count(SkillGapItem.id))
            .join(SkillGapItem, SkillGapItem.skill_id == Skill.id)
            .join(SkillGapAnalysis, SkillGapAnalysis.id == SkillGapItem.analysis_id)
            .where(
                SkillGapAnalysis.student_id.in_(student_ids_stmt),
                SkillGapItem.status.in_(["MISSING", "WEAK"]),
            )
            .group_by(Skill.name)
            .order_by(func.count(SkillGapItem.id).desc())
            .limit(15)
        )
    ).all()

    # ------------------------------------------------------- distribution --
    readiness_bands = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
    scores = (
        await db.execute(
            select(StudentProfile.skill_readiness_score).where(
                StudentProfile.institution_id == institution_id,
                StudentProfile.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    for score in scores:
        if score <= 25:
            readiness_bands["0-25"] += 1
        elif score <= 50:
            readiness_bands["26-50"] += 1
        elif score <= 75:
            readiness_bands["51-75"] += 1
        else:
            readiness_bands["76-100"] += 1

    # ------------------------------------------------------- departments ---
    department_rows = (
        await db.execute(
            select(
                Department.name,
                func.count(StudentProfile.id),
                func.avg(StudentProfile.skill_readiness_score),
                func.sum(case((StudentProfile.is_placed.is_(True), 1), else_=0)),
            )
            .join(Department, Department.id == StudentProfile.department_id)
            .where(
                StudentProfile.institution_id == institution_id,
                StudentProfile.deleted_at.is_(None),
            )
            .group_by(Department.name)
        )
    ).all()

    # ----------------------------------------------------------- trends ----
    months = _last_months(12)
    application_dates = (
        await db.execute(
            select(Application.created_at, Opportunity.opportunity_type)
            .join(Opportunity, Opportunity.id == Application.opportunity_id)
            .where(Application.student_id.in_(student_ids_stmt))
        )
    ).all()
    placement_dates = (
        await db.execute(
            select(Application.decided_at)
            .where(
                Application.student_id.in_(student_ids_stmt),
                Application.status == ApplicationStatus.SELECTED,
            )
        )
    ).scalars().all()

    application_trend = {m: 0 for m in months}
    internship_trend = {m: 0 for m in months}
    for created_at, kind in application_dates:
        key = _month_key(created_at)
        if key in application_trend:
            application_trend[key] += 1
            if kind == OpportunityType.INTERNSHIP:
                internship_trend[key] += 1
    placement_trend = {m: 0 for m in months}
    for decided_at in placement_dates:
        key = _month_key(decided_at)
        if key in placement_trend:
            placement_trend[key] += 1

    # ------------------------------------------------------ partnerships ---
    partnerships = await _scalar(
        db,
        select(func.count())
        .select_from(IndustryPartnership)
        .where(IndustryPartnership.institution_id == institution_id),
    )
    hiring_companies = (
        await db.execute(
            select(Company.name, func.count(Application.id))
            .join(Opportunity, Opportunity.company_id == Company.id)
            .join(Application, Application.opportunity_id == Opportunity.id)
            .where(Application.student_id.in_(student_ids_stmt))
            .group_by(Company.name)
            .order_by(func.count(Application.id).desc())
            .limit(10)
        )
    ).all()

    certifications = await _scalar(
        db,
        select(func.count())
        .select_from(StudentCertification)
        .where(StudentCertification.student_id.in_(student_ids_stmt)),
    )
    assessments_taken = await _scalar(
        db,
        select(func.count())
        .select_from(AssessmentAttempt)
        .where(
            AssessmentAttempt.student_id.in_(student_ids_stmt),
            AssessmentAttempt.status == AttemptStatus.EVALUATED,
        ),
    )
    enrolments = await _scalar(
        db,
        select(func.count())
        .select_from(Enrollment)
        .where(Enrollment.student_id.in_(student_ids_stmt)),
    )

    return {
        "summary": {
            "total_students": total_students,
            "placed_students": placed,
            "placement_rate": round(placed / total_students * 100, 1)
            if total_students
            else 0.0,
            "average_readiness": round(float(avg_readiness), 1),
            "average_profile_completion": round(float(avg_completion), 1),
            "total_applications": total_applications,
            "internship_participants": internship_participants,
            "internship_participation_rate": round(
                internship_participants / total_students * 100, 1
            )
            if total_students
            else 0.0,
            "internships_secured": internships_secured,
            "industry_partnerships": partnerships,
            "certifications_earned": certifications,
            "assessments_completed": assessments_taken,
            "learning_enrolments": enrolments,
        },
        "applications_by_status": by_status,
        "readiness_distribution": readiness_bands,
        "top_skills": [
            {"skill": name, "students": count} for _, (name, count) in list(supply.items())[:15]
        ],
        "skill_gaps": [{"skill": name, "students_affected": count} for name, count in gap_rows],
        "demand_vs_supply": demand_vs_supply[:15],
        "departments": [
            {
                "department": name,
                "students": count,
                "average_readiness": round(float(readiness or 0), 1),
                "placed": int(placed_count or 0),
                "placement_rate": round((placed_count or 0) / count * 100, 1)
                if count
                else 0.0,
            }
            for name, count, readiness, placed_count in department_rows
        ],
        "trends": {
            "months": months,
            "applications": [application_trend[m] for m in months],
            "internships": [internship_trend[m] for m in months],
            "placements": [placement_trend[m] for m in months],
        },
        "top_hiring_companies": [
            {"company": name, "applications": count} for name, count in hiring_companies
        ],
        "generated_at": _now(),
    }


# ================================================================== industry
async def industry_analytics(db: AsyncSession, company_id: uuid.UUID) -> dict[str, Any]:
    opportunity_ids = select(Opportunity.id).where(
        Opportunity.company_id == company_id, Opportunity.deleted_at.is_(None)
    )

    total_postings = await _scalar(
        db, select(func.count()).select_from(opportunity_ids.subquery())
    )
    active_postings = await _scalar(
        db,
        select(func.count())
        .select_from(Opportunity)
        .where(
            Opportunity.company_id == company_id,
            Opportunity.status == OpportunityStatus.PUBLISHED,
            Opportunity.deleted_at.is_(None),
        ),
    )

    status_rows = (
        await db.execute(
            select(Application.status, func.count())
            .where(Application.opportunity_id.in_(opportunity_ids))
            .group_by(Application.status)
        )
    ).all()
    by_status = {s.value: c for s, c in status_rows}
    total_applicants = sum(by_status.values())

    qualified = await _scalar(
        db,
        select(func.count())
        .select_from(Application)
        .where(
            Application.opportunity_id.in_(opportunity_ids),
            Application.match_score >= 70,
        ),
    )
    avg_match = (
        await db.execute(
            select(func.avg(Application.match_score)).where(
                Application.opportunity_id.in_(opportunity_ids)
            )
        )
    ).scalar() or 0.0

    # Time to hire, measured from application to decision.
    hires = (
        await db.execute(
            select(Application.submitted_at, Application.decided_at).where(
                Application.opportunity_id.in_(opportunity_ids),
                Application.status == ApplicationStatus.SELECTED,
                Application.decided_at.isnot(None),
            )
        )
    ).all()
    durations = []
    for submitted, decided in hires:
        if submitted and decided:
            submitted = submitted if submitted.tzinfo else submitted.replace(tzinfo=UTC)
            decided = decided if decided.tzinfo else decided.replace(tzinfo=UTC)
            durations.append((decided - submitted).days)
    avg_time_to_hire = round(sum(durations) / len(durations), 1) if durations else None

    applicant_skill_rows = (
        await db.execute(
            select(Skill.name, func.count(StudentSkill.id))
            .join(StudentSkill, StudentSkill.skill_id == Skill.id)
            .join(Application, Application.student_id == StudentSkill.student_id)
            .where(Application.opportunity_id.in_(opportunity_ids))
            .group_by(Skill.name)
            .order_by(func.count(StudentSkill.id).desc())
            .limit(15)
        )
    ).all()

    role_demand_rows = (
        await db.execute(
            select(Opportunity.title, Opportunity.applications_count)
            .where(
                Opportunity.company_id == company_id, Opportunity.deleted_at.is_(None)
            )
            .order_by(Opportunity.applications_count.desc())
            .limit(10)
        )
    ).all()

    missing_rows = (
        await db.execute(
            select(Application.missing_skills).where(
                Application.opportunity_id.in_(opportunity_ids)
            )
        )
    ).scalars().all()
    missing_counts: dict[str, int] = {}
    for entry in missing_rows:
        for name in entry or []:
            missing_counts[str(name)] = missing_counts.get(str(name), 0) + 1
    skill_shortfall = sorted(
        ({"skill": k, "applicants_missing": v} for k, v in missing_counts.items()),
        key=lambda r: -r["applicants_missing"],
    )[:12]

    months = _last_months(12)
    application_dates = (
        await db.execute(
            select(Application.created_at).where(
                Application.opportunity_id.in_(opportunity_ids)
            )
        )
    ).scalars().all()
    trend = {m: 0 for m in months}
    for created_at in application_dates:
        key = _month_key(created_at)
        if key in trend:
            trend[key] += 1

    def stage(*names: str) -> int:
        return sum(by_status.get(n, 0) for n in names)

    funnel = [
        {"stage": "Applied", "count": total_applicants},
        {
            "stage": "Under review",
            "count": stage(
                "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW", "OFFERED", "SELECTED"
            ),
        },
        {"stage": "Shortlisted", "count": stage("SHORTLISTED", "INTERVIEW", "OFFERED", "SELECTED")},
        {"stage": "Interview", "count": stage("INTERVIEW", "OFFERED", "SELECTED")},
        {"stage": "Offer", "count": stage("OFFERED", "SELECTED")},
        {"stage": "Hired", "count": stage("SELECTED")},
    ]

    return {
        "summary": {
            "total_postings": total_postings,
            "active_postings": active_postings,
            "total_applicants": total_applicants,
            "qualified_applicants": qualified,
            "qualified_rate": round(qualified / total_applicants * 100, 1)
            if total_applicants
            else 0.0,
            "average_match_score": round(float(avg_match), 1),
            "hires": by_status.get("SELECTED", 0),
            "average_time_to_hire_days": avg_time_to_hire,
        },
        "applications_by_status": by_status,
        "hiring_funnel": funnel,
        "applicant_skills": [
            {"skill": name, "applicants": count} for name, count in applicant_skill_rows
        ],
        "skill_shortfall": skill_shortfall,
        "role_demand": [
            {"role": title, "applications": count} for title, count in role_demand_rows
        ],
        "trends": {"months": months, "applications": [trend[m] for m in months]},
        "generated_at": _now(),
    }


# ================================================================== platform
async def platform_analytics(db: AsyncSession) -> dict[str, Any]:
    users_by_role = (
        await db.execute(
            select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        )
    ).scalar_one()

    from app.models.user import Role, user_roles

    role_rows = (
        await db.execute(
            select(Role.name, func.count(user_roles.c.user_id))
            .join(user_roles, user_roles.c.role_id == Role.id)
            .group_by(Role.name)
        )
    ).all()

    months = _last_months(12)
    signups = (
        await db.execute(select(User.created_at).where(User.deleted_at.is_(None)))
    ).scalars().all()
    signup_trend = {m: 0 for m in months}
    for created_at in signups:
        key = _month_key(created_at)
        if key in signup_trend:
            signup_trend[key] += 1

    return {
        "summary": {
            "total_users": users_by_role,
            "students": await _scalar(
                db,
                select(func.count())
                .select_from(StudentProfile)
                .where(StudentProfile.deleted_at.is_(None)),
            ),
            "institutions": await _scalar(
                db,
                select(func.count())
                .select_from(Institution)
                .where(Institution.deleted_at.is_(None)),
            ),
            "companies": await _scalar(
                db,
                select(func.count())
                .select_from(Company)
                .where(Company.deleted_at.is_(None)),
            ),
            "opportunities": await _scalar(
                db,
                select(func.count())
                .select_from(Opportunity)
                .where(Opportunity.deleted_at.is_(None)),
            ),
            "published_opportunities": await _scalar(
                db,
                select(func.count())
                .select_from(Opportunity)
                .where(
                    Opportunity.status == OpportunityStatus.PUBLISHED,
                    Opportunity.deleted_at.is_(None),
                ),
            ),
            "applications": await _scalar(
                db, select(func.count()).select_from(Application)
            ),
            "placements": await _scalar(
                db,
                select(func.count())
                .select_from(Application)
                .where(Application.status == ApplicationStatus.SELECTED),
            ),
            "assessments_completed": await _scalar(
                db,
                select(func.count())
                .select_from(AssessmentAttempt)
                .where(AssessmentAttempt.status == AttemptStatus.EVALUATED),
            ),
            "events": await _scalar(
                db, select(func.count()).select_from(Event).where(Event.deleted_at.is_(None))
            ),
            "skills_tracked": await _scalar(
                db, select(func.count()).select_from(Skill).where(Skill.is_active.is_(True))
            ),
        },
        "users_by_role": {name.value: count for name, count in role_rows},
        "signup_trend": {"months": months, "signups": [signup_trend[m] for m in months]},
        "generated_at": _now(),
    }


# =================================================================== exports
def to_csv(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    """Render rows as CSV. Values are quoted, so commas and quotes are safe."""
    import csv
    import io

    if not rows:
        return ""
    columns = columns or list(rows[0].keys())
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=columns, extrasaction="ignore", quoting=csv.QUOTE_MINIMAL
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    return buffer.getvalue()


def to_pdf(title: str, sections: list[tuple[str, list[dict[str, Any]]]]) -> bytes:
    """Render a simple tabular report to PDF."""
    import io

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    base = getSampleStyleSheet()
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
        title=title,
    )
    heading = ParagraphStyle(
        "H", parent=base["Heading1"], fontSize=16,
        textColor=colors.HexColor("#0f172a"), spaceAfter=2,
    )
    sub = ParagraphStyle(
        "S", parent=base["Normal"], fontSize=8.5,
        textColor=colors.HexColor("#64748b"), spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "Sec", parent=base["Heading2"], fontSize=11,
        textColor=colors.HexColor("#1c5d99"), spaceBefore=10, spaceAfter=4,
    )

    flow: list[Any] = [
        Paragraph(title, heading),
        Paragraph(
            f"SkillBridge report · generated {_now():%d %b %Y %H:%M} UTC", sub
        ),
    ]
    for section_title, rows in sections:
        flow.append(Paragraph(section_title, section_style))
        if not rows:
            flow.append(Paragraph("No data for this section.", base["Normal"]))
            flow.append(Spacer(1, 6))
            continue
        columns = list(rows[0].keys())
        data = [[c.replace("_", " ").title() for c in columns]]
        for row in rows[:60]:
            data.append([str(row.get(c, ""))[:60] for c in columns])
        table = Table(data, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8dee9")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#fafbfc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        flow.append(table)
        flow.append(Spacer(1, 8))

    document.build(flow)
    return buffer.getvalue()
