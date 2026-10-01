"""Populate a development database with the reference catalogue and demo data.

    python -m seeds.seed            # create anything missing
    python -m seeds.seed --reset    # drop and rebuild everything
    python -m seeds.seed --catalog-only

Every demo record is flagged ``is_demo=True`` so it can be told apart from real
data and removed wholesale. Demo accounts all share one password, printed at the
end; the seeder refuses to run against a production environment.
"""
from __future__ import annotations

import argparse
import asyncio
import random
import sys
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.models.application import Application, ApplicationStatusHistory, Interview
from app.models.assessment import AssessmentAttempt
from app.models.enums import (
    ApplicationStatus,
    CollaborationStatus,
    Degree,
    Difficulty,
    EmploymentType,
    EnrollmentStatus,
    EventType,
    FacultyOpportunityKind,
    MentorshipStatus,
    OpportunityStatus,
    OpportunityType,
    ProficiencyLevel,
    ProgramType,
    RegistrationStatus,
    ResearchProjectType,
    RoleName,
    SkillImportance,
    SkillSource,
    UserStatus,
    VerificationStatus,
    Visibility,
    WorkMode,
)
from app.models.event import Event, EventRegistration
from app.models.learning import (
    CourseModule,
    Enrollment,
    LearningProgram,
    ProgramSkill,
    StudentCertification,
)
from app.models.mentorship import MentorProfile, MentorshipRequest, MentorshipSession
from app.models.opportunity import (
    FacultyOpportunity,
    Internship,
    Job,
    LiveProject,
    Opportunity,
    OpportunitySkill,
)
from app.models.organization import Company, Department, IndustryPartnership, Institution
from app.models.portfolio import Portfolio
from app.models.profile import (
    AcademicianProfile,
    Achievement,
    EducationRecord,
    ExperienceRecord,
    RecruiterProfile,
    StudentProfile,
    StudentProject,
)
from app.models.research import ResearchApplication, ResearchProject
from app.models.skill import JobRole, RoleSkill, Skill, StudentSkill
from app.models.user import Role, User
from app.services import skill as skill_service
from app.services.auth import slugify
from app.services.bootstrap import sync_rbac_catalogue
from seeds import demo_data as demo
from seeds.assessment_seed import seed_assessments
from seeds.catalog_seed import seed_catalog

configure_logging()
log = get_logger("seed")

RNG = random.Random(20260922)  # deterministic: the same seed every run

DEMO_ACCOUNTS = [
    ("student@demo.com", RoleName.STUDENT, "Aditi Sharma"),
    ("faculty@demo.com", RoleName.ACADEMICIAN, "Dr. Sunita Deshmukh"),
    ("industry@demo.com", RoleName.INDUSTRY_RECRUITER, "Rohan Mehta"),
    ("industry-admin@demo.com", RoleName.INDUSTRY_ADMIN, "Priya Nair"),
    ("institution@demo.com", RoleName.INSTITUTION_ADMIN, "Prof. Anil Kulkarni"),
    ("admin@demo.com", RoleName.SUPER_ADMIN, "Platform Administrator"),
]


def _now() -> datetime:
    return datetime.now(UTC)


async def _unique_slug(db: AsyncSession, model: Any, base: str, column: str = "slug") -> str:
    base = slugify(base)
    candidate, suffix = base, 1
    col = getattr(model, column)
    while (await db.execute(select(model.id).where(col == candidate).limit(1))).first():
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate


# ============================================================ organisations
async def seed_institutions(db: AsyncSession) -> dict[str, Institution]:
    created: dict[str, Institution] = {}
    for spec in demo.INSTITUTIONS:
        existing = (
            await db.execute(select(Institution).where(Institution.name == spec["name"]))
        ).scalar_one_or_none()
        if existing is not None:
            created[spec["name"]] = existing
            continue
        institution = Institution(
            name=spec["name"], slug=await _unique_slug(db, Institution, spec["name"]),
            short_name=spec["short_name"], institution_type=spec["institution_type"],
            accreditation=spec["accreditation"], city=spec["city"], state=spec["state"],
            country="India", established_year=spec["established_year"],
            description=spec["description"],
            contact_email=f"placements@{slugify(spec['short_name'])}.edu",
            verification_status=VerificationStatus.VERIFIED, is_demo=True,
        )
        db.add(institution)
        await db.flush()
        for name, code in spec["departments"]:
            db.add(
                Department(
                    institution_id=institution.id, name=name, code=code,
                    hod_name=f"Dr. {RNG.choice(demo.LAST_NAMES)}",
                )
            )
        created[spec["name"]] = institution
    await db.flush()
    return created


async def seed_companies(db: AsyncSession) -> dict[str, Company]:
    created: dict[str, Company] = {}
    for spec in demo.COMPANIES:
        existing = (
            await db.execute(select(Company).where(Company.name == spec["name"]))
        ).scalar_one_or_none()
        if existing is not None:
            created[spec["name"]] = existing
            continue
        company = Company(
            name=spec["name"], slug=await _unique_slug(db, Company, spec["name"]),
            industry_sector=spec["sector"], headquarters_city=spec["city"],
            headquarters_country="India", employee_count=spec["employees"],
            founded_year=spec["founded"], description=spec["description"],
            about=spec["about"], tech_stack=spec["tech"], benefits=spec["benefits"],
            website=f"https://{slugify(spec['name'])}.example.com",
            contact_email=f"careers@{slugify(spec['name'])}.example.com",
            locations=[spec["city"]],
            verification_status=VerificationStatus.VERIFIED, is_hiring=True, is_demo=True,
        )
        db.add(company)
        created[spec["name"]] = company
    await db.flush()
    return created


# ==================================================================== users
async def _role_map(db: AsyncSession) -> dict[RoleName, Role]:
    from sqlalchemy.orm import selectinload

    rows = (
        await db.execute(select(Role).options(selectinload(Role.permissions)))
    ).scalars().all()
    return {r.name: r for r in rows}


async def _create_user(
    db: AsyncSession, *, email: str, full_name: str, role: Role,
    institution_id=None, company_id=None, password: str,
) -> User:
    user = User(
        email=email.lower(), hashed_password=hash_password(password),
        full_name=full_name, status=UserStatus.ACTIVE, is_email_verified=True,
        email_verified_at=_now(), password_changed_at=_now(),
        institution_id=institution_id, company_id=company_id,
        phone=f"+91 9{RNG.randint(100000000, 999999999)}",
    )
    user.roles = [role]
    db.add(user)
    await db.flush()
    return user


