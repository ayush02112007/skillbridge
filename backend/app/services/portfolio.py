"""Digital portfolio assembly and resume PDF generation."""
from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.enums import RoleName, Visibility
from app.models.learning import StudentCertification
from app.models.organization import Institution
from app.models.portfolio import Portfolio, StudentBadge
from app.models.profile import (
    Achievement,
    EducationRecord,
    ExperienceRecord,
    StudentProfile,
    StudentProject,
)
from app.models.skill import Skill, StudentSkill
from app.models.user import User

log = get_logger("portfolio")

DEFAULT_SECTIONS = [
    "about", "skills", "experience", "projects", "education",
    "certifications", "achievements",
]


def _now() -> datetime:
    return datetime.now(UTC)


async def get_or_create(db: AsyncSession, student: StudentProfile) -> Portfolio:
    portfolio = (
        await db.execute(select(Portfolio).where(Portfolio.student_id == student.id))
    ).scalar_one_or_none()
    if portfolio is None:
        portfolio = Portfolio(
            student_id=student.id,
            slug=student.portfolio_slug or f"student-{str(student.id)[:8]}",
            headline=student.headline or "",
            about=student.bio or "",
            visibility=student.portfolio_visibility,
            sections=DEFAULT_SECTIONS,
        )
        db.add(portfolio)
        await db.flush()
    return portfolio


async def can_view(
    db: AsyncSession, portfolio: Portfolio, student: StudentProfile, viewer: User | None
) -> bool:
    """Visibility rules: PUBLIC, INSTITUTION_ONLY or PRIVATE."""
    if portfolio.visibility == Visibility.PUBLIC:
        return True
    if viewer is None:
        return False
    if viewer.id == student.user_id:
        return True
    if RoleName.SUPER_ADMIN.value in viewer.role_names:
        return True
    if portfolio.visibility == Visibility.INSTITUTION_ONLY:
        # Institution staff, and recruiters the student has applied to.
        if viewer.institution_id and viewer.institution_id == student.institution_id:
            return True
        if viewer.company_id:
            from app.models.application import Application
            from app.models.opportunity import Opportunity

            applied = (
                await db.execute(
                    select(func.count())
                    .select_from(Application)
                    .join(Opportunity, Opportunity.id == Application.opportunity_id)
                    .where(
                        Application.student_id == student.id,
                        Opportunity.company_id == viewer.company_id,
                    )
                )
            ).scalar_one()
            return bool(applied)
    return False