async def seed_students(
    db: AsyncSession, institutions: dict[str, Institution], roles: dict[RoleName, Role],
    skills: dict[str, Skill], job_roles: dict[str, JobRole], count: int = 50,
) -> list[StudentProfile]:
    """Create students across archetypes, with skills, projects and history."""
    existing = (
        await db.execute(
            select(func.count()).select_from(StudentProfile).where(
                StudentProfile.is_demo.is_(True)
            )
        )
    ).scalar_one()
    if existing >= count:
        return (
            await db.execute(
                select(StudentProfile).where(StudentProfile.is_demo.is_(True))
            )
        ).scalars().all()

    institution_list = list(institutions.values())
    profiles: list[StudentProfile] = []
    password = settings.SEED_DEMO_PASSWORD

    for index in range(count):
        archetype = demo.STUDENT_ARCHETYPES[index % len(demo.STUDENT_ARCHETYPES)]
        first = demo.FIRST_NAMES[index % len(demo.FIRST_NAMES)]
        last = demo.LAST_NAMES[(index * 7) % len(demo.LAST_NAMES)]
        full_name = f"{first} {last}"
        email = f"{slugify(first)}.{slugify(last)}{index}@student.demo"

        if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
            continue

        institution = institution_list[index % len(institution_list)]
        await db.refresh(institution, ["departments"])
        department = (
            RNG.choice(institution.departments) if institution.departments else None
        )

        user = await _create_user(
            db, email=email, full_name=full_name, role=roles[RoleName.STUDENT],
            institution_id=institution.id, password=password,
        )
        graduation_year = RNG.choice([2026, 2027, 2027, 2028])
        current_year = max(1, min(4, 4 - (graduation_year - 2026)))
        target = job_roles.get(archetype["target"])

        profile = StudentProfile(
            user_id=user.id,
            institution_id=institution.id,
            department_id=department.id if department else None,
            headline=f"{archetype['roles'][0]} in training",
            bio=(
                f"{current_year}th-year student at {institution.short_name} focusing on "
                f"{archetype['interests'][0].lower()}. Building projects and looking for "
                "an internship where I can ship real work."
            ),
            city=institution.city,
            state=None,
            enrollment_number=f"{institution.short_name}{graduation_year}{1000 + index}",
            degree=Degree.BACHELORS,
            program_name=f"B.Tech {department.name}" if department else "B.Tech",
            current_year=current_year,
            current_semester=current_year * 2,
            cgpa=round(RNG.uniform(6.4, 9.6), 2),
            graduation_year=graduation_year,
            backlogs=RNG.choice([0, 0, 0, 0, 1, 2]),
            career_interests=archetype["interests"],
            preferred_roles=archetype["roles"],
            preferred_industries=[RNG.choice([c["sector"] for c in demo.COMPANIES])],
            preferred_locations=[institution.city, "Bengaluru"],
            preferred_work_mode=RNG.choice(list(WorkMode)),
            open_to_relocate=RNG.random() > 0.25,
            expected_stipend_min=RNG.choice([15000, 20000, 25000, 30000]),
            target_job_role_id=target.id if target else None,
            portfolio_slug=await _unique_slug(
                db, StudentProfile, f"{first}-{last}", "portfolio_slug"
            ),
            portfolio_visibility=RNG.choice(
                [Visibility.PUBLIC, Visibility.INSTITUTION_ONLY, Visibility.PUBLIC]
            ),
            github_url=f"https://github.com/{slugify(first)}{slugify(last)}",
            linkedin_url=f"https://linkedin.com/in/{slugify(first)}-{slugify(last)}",
            is_demo=True,
        )
        db.add(profile)
        await db.flush()

        # ------------------------------------------------------- skills --
        for slug, level in archetype["skills"].items():
            skill = skills.get(slug)
            if skill is None:
                continue
            # Vary levels so cohorts are not identical.
            if RNG.random() < 0.3:
                order = ["BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"]
                position = order.index(level) if level in order else 1
                level = order[max(0, min(len(order) - 1, position + RNG.choice([-1, 1])))]
            source = (
                SkillSource.ASSESSMENT if RNG.random() < 0.35 else SkillSource.SELF_REPORTED
            )
            proficiency = ProficiencyLevel(level)
            # Jitter the score for variety, clamped to the 0-100 range the
            # student_skills CHECK constraint enforces.
            score = max(0.0, min(100.0, proficiency.score * 25 + RNG.uniform(-6, 6)))
            db.add(
                StudentSkill(
                    student_id=profile.id, skill_id=skill.id, level=proficiency,
                    score=score,
                    confidence=0.9 if source == SkillSource.ASSESSMENT else 0.35,
                    source=source,
                    last_assessed_at=_now() if source == SkillSource.ASSESSMENT else None,
                    evidence=(
                        {"note": "Seeded demo assessment result"}
                        if source == SkillSource.ASSESSMENT
                        else {}
                    ),
                )
            )

        # ---------------------------------------------------- education --
        db.add(
            EducationRecord(
                student_id=profile.id, level=Degree.BACHELORS,
                institution_name=institution.name,
                board_or_university=institution.name,
                program=profile.program_name, start_year=graduation_year - 4,
                end_year=graduation_year, score_value=profile.cgpa, score_type="CGPA",
                is_verified=True,
            )
        )
        db.add(
            EducationRecord(
                student_id=profile.id, level=Degree.HIGHER_SECONDARY,
                institution_name=f"{institution.city} Junior College",
                board_or_university="State Board", start_year=graduation_year - 6,
                end_year=graduation_year - 4,
                score_value=round(RNG.uniform(72, 96), 1), score_type="PERCENTAGE",
                is_verified=True,
            )
        )

        # ----------------------------------------------------- projects --
        for title, description, tags in RNG.sample(demo.PROJECT_IDEAS, k=RNG.randint(1, 3)):
            db.add(
                StudentProject(
                    student_id=profile.id, title=title, description=description,
                    role=RNG.choice(["Solo", "Team lead", "Backend", "Frontend"]),
                    team_size=RNG.randint(1, 4), skill_tags=tags,
                    repository_url=f"https://github.com/{slugify(first)}/{slugify(title)}",
                    start_date=date(graduation_year - 2, RNG.randint(1, 9), 1),
                    highlights=[f"Built with {tags[0]}"],
                    is_featured=RNG.random() < 0.4,
                )
            )

        # -------------------------------------------------- achievements --
        for title, category, position in RNG.sample(
            demo.ACHIEVEMENTS, k=RNG.randint(0, 2)
        ):
            db.add(
                Achievement(
                    student_id=profile.id, category=category, title=title,
                    position=position, issuer=institution.name,
                    achieved_on=date(graduation_year - 1, RNG.randint(1, 12), 15),
                )
            )

        # ------------------------------------------------- prior intern --
        if RNG.random() < 0.35:
            company_name = RNG.choice(demo.COMPANIES)["name"]
            start = date(graduation_year - 1, 6, 1)
            db.add(
                ExperienceRecord(
                    student_id=profile.id, kind="INTERNSHIP",
                    title=f"{archetype['roles'][0]} Intern", organization=company_name,
                    location=institution.city, work_mode=WorkMode.ONSITE,
                    description="Summer internship building internal tooling.",
                    start_date=start, end_date=start + timedelta(days=60),
                    skill_tags=list(archetype["skills"])[:3],
                )
            )

        db.add(
            Portfolio(
                student_id=profile.id, slug=profile.portfolio_slug,
                headline=profile.headline, about=profile.bio,
                visibility=profile.portfolio_visibility,
                sections=["about", "skills", "experience", "projects", "education",
                          "certifications", "achievements"],
                published_at=_now(),
            )
        )
        profiles.append(profile)

    await db.flush()
    log.info("seed.students_created", count=len(profiles))
    return profiles


async def seed_academicians(
    db: AsyncSession, institutions: dict[str, Institution], roles: dict[RoleName, Role],
) -> list[AcademicianProfile]:
    institution_list = list(institutions.values())
    created: list[AcademicianProfile] = []
    for index, (first, last, designation, specialisation) in enumerate(demo.FACULTY_NAMES):
        email = f"{slugify(first)}.{slugify(last)}@faculty.demo"
        if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
            continue
        institution = institution_list[index % len(institution_list)]
        user = await _create_user(
            db, email=email, full_name=f"{first} {last}",
            role=roles[RoleName.ACADEMICIAN], institution_id=institution.id,
            password=settings.SEED_DEMO_PASSWORD,
        )
        profile = AcademicianProfile(
            user_id=user.id, institution_id=institution.id, designation=designation,
            employee_code=f"FAC{2000 + index}",
            highest_qualification="Ph.D.", specialization=specialisation,
            teaching_experience_years=RNG.randint(4, 24),
            industry_experience_years=RNG.randint(0, 8),
            research_areas=[specialisation, RNG.choice(["Distributed Systems", "HCI",
                                                        "Optimisation", "Privacy"])],
            expertise_areas=[specialisation],
            publications_count=RNG.randint(3, 60),
            patents_count=RNG.randint(0, 4),
            bio=f"{designation} of {specialisation} at {institution.name}, with research "
                "interests spanning applied systems and industry collaboration.",
            city=institution.city,
            is_available_for_mentorship=RNG.random() < 0.7,
            is_available_for_consultancy=RNG.random() < 0.5,
            profile_completion=RNG.randint(70, 100),
            is_demo=True,
        )
        db.add(profile)
        created.append(profile)
    await db.flush()
    log.info("seed.academicians_created", count=len(created))
    return created


async def seed_company_users(
    db: AsyncSession, companies: dict[str, Company], roles: dict[RoleName, Role]
) -> dict[str, User]:
    """One recruiter per company, so every posting has a real owner."""
    recruiters: dict[str, User] = {}
    for index, (name, company) in enumerate(companies.items()):
        email = f"careers@{slugify(name)}.demo"
        existing = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            recruiters[name] = existing
            continue
        first = demo.FIRST_NAMES[(index * 3) % len(demo.FIRST_NAMES)]
        last = demo.LAST_NAMES[(index * 5) % len(demo.LAST_NAMES)]
        user = await _create_user(
            db, email=email, full_name=f"{first} {last}",
            role=roles[RoleName.INDUSTRY_ADMIN], company_id=company.id,
            password=settings.SEED_DEMO_PASSWORD,
        )
        db.add(
            RecruiterProfile(
                user_id=user.id, company_id=company.id,
                designation="Talent Acquisition Lead", is_primary_contact=True,
                hiring_domains=[company.industry_sector], is_demo=True,
            )
        )
        recruiters[name] = user
    await db.flush()
    return recruiters


async def seed_institution_admins(
    db: AsyncSession, institutions: dict[str, Institution], roles: dict[RoleName, Role]
) -> None:
    for name, institution in institutions.items():
        email = f"placements@{slugify(institution.short_name or name)}.demo"
        if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
            continue
        await _create_user(
            db, email=email, full_name=f"Placement Office, {institution.short_name}",
            role=roles[RoleName.INSTITUTION_ADMIN], institution_id=institution.id,
            password=settings.SEED_DEMO_PASSWORD,
        )
    await db.flush()


# ========================================================== opportunities
async def _attach_role_skills(
    db: AsyncSession, opportunity: Opportunity, job_role: JobRole | None,
    skills: dict[str, Skill], extra_slugs: list[str] | None = None,
) -> list[str]:
    names: list[str] = []
    if job_role is not None:
        role_skills = (
            await db.execute(
                select(RoleSkill).where(RoleSkill.job_role_id == job_role.id)
            )
        ).scalars().all()
        for role_skill in role_skills:
            db.add(
                OpportunitySkill(
                    opportunity_id=opportunity.id, skill_id=role_skill.skill_id,
                    required_level=role_skill.required_level,
                    importance=role_skill.importance, weight=role_skill.weight,
                )
            )
    for slug in extra_slugs or []:
        skill = skills.get(slug)
        if skill is not None:
            db.add(
                OpportunitySkill(
                    opportunity_id=opportunity.id, skill_id=skill.id,
                    required_level=ProficiencyLevel.INTERMEDIATE,
                    importance=SkillImportance.PREFERRED, weight=0.8,
                )
            )
    await db.flush()
    rows = (
        await db.execute(
            select(Skill.name)
            .join(OpportunitySkill, OpportunitySkill.skill_id == Skill.id)
            .where(OpportunitySkill.opportunity_id == opportunity.id)
        )
    ).scalars().all()
    names = list(rows)
    opportunity.search_text = " ".join(
        [
            opportunity.title, opportunity.description or "",
            opportunity.location_city or "",
            opportunity.company.name if opportunity.company else "",
            *names,
        ]
    ).lower()[:12000]
    return names


async def seed_opportunities(
    db: AsyncSession, companies: dict[str, Company], recruiters: dict[str, User],
    job_roles: dict[str, JobRole], skills: dict[str, Skill],
) -> dict[str, list[Opportunity]]:
    created: dict[str, list[Opportunity]] = {"internships": [], "jobs": [], "projects": []}

    for title, role_slug, company_name, city, mode, stipend, weeks, description in demo.INTERNSHIPS:
        company = companies[company_name]
        if (
            await db.execute(
                select(Opportunity).where(
                    Opportunity.title == title, Opportunity.company_id == company.id
                )
            )
        ).scalar_one_or_none():
            continue
        job_role = job_roles.get(role_slug)
        internship = Internship(
            title=title, slug=await _unique_slug(db, Opportunity, f"{title}-{company.slug}"),
            description=description,
            responsibilities=[
                "Work in a delivery team with regular code review",
                "Own a scoped piece of the product end to end",
                "Write tests and documentation for what you build",
            ],
            eligibility_text="Open to pre-final and final year students.",
            company_id=company.id, posted_by_id=recruiters[company_name].id,
            job_role_id=job_role.id if job_role else None,
            status=OpportunityStatus.PUBLISHED, published_at=_now() - timedelta(days=RNG.randint(1, 40)),
            work_mode=WorkMode(mode), location_city=city,
            positions=RNG.randint(1, 5),
            min_cgpa=RNG.choice([None, 6.0, 6.5, 7.0]),
            max_backlogs=RNG.choice([None, 0, 1]),
            eligible_degrees=["BACHELORS"],
            eligible_graduation_years=[2026, 2027, 2028],
            application_deadline=_now() + timedelta(days=RNG.randint(7, 60)),
            starts_on=date.today() + timedelta(days=RNG.randint(30, 120)),
            perks=["Certificate", "Mentorship", "Flexible hours"],
            duration_weeks=weeks, stipend_min=stipend[0], stipend_max=stipend[1],
            is_paid=True,
            learning_outcomes=[
                "Ship production code with review",
                "Work with real data and real constraints",
            ],
            mentor_name=recruiters[company_name].full_name,
            is_ppo_available=RNG.random() < 0.5,
            is_demo=True,
        )
        db.add(internship)
        await db.flush()
        await db.refresh(internship, ["company"])
        await _attach_role_skills(db, internship, job_role, skills)
        created["internships"].append(internship)

    for title, role_slug, company_name, city, mode, salary, experience, description in demo.JOBS:
        company = companies[company_name]
        if (
            await db.execute(
                select(Opportunity).where(
                    Opportunity.title == title, Opportunity.company_id == company.id
                )
            )
        ).scalar_one_or_none():
            continue
        job_role = job_roles.get(role_slug)
        job = Job(
            title=title, slug=await _unique_slug(db, Opportunity, f"{title}-{company.slug}"),
            description=description,
            responsibilities=[
                "Design, build and operate services in your team's domain",
                "Participate in on-call and incident review",
                "Mentor interns and new joiners",
            ],
            eligibility_text="Open to final-year students and graduates.",
            company_id=company.id, posted_by_id=recruiters[company_name].id,
            job_role_id=job_role.id if job_role else None,
            status=OpportunityStatus.PUBLISHED,
            published_at=_now() - timedelta(days=RNG.randint(1, 50)),
            work_mode=WorkMode(mode), location_city=city,
            positions=RNG.randint(1, 8),
            min_cgpa=RNG.choice([None, 6.0, 6.5, 7.0]),
            max_backlogs=RNG.choice([None, 0, 1]),
            eligible_degrees=["BACHELORS", "MASTERS"],
            eligible_graduation_years=[2025, 2026, 2027],
            application_deadline=_now() + timedelta(days=RNG.randint(10, 75)),
            perks=["Health cover", "Learning budget", "Hybrid working"],
            employment_type=EmploymentType.FULL_TIME,
            salary_min=salary[0], salary_max=salary[1], salary_period="YEAR",
            experience_min_years=experience,
            experience_max_years=experience + 3,
            hiring_process=["Screening", "Technical round", "System design", "Culture fit"],
            is_demo=True,
        )
        db.add(job)
        await db.flush()
        await db.refresh(job, ["company"])
        await _attach_role_skills(db, job, job_role, skills)
        created["jobs"].append(job)

    for title, company_name, city, weeks, team, problem, outcome in demo.LIVE_PROJECTS:
        company = companies[company_name]
        if (
            await db.execute(
                select(Opportunity).where(
                    Opportunity.title == title, Opportunity.company_id == company.id
                )
            )
        ).scalar_one_or_none():
            continue
        project = LiveProject(
            title=title, slug=await _unique_slug(db, Opportunity, f"{title}-{company.slug}"),
            description=problem,
            responsibilities=["Scope the problem", "Build and demo a solution"],
            company_id=company.id, posted_by_id=recruiters[company_name].id,
            status=OpportunityStatus.PUBLISHED, published_at=_now() - timedelta(days=5),
            work_mode=WorkMode.REMOTE, location_city=city, positions=team[1],
            application_deadline=_now() + timedelta(days=30),
            problem_statement=problem, expected_outcome=outcome,
            team_size_min=team[0], team_size_max=team[1], timeline_weeks=weeks,
            stipend_amount=RNG.choice([None, 10000, 15000]),
            mentor_user_id=recruiters[company_name].id,
            is_demo=True,
        )
        db.add(project)
        await db.flush()
        await db.refresh(project, ["company"])
        await _attach_role_skills(db, project, None, skills, ["problem-solving", "teamwork", "git"])
        created["projects"].append(project)

    for title, kind, company_name, days, focus, description in demo.FACULTY_PROGRAMMES:
        company = companies[company_name]
        if (
            await db.execute(
                select(Opportunity).where(
                    Opportunity.title == title, Opportunity.company_id == company.id
                )
            )
        ).scalar_one_or_none():
            continue
        programme = FacultyOpportunity(
            title=title, slug=await _unique_slug(db, Opportunity, f"{title}-{company.slug}"),
            description=description,
            company_id=company.id, posted_by_id=recruiters[company_name].id,
            status=OpportunityStatus.PUBLISHED, published_at=_now() - timedelta(days=10),
            work_mode=WorkMode.HYBRID, location_city=company.headquarters_city,
            positions=RNG.randint(5, 30),
            application_deadline=_now() + timedelta(days=45),
            kind=FacultyOpportunityKind(kind), duration_days=days,
            honorarium=RNG.choice([None, 25000, 50000]),
            min_teaching_experience_years=RNG.choice([0, 2, 3, 5]),
            focus_areas=focus, seats=RNG.randint(10, 40),
            is_demo=True,
        )
        db.add(programme)
        await db.flush()
        await db.refresh(programme, ["company"])
        await _attach_role_skills(db, programme, None, skills, [])
    await db.flush()
    log.info(
        "seed.opportunities_created",
        internships=len(created["internships"]), jobs=len(created["jobs"]),
        projects=len(created["projects"]),
    )
    return created