async def build_public_view(
    db: AsyncSession, student: StudentProfile, portfolio: Portfolio
) -> dict[str, Any]:
    """Assemble the portfolio. Contact details appear only if opted in."""
    user = student.user or await db.get(User, student.user_id)
    institution = (
        await db.get(Institution, student.institution_id)
        if student.institution_id
        else None
    )

    skills = (
        await db.execute(
            select(StudentSkill)
            .where(StudentSkill.student_id == student.id)
            .options(selectinload(StudentSkill.skill).selectinload(Skill.category))
            .order_by(StudentSkill.score.desc())
        )
    ).scalars().all()
    education = (
        await db.execute(
            select(EducationRecord)
            .where(EducationRecord.student_id == student.id)
            .order_by(EducationRecord.end_year.desc().nullslast())
        )
    ).scalars().all()
    experience = (
        await db.execute(
            select(ExperienceRecord)
            .where(ExperienceRecord.student_id == student.id)
            .order_by(ExperienceRecord.start_date.desc().nullslast())
        )
    ).scalars().all()
    projects = (
        await db.execute(
            select(StudentProject)
            .where(StudentProject.student_id == student.id)
            .order_by(StudentProject.is_featured.desc(), StudentProject.created_at.desc())
        )
    ).scalars().all()
    certifications = (
        await db.execute(
            select(StudentCertification).where(
                StudentCertification.student_id == student.id
            )
        )
    ).scalars().all()
    achievements = (
        await db.execute(
            select(Achievement)
            .where(Achievement.student_id == student.id)
            .order_by(Achievement.achieved_on.desc().nullslast())
        )
    ).scalars().all()
    badges = (
        await db.execute(
            select(StudentBadge)
            .where(StudentBadge.student_id == student.id)
            .options(selectinload(StudentBadge.badge))
        )
    ).scalars().all()

    verified = sum(
        [
            sum(1 for e in experience if e.is_verified),
            sum(1 for c in certifications if c.verification_status == "VERIFIED"),
            sum(1 for e in education if e.is_verified),
            sum(1 for s in skills if s.is_verified),
        ]
    )

    return {
        "slug": portfolio.slug,
        "full_name": user.full_name if user else "",
        "headline": portfolio.headline or student.headline or "",
        "about": portfolio.about or student.bio or "",
        "theme": portfolio.theme,
        "avatar_url": user.avatar_url if user else None,
        "city": student.city,
        "institution_name": institution.name if institution else None,
        "program_name": student.program_name,
        "graduation_year": student.graduation_year,
        "email": (user.email if user and portfolio.contact_email_visible else None),
        "phone": (user.phone if user and portfolio.phone_visible else None),
        "github_url": student.github_url,
        "linkedin_url": student.linkedin_url,
        "skill_readiness_score": student.skill_readiness_score,
        "verified_credential_count": verified,
        "skills": [
            {
                "name": s.skill.name if s.skill else "",
                "category": s.skill.category.name if s.skill and s.skill.category else "",
                "level": s.level.value,
                "score": s.score,
                "source": s.source.value,
                "is_verified": s.is_verified,
            }
            for s in skills
        ],
        "education": [
            {
                "level": e.level.value, "institution_name": e.institution_name,
                "program": e.program, "specialization": e.specialization,
                "start_year": e.start_year, "end_year": e.end_year,
                "score_value": e.score_value, "score_type": e.score_type,
                "is_verified": e.is_verified,
            }
            for e in education
        ],
        "experience": [
            {
                "kind": e.kind, "title": e.title, "organization": e.organization,
                "location": e.location, "description": e.description,
                "start_date": e.start_date, "end_date": e.end_date,
                "is_current": e.is_current, "skill_tags": list(e.skill_tags or []),
                "is_verified": e.is_verified,
            }
            for e in experience
        ],
        "projects": [
            {
                "title": p.title, "description": p.description, "role": p.role,
                "skill_tags": list(p.skill_tags or []),
                "repository_url": p.repository_url, "demo_url": p.demo_url,
                "highlights": list(p.highlights or []), "is_featured": p.is_featured,
            }
            for p in projects
        ],
        "certifications": [
            {
                "name": c.name, "issuer": c.issuer, "issued_on": c.issued_on,
                "credential_url": c.credential_url,
                "is_verified": c.verification_status == "VERIFIED",
            }
            for c in certifications
        ],
        "achievements": [
            {
                "title": a.title, "category": a.category, "issuer": a.issuer,
                "achieved_on": a.achieved_on, "position": a.position,
                "description": a.description, "is_verified": a.is_verified,
            }
            for a in achievements
        ],
        "badges": [
            {
                "code": b.badge.code.value if b.badge else "",
                "name": b.badge.name if b.badge else "",
                "icon": b.badge.icon if b.badge else "award",
            }
            for b in badges
        ],
    }


# ------------------------------------------------------------ resume PDF ---
TEMPLATE_STYLES: dict[str, dict[str, Any]] = {
    "modern": {"accent": "#1c5d99", "rule": True, "name_size": 22},
    "minimal": {"accent": "#111827", "rule": False, "name_size": 20},
    "professional": {"accent": "#2a4365", "rule": True, "name_size": 21},
    "technical": {"accent": "#0f766e", "rule": True, "name_size": 20},
}