# ================================================================ learning
async def seed_programs(
    db: AsyncSession, companies: dict[str, Company], recruiters: dict[str, User],
    skills: dict[str, Skill],
) -> list[LearningProgram]:
    created: list[LearningProgram] = []
    for title, kind, company_name, difficulty, hours, is_free, skill_slugs, description in demo.PROGRAMS:
        if (
            await db.execute(select(LearningProgram).where(LearningProgram.title == title))
        ).scalar_one_or_none():
            continue
        company = companies[company_name]
        program = LearningProgram(
            title=title, slug=await _unique_slug(db, LearningProgram, title),
            summary=description[:400], description=description,
            program_type=ProgramType(kind), provider_company_id=company.id,
            provider_name=company.name, created_by_id=recruiters[company_name].id,
            difficulty=Difficulty(difficulty), duration_hours=hours,
            mode=WorkMode.REMOTE, price_amount=0 if is_free else RNG.choice([2999, 4999, 7999]),
            is_free=is_free, grants_certificate=True,
            outcomes=[f"Apply {s.replace('-', ' ')} in a real project" for s in skill_slugs[:3]],
            prerequisites=["Basic programming" if "python" in skill_slugs else "None"],
            rating=round(RNG.uniform(3.9, 4.9), 1),
            is_published=True, is_demo=True,
        )
        db.add(program)
        await db.flush()

        for slug in skill_slugs:
            skill = skills.get(slug)
            if skill is None:
                continue
            db.add(
                ProgramSkill(
                    program_id=program.id, skill_id=skill.id,
                    target_level="INTERMEDIATE" if difficulty != "HARD" else "ADVANCED",
                    coverage_weight=1.0,
                )
            )
        module_count = max(3, hours // 6)
        for order in range(module_count):
            db.add(
                CourseModule(
                    program_id=program.id,
                    title=f"Module {order + 1}: {skill_slugs[order % len(skill_slugs)].replace('-', ' ').title()}",
                    description="Concepts, worked examples and a short exercise.",
                    content_type=RNG.choice(["VIDEO", "READING", "EXERCISE"]),
                    duration_minutes=RNG.choice([30, 45, 60]),
                    display_order=order,
                )
            )
        program.search_text = " ".join(
            [title, description, *[s.replace("-", " ") for s in skill_slugs]]
        ).lower()
        created.append(program)
    await db.flush()
    log.info("seed.programs_created", count=len(created))
    return created


# =============================================================== mentorship
async def seed_mentors(
    db: AsyncSession, recruiters: dict[str, User], academicians: list[AcademicianProfile],
    companies: dict[str, Company], skills: dict[str, Skill],
) -> list[MentorProfile]:
    created: list[MentorProfile] = []
    topics_pool = [
        "Breaking into backend engineering", "Preparing for technical interviews",
        "Choosing a specialisation", "Building a portfolio that gets replies",
        "Transitioning into data science", "Working in security",
        "Designing for accessibility", "Product thinking for engineers",
    ]

    for name, user in recruiters.items():
        existing = (
            await db.execute(select(MentorProfile).where(MentorProfile.user_id == user.id))
        ).scalar_one_or_none()
        if existing is not None:
            created.append(existing)
            continue
        company = companies[name]
        relevant = [
            skills[s].id for s in RNG.sample(list(skills), k=6) if s in skills
        ]
        mentor = MentorProfile(
            user_id=user.id, company_id=company.id,
            headline=f"Talent lead at {company.name}",
            bio="I hire and coach early-career engineers. Happy to review portfolios "
                "and talk honestly about what gets someone shortlisted.",
            designation="Talent Acquisition Lead",
            experience_years=RNG.randint(5, 18),
            industry=company.industry_sector,
            expertise_skill_ids=[str(i) for i in relevant],
            topics=RNG.sample(topics_pool, k=3),
            languages=["English", "Hindi"],
            availability=[{"day": d, "from": "18:00", "to": "20:00"}
                          for d in RNG.sample(["MON", "TUE", "WED", "THU", "FRI"], k=2)],
            capacity_per_month=RNG.randint(3, 8),
            rating=round(RNG.uniform(4.0, 5.0), 1),
            sessions_completed=RNG.randint(0, 40),
            is_demo=True,
        )
        db.add(mentor)
        created.append(mentor)

    for profile in academicians[:5]:
        existing = (
            await db.execute(
                select(MentorProfile).where(MentorProfile.user_id == profile.user_id)
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        relevant = [skills[s].id for s in RNG.sample(list(skills), k=4) if s in skills]
        mentor = MentorProfile(
            user_id=profile.user_id, institution_id=profile.institution_id,
            headline=f"{profile.designation}, {profile.specialization}",
            bio=profile.bio, designation=profile.designation,
            experience_years=profile.teaching_experience_years,
            industry="Education",
            expertise_skill_ids=[str(i) for i in relevant],
            topics=RNG.sample(topics_pool, k=2),
            languages=["English"],
            availability=[{"day": "SAT", "from": "10:00", "to": "12:00"}],
            capacity_per_month=RNG.randint(2, 6),
            rating=round(RNG.uniform(4.0, 5.0), 1),
            is_demo=True,
        )
        db.add(mentor)
        created.append(mentor)
    await db.flush()
    log.info("seed.mentors_created", count=len(created))
    return created


# =================================================================== events
async def seed_events(
    db: AsyncSession, companies: dict[str, Company], recruiters: dict[str, User]
) -> list[Event]:
    created: list[Event] = []
    for title, kind, company_name, days_ahead, minutes, tags, description in demo.EVENTS:
        if (await db.execute(select(Event).where(Event.title == title))).scalar_one_or_none():
            continue
        company = companies[company_name]
        starts = _now() + timedelta(days=days_ahead, hours=RNG.choice([10, 14, 16]))
        event = Event(
            title=title, slug=await _unique_slug(db, Event, title),
            description=description, event_type=EventType(kind),
            host_company_id=company.id, created_by_id=recruiters[company_name].id,
            speaker_name=recruiters[company_name].full_name,
            speaker_designation="Engineering Lead",
            mode=RNG.choice([WorkMode.REMOTE, WorkMode.HYBRID, WorkMode.ONSITE]),
            venue=company.headquarters_city,
            meeting_link="https://meet.example.com/" + slugify(title)[:20],
            starts_at=starts, ends_at=starts + timedelta(minutes=minutes),
            registration_deadline=starts - timedelta(days=1),
            capacity=RNG.choice([50, 100, 200, None]),
            skill_tags=tags, target_audience=["Students", "Final year"],
            grants_certificate=True, is_published=True, is_demo=True,
            search_text=" ".join([title, description, *tags]).lower(),
        )
        db.add(event)
        created.append(event)
    await db.flush()
    log.info("seed.events_created", count=len(created))
    return created


# ================================================================= research
async def seed_research(
    db: AsyncSession, companies: dict[str, Company], recruiters: dict[str, User],
    institutions: dict[str, Institution], academicians: list[AcademicianProfile],
) -> list[ResearchProject]:
    created: list[ResearchProject] = []
    institution_list = list(institutions.values())
    for index, (title, kind, company_name, areas, funding, months) in enumerate(
        demo.RESEARCH_PROJECTS
    ):
        if (
            await db.execute(select(ResearchProject).where(ResearchProject.title == title))
        ).scalar_one_or_none():
            continue
        company = companies[company_name]
        project = ResearchProject(
            title=title, slug=await _unique_slug(db, ResearchProject, title),
            abstract=f"{title}. A collaboration between {company.name} and academic "
                     "partners, with defined deliverables and funding.",
            project_type=ResearchProjectType(kind),
            status=CollaborationStatus.OPEN,
            company_id=company.id,
            institution_id=institution_list[index % len(institution_list)].id,
            created_by_id=recruiters[company_name].id,
            research_areas=areas, required_expertise=areas,
            deliverables=["Interim report", "Working prototype", "Final publication"],
            funding_amount=funding, duration_months=months,
            starts_on=date.today() + timedelta(days=60),
            application_deadline=_now() + timedelta(days=45),
            positions=RNG.randint(1, 3),
            search_text=" ".join([title, *areas]).lower(),
            is_demo=True,
        )
        db.add(project)
        await db.flush()
        created.append(project)

        # A couple of faculty proposals so the reviewer screen is not empty.
        for profile in RNG.sample(academicians, k=min(2, len(academicians))):
            db.add(
                ResearchApplication(
                    project_id=project.id, academician_id=profile.id,
                    proposal=(
                        f"Our group has worked on {profile.specialization} for "
                        f"{profile.teaching_experience_years} years. We propose to "
                        "contribute experimental design and evaluation."
                    ),
                    relevant_publications=[
                        f"{profile.specialization}: a survey ({RNG.randint(2019, 2026)})"
                    ],
                    status=RNG.choice(["APPLIED", "UNDER_REVIEW", "SHORTLISTED"]),
                    is_demo=True,
                )
            )
    await db.flush()
    return created


# ============================================================= applications
async def seed_applications(
    db: AsyncSession, students: list[StudentProfile],
    opportunities: dict[str, list[Opportunity]], recruiters: dict[str, User],
    count: int = 120,
) -> int:
    """Create applications at realistic pipeline stages, with real match scores."""
    from app.services import opportunity as opportunity_service

    existing = (
        await db.execute(select(func.count()).select_from(Application))
    ).scalar_one()
    if existing >= count:
        return existing

    pool = opportunities["internships"] + opportunities["jobs"]
    if not pool or not students:
        return 0

    # A realistic funnel shape rather than a uniform spread.
    stages = (
        [ApplicationStatus.APPLIED] * 10
        + [ApplicationStatus.UNDER_REVIEW] * 6
        + [ApplicationStatus.SHORTLISTED] * 4
        + [ApplicationStatus.INTERVIEW] * 3
        + [ApplicationStatus.OFFERED] * 1
        + [ApplicationStatus.SELECTED] * 1
        + [ApplicationStatus.REJECTED] * 5
        + [ApplicationStatus.WITHDRAWN] * 1
    )

    created = 0
    attempts = 0
    while created < count and attempts < count * 4:
        attempts += 1
        student = RNG.choice(students)
        opportunity = RNG.choice(pool)
        duplicate = (
            await db.execute(
                select(Application).where(
                    Application.student_id == student.id,
                    Application.opportunity_id == opportunity.id,
                )
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            continue

        await db.refresh(opportunity, ["company", "job_role"])
        result = await opportunity_service.match_student_to_opportunity(
            db, student, opportunity
        )
        if not result.is_eligible:
            continue

        submitted = _now() - timedelta(days=RNG.randint(1, 45))
        target_status = RNG.choice(stages)
        application = Application(
            opportunity_id=opportunity.id, student_id=student.id,
            status=ApplicationStatus.APPLIED,
            cover_letter="I have built projects using the skills in this posting and "
                         "would value the chance to work on real systems.",
            match_score=result.match_score, match_breakdown=result.breakdown,
            matching_skills=result.matching_skills, missing_skills=result.missing_skills,
            submitted_at=submitted, last_status_change_at=submitted, is_demo=True,
        )
        db.add(application)
        await db.flush()
        db.add(
            ApplicationStatusHistory(
                application_id=application.id, to_status=ApplicationStatus.APPLIED,
                changed_by_id=student.user_id, note="Application submitted",
                created_at=submitted,
            )
        )

        # Walk the application forward through legal transitions only.
        path = {
            ApplicationStatus.APPLIED: [],
            ApplicationStatus.UNDER_REVIEW: [ApplicationStatus.UNDER_REVIEW],
            ApplicationStatus.SHORTLISTED: [
                ApplicationStatus.UNDER_REVIEW, ApplicationStatus.SHORTLISTED
            ],
            ApplicationStatus.INTERVIEW: [
                ApplicationStatus.UNDER_REVIEW, ApplicationStatus.SHORTLISTED,
                ApplicationStatus.INTERVIEW,
            ],
            ApplicationStatus.OFFERED: [
                ApplicationStatus.UNDER_REVIEW, ApplicationStatus.SHORTLISTED,
                ApplicationStatus.INTERVIEW, ApplicationStatus.OFFERED,
            ],
            ApplicationStatus.SELECTED: [
                ApplicationStatus.UNDER_REVIEW, ApplicationStatus.SHORTLISTED,
                ApplicationStatus.INTERVIEW, ApplicationStatus.OFFERED,
                ApplicationStatus.SELECTED,
            ],
            ApplicationStatus.REJECTED: [
                ApplicationStatus.UNDER_REVIEW, ApplicationStatus.REJECTED
            ],
            ApplicationStatus.WITHDRAWN: [ApplicationStatus.WITHDRAWN],
        }[target_status]

        recruiter = recruiters.get(
            opportunity.company.name if opportunity.company else "", None
        )
        cursor = submitted
        previous = ApplicationStatus.APPLIED
        for step in path:
            cursor += timedelta(days=RNG.randint(1, 6))
            db.add(
                ApplicationStatusHistory(
                    application_id=application.id, from_status=previous, to_status=step,
                    changed_by_id=(
                        student.user_id if step == ApplicationStatus.WITHDRAWN
                        else (recruiter.id if recruiter else None)
                    ),
                    note=f"Moved to {step.value.replace('_', ' ').lower()}",
                    created_at=cursor,
                )
            )
            previous = step
        application.status = target_status
        application.last_status_change_at = cursor
        if target_status in (
            ApplicationStatus.SELECTED, ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        ):
            application.decided_at = cursor
        if target_status == ApplicationStatus.REJECTED:
            application.rejection_reason = RNG.choice(
                [
                    "Stronger candidates at this stage",
                    "Looking for more depth in the core stack",
                    "Role filled",
                ]
            )

        if target_status in (
            ApplicationStatus.INTERVIEW, ApplicationStatus.OFFERED,
            ApplicationStatus.SELECTED,
        ):
            db.add(
                Interview(
                    application_id=application.id, round_number=1,
                    round_name="Technical Round", mode="ONLINE",
                    scheduled_at=cursor + timedelta(days=RNG.randint(1, 10)),
                    duration_minutes=45,
                    location_or_link="https://meet.example.com/interview",
                    interviewer_user_id=recruiter.id if recruiter else None,
                    interviewer_name=recruiter.full_name if recruiter else None,
                    status="COMPLETED" if target_status != ApplicationStatus.INTERVIEW
                    else "SCHEDULED",
                )
            )

        if target_status == ApplicationStatus.SELECTED:
            db.add(
                ExperienceRecord(
                    student_id=student.id,
                    kind="INTERNSHIP"
                    if opportunity.opportunity_type == OpportunityType.INTERNSHIP
                    else "JOB",
                    title=opportunity.title,
                    organization=opportunity.company.name if opportunity.company else "",
                    location=opportunity.location_city, work_mode=opportunity.work_mode,
                    description="Selected through SkillBridge.",
                    start_date=opportunity.starts_on,
                    skill_tags=result.matching_skills[:5],
                    source_application_id=application.id, is_verified=True,
                    verified_by_company_id=opportunity.company_id,
                )
            )
            if opportunity.opportunity_type == OpportunityType.JOB:
                student.is_placed = True
                student.placed_company_id = opportunity.company_id

        opportunity.applications_count = (opportunity.applications_count or 0) + 1
        opportunity.views_count = (opportunity.views_count or 0) + RNG.randint(5, 120)
        created += 1

    await db.flush()
    log.info("seed.applications_created", count=created)
    return created


async def seed_engagement(
    db: AsyncSession, students: list[StudentProfile], programs: list[LearningProgram],
    events: list[Event], mentors: list[MentorProfile],
) -> None:
    """Enrolments, certifications, event registrations and mentorship threads."""
    for student in RNG.sample(students, k=min(30, len(students))):
        for program in RNG.sample(programs, k=RNG.randint(1, 3)):
            exists = (
                await db.execute(
                    select(Enrollment).where(
                        Enrollment.student_id == student.id,
                        Enrollment.program_id == program.id,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                continue
            progress = RNG.choice([0, 20, 45, 70, 100])
            status = (
                EnrollmentStatus.COMPLETED if progress == 100
                else EnrollmentStatus.IN_PROGRESS if progress
                else EnrollmentStatus.ENROLLED
            )
            enrolled_at = _now() - timedelta(days=RNG.randint(5, 120))
            db.add(
                Enrollment(
                    program_id=program.id, student_id=student.id, status=status,
                    progress_percentage=progress, enrolled_at=enrolled_at,
                    started_at=enrolled_at if progress else None,
                    completed_at=_now() if progress == 100 else None,
                    last_activity_at=_now() - timedelta(days=RNG.randint(0, 20)),
                    is_demo=True,
                )
            )
            program.enrollment_count += 1
            if progress == 100:
                # awaitable_attrs: the collection was populated by separate
                # inserts, so it is not loaded on these instances.
                program_skills = await program.awaitable_attrs.skills
                db.add(
                    StudentCertification(
                        student_id=student.id, name=program.title,
                        issuer=program.provider_name or "SkillBridge",
                        issued_on=date.today() - timedelta(days=RNG.randint(1, 60)),
                        skill_ids=[str(s.skill_id) for s in program_skills],
                        verification_status=VerificationStatus.VERIFIED,
                        is_demo=True,
                    )
                )

    for event in events:
        for student in RNG.sample(students, k=min(RNG.randint(5, 20), len(students))):
            exists = (
                await db.execute(
                    select(EventRegistration).where(
                        EventRegistration.event_id == event.id,
                        EventRegistration.user_id == student.user_id,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                continue
            db.add(
                EventRegistration(
                    event_id=event.id, user_id=student.user_id,
                    status=RegistrationStatus.REGISTERED, is_demo=True,
                )
            )
            event.registered_count += 1

    topics = [
        "Preparing for backend interviews", "Choosing between data and backend",
        "Portfolio review", "Breaking into security", "Getting started with cloud",
    ]
    for student in RNG.sample(students, k=min(18, len(students))):
        mentor = RNG.choice(mentors)
        exists = (
            await db.execute(
                select(MentorshipRequest).where(
                    MentorshipRequest.mentor_id == mentor.id,
                    MentorshipRequest.student_id == student.id,
                )
            )
        ).scalar_one_or_none()
        if exists is not None:
            continue
        status = RNG.choice(
            [
                MentorshipStatus.REQUESTED, MentorshipStatus.ACCEPTED,
                MentorshipStatus.SCHEDULED, MentorshipStatus.COMPLETED,
            ]
        )
        request = MentorshipRequest(
            mentor_id=mentor.id, student_id=student.id,
            topic=RNG.choice(topics),
            message="I would value 30 minutes to talk through what to focus on next.",
            goals=["Understand what employers expect", "Get portfolio feedback"],
            status=status,
            responded_at=_now() if status != MentorshipStatus.REQUESTED else None,
            is_demo=True,
        )
        db.add(request)
        await db.flush()
        if status in (MentorshipStatus.SCHEDULED, MentorshipStatus.COMPLETED):
            scheduled = _now() + timedelta(days=RNG.randint(-20, 20))
            db.add(
                MentorshipSession(
                    request_id=request.id, scheduled_at=scheduled,
                    duration_minutes=mentor.session_duration_minutes,
                    meeting_link="https://meet.example.com/mentorship",
                    agenda=request.topic,
                    status="COMPLETED" if status == MentorshipStatus.COMPLETED
                    else "SCHEDULED",
                    completed_at=scheduled if status == MentorshipStatus.COMPLETED else None,
                    student_rating=RNG.randint(4, 5)
                    if status == MentorshipStatus.COMPLETED
                    else None,
                )
            )
    await db.flush()


async def seed_assessment_attempts(
    db: AsyncSession, students: list[StudentProfile], count_per_student: int = 2
) -> int:
    """Give a slice of students real, scored assessment history.

    Attempts are scored with the production scoring function, so the resulting
    percentages, per-skill breakdowns and confidences are genuine rather than
    invented numbers.
    """
    from app.models.assessment import (
        Assessment,
        AssessmentAnswer,
        AssessmentAttempt,
        AssessmentQuestion,
        AttemptSkillScore,
    )
    from app.models.enums import AttemptStatus
    from app.services.assessment import confidence_for, score_question

    assessments = (
        await db.execute(
            select(Assessment)
            .where(Assessment.is_published.is_(True))
            .options(
                __import__("sqlalchemy.orm", fromlist=["selectinload"]).selectinload(
                    Assessment.questions
                ).selectinload(AssessmentQuestion.options)
            )
        )
    ).scalars().all()
    if not assessments:
        return 0

    demo_student_ids = set(
        (
            await db.execute(
                select(StudentProfile.id)
                .join(User, User.id == StudentProfile.user_id)
                .where(User.email == "student@demo.com")
            )
        ).scalars()
    )

    created = 0
    for student in RNG.sample(students, k=min(28, len(students))):
        for assessment in RNG.sample(assessments, k=min(count_per_student, len(assessments))):
            exists = (
                await db.execute(
                    select(AssessmentAttempt).where(
                        AssessmentAttempt.student_id == student.id,
                        AssessmentAttempt.assessment_id == assessment.id,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                continue
            questions = [q for q in assessment.questions if q.is_active]
            if not questions:
                continue

            # Ability determines how often this student answers correctly.
            # The documented demo account gets a strong draw so the login shows
            # a credible "strong but improving" profile rather than a random one.
            ability = (
                RNG.uniform(0.82, 0.95)
                if student.id in demo_student_ids
                else RNG.uniform(0.35, 0.95)
            )
            started = _now() - timedelta(days=RNG.randint(2, 60))
            attempt = AssessmentAttempt(
                assessment_id=assessment.id, student_id=student.id, attempt_number=1,
                status=AttemptStatus.EVALUATED, started_at=started,
                expires_at=started + timedelta(minutes=assessment.duration_minutes),
                submitted_at=started + timedelta(minutes=RNG.randint(5, assessment.duration_minutes)),
                duration_seconds=RNG.randint(300, assessment.duration_minutes * 60),
                question_order=[str(q.id) for q in questions],
            )
            db.add(attempt)
            await db.flush()

            by_skill: dict[Any, dict[str, float]] = {}
            total_awarded = total_max = 0.0
            for question in questions:
                correct = [o.id for o in question.options if o.is_correct]
                options = list(question.options)
                if question.question_type.value == "LIKERT":
                    chosen = [
                        max(options, key=lambda o: (o.proficiency_value or 0)).id
                        if RNG.random() < ability
                        else RNG.choice(options).id
                    ]
                elif RNG.random() < ability and correct:
                    chosen = correct
                else:
                    wrong = [o.id for o in options if o.id not in correct]
                    chosen = [RNG.choice(wrong)] if wrong else []

                awarded, maximum, is_correct = score_question(question, chosen)
                total_awarded += awarded
                total_max += maximum
                db.add(
                    AssessmentAnswer(
                        attempt_id=attempt.id, question_id=question.id,
                        selected_option_ids=[str(c) for c in chosen],
                        is_correct=is_correct, awarded_score=awarded, max_score=maximum,
                        time_spent_seconds=RNG.randint(20, 180),
                    )
                )
                bucket = by_skill.setdefault(
                    question.skill_id, {"score": 0.0, "max": 0.0, "q": 0, "c": 0}
                )
                bucket["score"] += awarded
                bucket["max"] += maximum
                bucket["q"] += 1
                bucket["c"] += 1 if is_correct else 0

            percentage = round(total_awarded / total_max * 100, 2) if total_max else 0.0
            attempt.raw_score = round(total_awarded, 2)
            attempt.max_score = round(total_max, 2)
            attempt.percentage = percentage
            attempt.is_passed = percentage >= assessment.passing_score
            attempt.confidence = confidence_for(len(questions))
            attempt.feedback = (
                "You passed. Your skill profile has been updated."
                if attempt.is_passed
                else "Review the explanations and retake when ready."
            )

            for skill_id, bucket in by_skill.items():
                skill_percentage = (
                    round(bucket["score"] / bucket["max"] * 100, 2) if bucket["max"] else 0.0
                )
                level = ProficiencyLevel.from_score(skill_percentage)
                db.add(
                    AttemptSkillScore(
                        attempt_id=attempt.id, skill_id=skill_id,
                        score=round(bucket["score"], 2), max_score=round(bucket["max"], 2),
                        percentage=skill_percentage, questions_count=int(bucket["q"]),
                        correct_count=int(bucket["c"]),
                        confidence=confidence_for(int(bucket["q"])), level=level,
                    )
                )
                await skill_service.upsert_student_skill(
                    db, student.id, skill_id, level=level,
                    source=SkillSource.ASSESSMENT, score=skill_percentage,
                    confidence=confidence_for(int(bucket["q"])),
                    evidence={
                        "assessment_id": str(assessment.id),
                        "assessment_title": assessment.title,
                        "attempt_id": str(attempt.id),
                        "percentage": skill_percentage,
                    },
                    mark_assessed=True,
                )
            created += 1
    await db.flush()
    log.info("seed.assessment_attempts_created", count=created)
    return created


async def seed_partnerships(
    db: AsyncSession, institutions: dict[str, Institution], companies: dict[str, Company]
) -> None:
    for institution in institutions.values():
        for company in RNG.sample(list(companies.values()), k=RNG.randint(2, 5)):
            exists = (
                await db.execute(
                    select(IndustryPartnership).where(
                        IndustryPartnership.institution_id == institution.id,
                        IndustryPartnership.company_id == company.id,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                continue
            db.add(
                IndustryPartnership(
                    institution_id=institution.id, company_id=company.id,
                    partnership_type=RNG.choice(
                        ["PLACEMENT", "INTERNSHIP", "RESEARCH", "TRAINING"]
                    ),
                    status="ACTIVE",
                    summary=f"{company.name} partners with {institution.short_name} on "
                            "placements and industry-led training.",
                    started_on=f"{RNG.randint(2019, 2025)}-06-01",
                    engagement_score=RNG.randint(40, 98),
                )
            )
    await db.flush()


# ========================================================== demo accounts
async def seed_demo_accounts(
    db: AsyncSession, institutions: dict[str, Institution], companies: dict[str, Company],
    roles: dict[RoleName, Role], skills: dict[str, Skill], job_roles: dict[str, JobRole],
) -> list[tuple[str, str]]:
    """The five labelled demo logins documented in the README."""
    password = settings.SEED_DEMO_PASSWORD
    institution = next(iter(institutions.values()))
    company = next(iter(companies.values()))
    await db.refresh(institution, ["departments"])
    created: list[tuple[str, str]] = []

    for email, role_name, full_name in DEMO_ACCOUNTS:
        existing = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            created.append((email, role_name.value))
            continue

        user = await _create_user(
            db, email=email, full_name=full_name, role=roles[role_name],
            institution_id=(
                institution.id
                if role_name in (RoleName.STUDENT, RoleName.ACADEMICIAN,
                                 RoleName.INSTITUTION_ADMIN)
                else None
            ),
            company_id=(
                company.id
                if role_name in (RoleName.INDUSTRY_RECRUITER, RoleName.INDUSTRY_ADMIN)
                else None
            ),
            password=password,
        )

        if role_name == RoleName.STUDENT:
            target = job_roles.get("backend-developer")
            profile = StudentProfile(
                user_id=user.id, institution_id=institution.id,
                department_id=institution.departments[0].id if institution.departments else None,
                headline="Final-year CS student · aspiring backend engineer",
                bio="I build backend services and care about clean data models. "
                    "Currently deepening my FastAPI and Docker skills.",
                city=institution.city, enrollment_number="PIT20271001",
                degree=Degree.BACHELORS, program_name="B.Tech Computer Engineering",
                current_year=4, current_semester=7, cgpa=8.4, graduation_year=2027,
                career_interests=["Backend Development", "Cloud"],
                preferred_roles=["Backend Developer", "Full Stack Developer"],
                preferred_industries=["Cloud Infrastructure", "Data & AI"],
                preferred_locations=["Bengaluru", "Pune"],
                preferred_work_mode=WorkMode.HYBRID,
                expected_stipend_min=25000,
                target_job_role_id=target.id if target else None,
                portfolio_slug="aditi-sharma-demo",
                portfolio_visibility=Visibility.PUBLIC,
                github_url="https://github.com/aditi-demo",
                linkedin_url="https://linkedin.com/in/aditi-demo",
                is_demo=True,
            )
            db.add(profile)
            await db.flush()
            for slug, level in [
                ("python", "ADVANCED"), ("sql", "ADVANCED"), ("postgresql", "INTERMEDIATE"),
                ("rest-api", "INTERMEDIATE"), ("git", "ADVANCED"), ("docker", "BEGINNER"),
                ("fastapi", "BEGINNER"), ("javascript", "INTERMEDIATE"),
                ("problem-solving", "ADVANCED"), ("communication", "INTERMEDIATE"),
            ]:
                skill = skills.get(slug)
                if skill is None:
                    continue
                proficiency = ProficiencyLevel(level)
                db.add(
                    StudentSkill(
                        student_id=profile.id, skill_id=skill.id, level=proficiency,
                        score=min(100.0, proficiency.score * 25),
                        confidence=0.9 if slug in ("python", "sql") else 0.4,
                        source=SkillSource.ASSESSMENT
                        if slug in ("python", "sql")
                        else SkillSource.SELF_REPORTED,
                        last_assessed_at=_now() if slug in ("python", "sql") else None,
                    )
                )
            db.add(
                EducationRecord(
                    student_id=profile.id, level=Degree.BACHELORS,
                    institution_name=institution.name, program="B.Tech Computer Engineering",
                    start_year=2023, end_year=2027, score_value=8.4, score_type="CGPA",
                    is_verified=True,
                )
            )
            db.add(
                StudentProject(
                    student_id=profile.id, title="Campus Placement Tracker",
                    description="A dashboard for the placement cell, with role-based "
                                "access and application tracking.",
                    role="Solo", team_size=1,
                    skill_tags=["Python", "PostgreSQL", "React"],
                    repository_url="https://github.com/aditi-demo/placement-tracker",
                    highlights=["Used by 400 students", "Cut manual tracking to zero"],
                    is_featured=True,
                )
            )
            db.add(
                Portfolio(
                    student_id=profile.id, slug="aditi-sharma-demo",
                    headline=profile.headline, about=profile.bio,
                    visibility=Visibility.PUBLIC,
                    sections=["about", "skills", "experience", "projects", "education",
                              "certifications", "achievements"],
                    contact_email_visible=True, published_at=_now(),
                )
            )

        elif role_name == RoleName.ACADEMICIAN:
            db.add(
                AcademicianProfile(
                    user_id=user.id, institution_id=institution.id,
                    designation="Professor", employee_code="FAC1001",
                    highest_qualification="Ph.D.",
                    specialization="Computer Engineering",
                    teaching_experience_years=16, industry_experience_years=4,
                    research_areas=["Distributed Systems", "Software Engineering"],
                    expertise_areas=["Cloud Architecture", "Software Engineering"],
                    publications_count=34, patents_count=2,
                    bio="Professor of Computer Engineering with an interest in "
                        "industry-linked curriculum design.",
                    city=institution.city, is_available_for_mentorship=True,
                    is_available_for_consultancy=True, profile_completion=95,
                    is_demo=True,
                )
            )

        elif role_name in (RoleName.INDUSTRY_RECRUITER, RoleName.INDUSTRY_ADMIN):
            db.add(
                RecruiterProfile(
                    user_id=user.id, company_id=company.id,
                    designation="Head of Talent"
                    if role_name == RoleName.INDUSTRY_ADMIN
                    else "Technical Recruiter",
                    hiring_domains=[company.industry_sector],
                    is_primary_contact=role_name == RoleName.INDUSTRY_ADMIN,
                    is_demo=True,
                )
            )

        created.append((email, role_name.value))
    await db.flush()
    return created


# ==================================================================== main
async def run(reset: bool = False, catalog_only: bool = False, students: int = 50) -> None:
    if settings.is_production:
        sys.exit(
            "Refusing to seed a production environment. "
            "Seed data is for development and demonstration only."
        )

    if reset:
        log.warning("seed.resetting_database")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    await sync_rbac_catalogue()

    async with AsyncSessionLocal() as db:
        catalog_stats = await seed_catalog(db)
        assessment_stats = await seed_assessments(db)
        await db.commit()

        if catalog_only:
            log.info("seed.catalog_only_done", **catalog_stats, **assessment_stats)
            _print_summary(catalog_stats, assessment_stats, {})
            return

        skills = {s.slug: s for s in (await db.execute(select(Skill))).scalars()}
        job_roles = {r.slug: r for r in (await db.execute(select(JobRole))).scalars()}
        roles = await _role_map(db)

        institutions = await seed_institutions(db)
        companies = await seed_companies(db)
        await db.commit()

        recruiters = await seed_company_users(db, companies, roles)
        await seed_institution_admins(db, institutions, roles)
        academicians = await seed_academicians(db, institutions, roles)
        student_profiles = await seed_students(
            db, institutions, roles, skills, job_roles, count=students
        )
        # Demo accounts are created before activity is generated so the
        # flagship student@demo.com login lands on a populated dashboard
        # rather than an empty state.
        demo_accounts = await seed_demo_accounts(
            db, institutions, companies, roles, skills, job_roles
        )
        await db.commit()

        demo_student = (
            await db.execute(
                select(StudentProfile)
                .join(User, User.id == StudentProfile.user_id)
                .where(User.email == "student@demo.com")
            )
        ).scalar_one_or_none()
        if demo_student is not None and demo_student not in student_profiles:
            student_profiles.append(demo_student)

        opportunities = await seed_opportunities(
            db, companies, recruiters, job_roles, skills
        )
        programs = await seed_programs(db, companies, recruiters, skills)
        events = await seed_events(db, companies, recruiters)
        mentors = await seed_mentors(db, recruiters, academicians, companies, skills)
        await seed_research(db, companies, recruiters, institutions, academicians)
        await seed_partnerships(db, institutions, companies)
        await db.commit()

        await seed_assessment_attempts(db, student_profiles)
        await db.commit()

        await seed_applications(db, student_profiles, opportunities, recruiters)
        await seed_engagement(db, student_profiles, programs, events, mentors)
        await db.commit()

        # Demand is derived from the postings we just created.
        await skill_service.refresh_skill_demand(db)

        # Readiness and profile completion for everyone, so dashboards are live.
        from app.services import student as student_service

        for profile in student_profiles:
            await skill_service.refresh_student_readiness(db, profile)
            await student_service.compute_profile_completion(db, profile)
            await student_service.evaluate_badges(db, profile)
        await db.commit()

        await _ensure_demo_student_activity(
            db, demo_student, opportunities, programs, events, mentors
        )
        await db.commit()

        counts = await _counts(db)
        _print_summary(catalog_stats, assessment_stats, counts, demo_accounts)

    await engine.dispose()


async def _ensure_demo_student_activity(
    db: AsyncSession, student: StudentProfile | None,
    opportunities: dict[str, list[Opportunity]], programs: list[LearningProgram],
    events: list[Event], mentors: list[MentorProfile],
) -> None:
    """Guarantee the documented demo login has something in every section.

    Random sampling alone can leave the flagship account empty, which makes a
    demo look broken. This fills each area deterministically if it is bare.
    """
    if student is None:
        return
    from app.services import opportunity as opportunity_service

    has_application = (
        await db.execute(
            select(func.count())
            .select_from(Application)
            .where(Application.student_id == student.id)
        )
    ).scalar_one()
    if has_application < 3:
        stages = [
            ApplicationStatus.APPLIED,
            ApplicationStatus.SHORTLISTED,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.REJECTED,
        ]
        walks = {
            ApplicationStatus.APPLIED: [ApplicationStatus.APPLIED],
            ApplicationStatus.SHORTLISTED: [
                ApplicationStatus.APPLIED, ApplicationStatus.UNDER_REVIEW,
                ApplicationStatus.SHORTLISTED,
            ],
            ApplicationStatus.INTERVIEW: [
                ApplicationStatus.APPLIED, ApplicationStatus.UNDER_REVIEW,
                ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW,
            ],
            ApplicationStatus.REJECTED: [
                ApplicationStatus.APPLIED, ApplicationStatus.UNDER_REVIEW,
                ApplicationStatus.REJECTED,
            ],
        }
        pool = opportunities["internships"][:6] + opportunities["jobs"][:2]
        for stage, opportunity in zip(stages, pool, strict=False):
            await db.refresh(opportunity, ["company", "job_role"])
            result = await opportunity_service.match_student_to_opportunity(
                db, student, opportunity
            )
            submitted = _now() - timedelta(days=RNG.randint(4, 25))
            application = Application(
                opportunity_id=opportunity.id, student_id=student.id, status=stage,
                cover_letter=(
                    "I have shipped a placement tracker end to end and would value "
                    "working on production services."
                ),
                match_score=result.match_score, match_breakdown=result.breakdown,
                matching_skills=result.matching_skills,
                missing_skills=result.missing_skills,
                submitted_at=submitted,
                last_status_change_at=submitted + timedelta(days=2),
                decided_at=(
                    submitted + timedelta(days=4)
                    if stage == ApplicationStatus.REJECTED
                    else None
                ),
                rejection_reason=(
                    "Stronger candidates at this stage"
                    if stage == ApplicationStatus.REJECTED
                    else None
                ),
                is_demo=True,
            )
            db.add(application)
            await db.flush()

            previous = None
            cursor = submitted
            for step in walks[stage]:
                db.add(
                    ApplicationStatusHistory(
                        application_id=application.id, from_status=previous,
                        to_status=step,
                        note=f"Moved to {step.value.replace('_', ' ').title()}",
                        created_at=cursor,
                    )
                )
                previous = step
                cursor += timedelta(days=2)

            if stage == ApplicationStatus.INTERVIEW:
                db.add(
                    Interview(
                        application_id=application.id, round_number=1,
                        round_name="Technical Round", mode="ONLINE",
                        scheduled_at=_now() + timedelta(days=3), duration_minutes=45,
                        location_or_link="https://meet.example.com/demo-interview",
                        status="SCHEDULED",
                    )
                )
            opportunity.applications_count = (opportunity.applications_count or 0) + 1

    has_enrolment = (
        await db.execute(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.student_id == student.id)
        )
    ).scalar_one()
    if not has_enrolment and programs:
        for program, progress in zip(programs[:3], (100, 45, 0), strict=False):
            enrolled_at = _now() - timedelta(days=RNG.randint(10, 90))
            db.add(
                Enrollment(
                    program_id=program.id, student_id=student.id,
                    status=(
                        EnrollmentStatus.COMPLETED if progress == 100
                        else EnrollmentStatus.IN_PROGRESS if progress
                        else EnrollmentStatus.ENROLLED
                    ),
                    progress_percentage=progress, enrolled_at=enrolled_at,
                    started_at=enrolled_at if progress else None,
                    completed_at=_now() if progress == 100 else None,
                    last_activity_at=_now() - timedelta(days=2), is_demo=True,
                )
            )
            program.enrollment_count += 1
            if progress == 100:
                program_skills = await program.awaitable_attrs.skills
                db.add(
                    StudentCertification(
                        student_id=student.id, name=program.title,
                        issuer=program.provider_name or "SkillBridge",
                        issued_on=date.today() - timedelta(days=14),
                        skill_ids=[str(s.skill_id) for s in program_skills],
                        verification_status=VerificationStatus.VERIFIED, is_demo=True,
                    )
                )

    has_event = (
        await db.execute(
            select(func.count())
            .select_from(EventRegistration)
            .where(EventRegistration.user_id == student.user_id)
        )
    ).scalar_one()
    if not has_event:
        for event in events[:3]:
            db.add(
                EventRegistration(
                    event_id=event.id, user_id=student.user_id,
                    status=RegistrationStatus.REGISTERED, is_demo=True,
                )
            )
            event.registered_count += 1

    has_mentorship = (
        await db.execute(
            select(func.count())
            .select_from(MentorshipRequest)
            .where(MentorshipRequest.student_id == student.id)
        )
    ).scalar_one()
    if not has_mentorship and mentors:
        request = MentorshipRequest(
            mentor_id=mentors[0].id, student_id=student.id,
            topic="Preparing for backend interviews",
            message="I would value 30 minutes on what to prioritise before applying.",
            goals=["Understand expectations", "Get portfolio feedback"],
            status=MentorshipStatus.SCHEDULED, responded_at=_now(), is_demo=True,
        )
        db.add(request)
        await db.flush()
        db.add(
            MentorshipSession(
                request_id=request.id, scheduled_at=_now() + timedelta(days=5),
                duration_minutes=45,
                meeting_link="https://meet.example.com/demo-mentorship",
                agenda=request.topic, status="SCHEDULED",
            )
        )
    await db.flush()


async def _counts(db: AsyncSession) -> dict[str, int]:
    async def count(model, *where) -> int:
        stmt = select(func.count()).select_from(model)
        if where:
            stmt = stmt.where(*where)
        return (await db.execute(stmt)).scalar_one()

    return {
        "users": await count(User),
        "students": await count(StudentProfile),
        "academicians": await count(AcademicianProfile),
        "institutions": await count(Institution),
        "companies": await count(Company),
        "internships": await count(
            Opportunity, Opportunity.opportunity_type == OpportunityType.INTERNSHIP
        ),
        "jobs": await count(Opportunity, Opportunity.opportunity_type == OpportunityType.JOB),
        "live_projects": await count(
            Opportunity, Opportunity.opportunity_type == OpportunityType.LIVE_PROJECT
        ),
        "faculty_programmes": await count(
            Opportunity,
            Opportunity.opportunity_type == OpportunityType.FACULTY_OPPORTUNITY,
        ),
        "applications": await count(Application),
        "learning_programs": await count(LearningProgram),
        "enrollments": await count(Enrollment),
        "certifications": await count(StudentCertification),
        "mentors": await count(MentorProfile),
        "mentorship_requests": await count(MentorshipRequest),
        "events": await count(Event),
        "event_registrations": await count(EventRegistration),
        "research_projects": await count(ResearchProject),
        "partnerships": await count(IndustryPartnership),
        "assessment_attempts": await count(AssessmentAttempt),
    }


def _print_summary(
    catalog_stats: dict, assessment_stats: dict, counts: dict,
    demo_accounts: list[tuple[str, str]] | None = None,
) -> None:
    line = "=" * 68
    print(f"\n{line}\n  SkillBridge seed complete\n{line}")
    print("\n  Reference catalogue")
    for key, value in catalog_stats.items():
        print(f"    {key:<24} {value:>5} created")
    for key, value in assessment_stats.items():
        print(f"    {key:<24} {value:>5} created")
    if counts:
        print("\n  Demo dataset (all rows flagged is_demo = true)")
        for key, value in counts.items():
            print(f"    {key:<24} {value:>5}")
    if demo_accounts:
        print("\n  Demo accounts — DEVELOPMENT ONLY, never use in production")
        print(f"    password for every account: {settings.SEED_DEMO_PASSWORD}")
        for email, role in demo_accounts:
            print(f"    {email:<28} {role}")
    print(f"\n{line}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the SkillBridge database")
    parser.add_argument("--reset", action="store_true", help="drop and recreate all tables")
    parser.add_argument(
        "--catalog-only", action="store_true",
        help="load only the skill/role/assessment catalogue, no demo data",
    )
    parser.add_argument("--students", type=int, default=50, help="number of demo students")
    args = parser.parse_args()
    asyncio.run(run(reset=args.reset, catalog_only=args.catalog_only, students=args.students))


if __name__ == "__main__":
    main()