def render_resume_pdf(content: dict[str, Any], template: str = "modern") -> bytes:
    """Render a resume to PDF.

    Only what the student entered is rendered - the generator never invents
    experience, dates or achievements to fill space.
    """
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    style = TEMPLATE_STYLES.get(template, TEMPLATE_STYLES["modern"])
    accent = colors.HexColor(style["accent"])
    base = getSampleStyleSheet()

    name_style = ParagraphStyle(
        "Name", parent=base["Title"], fontSize=style["name_size"], leading=style["name_size"] + 4,
        alignment=TA_LEFT, textColor=colors.HexColor("#111827"), spaceAfter=2,
    )
    contact_style = ParagraphStyle(
        "Contact", parent=base["Normal"], fontSize=9, textColor=colors.HexColor("#4b5563"),
        spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "SectionHeading", parent=base["Heading2"], fontSize=11, leading=13,
        textColor=accent, spaceBefore=10, spaceAfter=3,
    )
    entry_title = ParagraphStyle(
        "EntryTitle", parent=base["Normal"], fontSize=10.5, leading=13,
        textColor=colors.HexColor("#111827"),
    )
    entry_meta = ParagraphStyle(
        "EntryMeta", parent=base["Normal"], fontSize=9, leading=11,
        textColor=colors.HexColor("#6b7280"), spaceAfter=2,
    )
    body_style = ParagraphStyle(
        "Body", parent=base["Normal"], fontSize=9.5, leading=12.5,
        textColor=colors.HexColor("#374151"),
    )

    def escape(value: Any) -> str:
        return (
            str(value or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=escape(content.get("contact", {}).get("full_name", "Resume")),
        author=escape(content.get("contact", {}).get("full_name", "")),
    )

    flow: list[Any] = []
    contact = content.get("contact") or {}
    flow.append(Paragraph(escape(contact.get("full_name", "")), name_style))

    bits = [
        escape(contact.get("email")), escape(contact.get("phone")),
        escape(contact.get("location")),
    ]
    bits += [escape(link.get("url", "")) for link in (contact.get("links") or [])]
    flow.append(Paragraph("  ·  ".join(b for b in bits if b), contact_style))
    if style["rule"]:
        flow.append(HRFlowable(width="100%", thickness=1, color=accent, spaceAfter=6))

    def section(title: str) -> None:
        flow.append(Paragraph(title.upper(), heading_style))

    if content.get("summary"):
        section("Summary")
        flow.append(Paragraph(escape(content["summary"]), body_style))

    if content.get("skills"):
        section("Skills")
        flow.append(
            Paragraph(
                "  ·  ".join(escape(s) for s in content["skills"][:40]), body_style
            )
        )

    for key, heading in (
        ("experience", "Experience"),
        ("projects", "Projects"),
        ("education", "Education"),
        ("certifications", "Certifications"),
    ):
        entries = content.get(key) or []
        if not entries:
            continue
        section(heading)
        for entry in entries:
            title = escape(entry.get("title"))
            subtitle = escape(entry.get("subtitle"))
            flow.append(
                Paragraph(
                    f"<b>{title}</b>" + (f" — {subtitle}" if subtitle else ""),
                    entry_title,
                )
            )
            period = " – ".join(
                p for p in [escape(entry.get("start")), escape(entry.get("end"))] if p
            )
            meta = "  ·  ".join(p for p in [period, escape(entry.get("location"))] if p)
            if meta:
                flow.append(Paragraph(meta, entry_meta))
            bullets = [b for b in (entry.get("bullets") or []) if b]
            if bullets:
                flow.append(
                    ListFlowable(
                        [
                            ListItem(Paragraph(escape(b), body_style), leftIndent=10)
                            for b in bullets[:6]
                        ],
                        bulletType="bullet", start="•", leftIndent=10, spaceAfter=4,
                    )
                )
            flow.append(Spacer(1, 4))

    if content.get("achievements"):
        section("Achievements")
        flow.append(
            ListFlowable(
                [
                    ListItem(Paragraph(escape(a), body_style), leftIndent=10)
                    for a in content["achievements"][:8]
                ],
                bulletType="bullet", start="•", leftIndent=10,
            )
        )

    document.build(flow)
    return buffer.getvalue()


async def resume_content_from_profile(
    db: AsyncSession, student: StudentProfile
) -> dict[str, Any]:
    """Pre-fill the resume builder from the profile the student already has."""
    view = await build_public_view(
        db, student, await get_or_create(db, student)
    )
    return {
        "contact": {
            "full_name": view["full_name"],
            "email": student.user.email if student.user else "",
            "phone": student.user.phone if student.user else "",
            "location": student.city or "",
            "links": [
                {"label": label, "url": url}
                for label, url in (
                    ("GitHub", student.github_url),
                    ("LinkedIn", student.linkedin_url),
                    ("Portfolio", student.portfolio_url),
                )
                if url
            ],
        },
        "summary": view["about"],
        "skills": [s["name"] for s in view["skills"][:20]],
        "experience": [
            {
                "title": e["title"], "subtitle": e["organization"],
                "start": str(e["start_date"] or ""), "end": str(e["end_date"] or "Present"),
                "location": e["location"] or "",
                "bullets": [e["description"]] if e["description"] else [],
            }
            for e in view["experience"]
        ],
        "projects": [
            {
                "title": p["title"], "subtitle": p["role"] or "",
                "start": "", "end": "", "location": "",
                "bullets": ([p["description"]] if p["description"] else [])
                + list(p["highlights"] or []),
            }
            for p in view["projects"]
        ],
        "education": [
            {
                "title": e["program"] or e["level"].title(),
                "subtitle": e["institution_name"],
                "start": str(e["start_year"] or ""), "end": str(e["end_year"] or ""),
                "location": "",
                "bullets": (
                    [f"{e['score_type'].title()}: {e['score_value']}"]
                    if e["score_value"]
                    else []
                ),
            }
            for e in view["education"]
        ],
        "certifications": [
            {
                "title": c["name"], "subtitle": c["issuer"],
                "start": "", "end": str(c["issued_on"] or ""), "location": "",
                "bullets": [],
            }
            for c in view["certifications"]
        ],
        "achievements": [a["title"] for a in view["achievements"]],
    }
