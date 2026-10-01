"""Role-based access control.

Permissions are ``resource:action`` strings. The catalogue below is the single
source of truth: it is synchronised into the ``permissions`` / ``roles`` tables
at bootstrap, so the database and the code can never drift apart.

Object-level rules (e.g. "a recruiter may only edit their own company's jobs")
are enforced in the service layer; this module covers the coarse-grained layer.
"""
from __future__ import annotations

from app.models.enums import RoleName

# ---------------------------------------------------------------- catalogue --
PERMISSIONS: dict[str, str] = {
    # profile & identity
    "profile:read_self": "Read own profile",
    "profile:update_self": "Update own profile",
    "user:read_any": "Read any user account",
    "user:manage": "Create, suspend and delete user accounts",
    "role:assign": "Grant or revoke roles",
    # skills & taxonomy
    "skill:read": "Browse the skill taxonomy",
    "skill:manage": "Create and edit skills, categories and job roles",
    "student_skill:manage_self": "Manage own skill profile",
    "skill_gap:read_self": "Run and read own skill-gap analysis",
    # assessments
    "assessment:read": "Browse available assessments",
    "assessment:attempt": "Start and submit assessment attempts",
    "assessment:manage": "Author assessments, questions and options",
    # opportunities
    "opportunity:read": "Browse published opportunities",
    "opportunity:create": "Create internships, jobs and projects",
    "opportunity:update": "Edit own organisation's opportunities",
    "opportunity:delete": "Close or delete own organisation's opportunities",
    "opportunity:moderate": "Moderate any opportunity on the platform",
    # applications
    "application:create": "Apply to an opportunity",
    "application:read_self": "Read own applications",
    "application:withdraw": "Withdraw own application",
    "application:review": "Review applicants and change application status",
    "application:export": "Export candidate data",
    # learning
    "program:read": "Browse learning programmes",
    "program:manage": "Publish and edit learning programmes",
    "enrollment:manage_self": "Enrol in and progress through programmes",
    # mentorship
    "mentor:read": "Browse mentors",
    "mentor:manage_self": "Maintain own mentor profile",
    "mentorship:request": "Request mentorship",
    "mentorship:respond": "Accept, decline and schedule mentorship",
    # events
    "event:read": "Browse events",
    "event:manage": "Create and manage events",
    "event:register": "Register for events",
    # projects & research
    "project:manage": "Manage live project milestones and evaluation",
    "project:participate": "Join teams and submit project work",
    "research:read": "Browse research and consultancy opportunities",
    "research:manage": "Create research and consultancy projects",
    "research:apply": "Apply to research and consultancy projects",
    # documents & portfolio
    "document:upload": "Upload documents",
    "document:read_self": "Read own documents",
    "document:read_granted": "Read documents shared through an application",
    "portfolio:manage_self": "Manage own digital portfolio and resumes",
    # messaging & notifications
    "message:send": "Send messages in permitted conversations",
    "notification:read_self": "Read own notifications",
    # analytics
    "analytics:institution": "View institution analytics",
    "analytics:industry": "View industry analytics",
    "analytics:platform": "View platform-wide analytics",
    "report:export": "Export CSV/PDF reports",
    # administration
    "institution:manage": "Manage institution records and departments",
    "company:manage": "Manage own company profile",
    "company:manage_any": "Manage any company record",
    "audit:read": "Read the audit trail",
    "system:manage": "Change system settings",
}

# ------------------------------------------------------------ role mapping --
_STUDENT = {
    "profile:read_self", "profile:update_self", "skill:read",
    "student_skill:manage_self", "skill_gap:read_self", "assessment:read",
    "assessment:attempt", "opportunity:read", "application:create",
    "application:read_self", "application:withdraw", "program:read",
    "enrollment:manage_self", "mentor:read", "mentorship:request",
    "event:read", "event:register", "project:participate", "document:upload",
    "document:read_self", "portfolio:manage_self", "message:send",
    "notification:read_self",
}

_ACADEMICIAN = {
    "profile:read_self", "profile:update_self", "skill:read", "assessment:read",
    "opportunity:read", "application:create", "application:read_self",
    "application:withdraw", "program:read", "mentor:read",
    "mentor:manage_self", "mentorship:respond", "event:read", "event:register",
    "event:manage", "research:read", "research:apply", "document:upload",
    "document:read_self", "message:send", "notification:read_self",
}

_INDUSTRY_RECRUITER = {
    "profile:read_self", "profile:update_self", "skill:read", "opportunity:read",
    "opportunity:create", "opportunity:update", "application:review",
    "application:export", "program:read", "mentor:read", "mentor:manage_self",
    "mentorship:respond", "event:read", "event:manage", "event:register",
    "project:manage", "research:read", "document:upload", "document:read_self",
    "document:read_granted", "message:send", "notification:read_self",
    "analytics:industry",
}

_INDUSTRY_ADMIN = _INDUSTRY_RECRUITER | {
    "opportunity:delete", "program:manage", "company:manage", "research:manage",
    "report:export",
}

_INSTITUTION_ADMIN = {
    "profile:read_self", "profile:update_self", "user:read_any", "skill:read",
    "assessment:read", "opportunity:read", "program:read", "mentor:read",
    "event:read", "event:manage", "research:read", "research:manage",
    "document:read_self", "document:upload", "message:send",
    "notification:read_self", "analytics:institution", "report:export",
    "institution:manage", "application:export",
}

_SUPER_ADMIN = set(PERMISSIONS)

ROLE_PERMISSIONS: dict[RoleName, set[str]] = {
    RoleName.STUDENT: _STUDENT,
    RoleName.ACADEMICIAN: _ACADEMICIAN,
    RoleName.INDUSTRY_RECRUITER: _INDUSTRY_RECRUITER,
    RoleName.INDUSTRY_ADMIN: _INDUSTRY_ADMIN,
    RoleName.INSTITUTION_ADMIN: _INSTITUTION_ADMIN,
    RoleName.SUPER_ADMIN: _SUPER_ADMIN,
}

ROLE_LABELS: dict[RoleName, tuple[str, str, bool]] = {
    # name -> (label, description, self-serve signup allowed)
    RoleName.STUDENT: ("Student", "Learner building employability", True),
    RoleName.ACADEMICIAN: ("Academician", "Faculty member or researcher", True),
    RoleName.INDUSTRY_RECRUITER: (
        "Recruiter", "Hires talent on behalf of a company", True,
    ),
    RoleName.INDUSTRY_ADMIN: (
        "Industry Admin", "Owns a company workspace on SkillBridge", True,
    ),
    RoleName.INSTITUTION_ADMIN: (
        "Institution Admin", "Runs placements and analytics for an institution", False,
    ),
    RoleName.SUPER_ADMIN: ("Platform Admin", "Full platform administration", False),
}

# Landing route per role, consumed by the frontend after login.
ROLE_HOME: dict[str, str] = {
    RoleName.STUDENT: "/student/dashboard",
    RoleName.ACADEMICIAN: "/academician/dashboard",
    RoleName.INDUSTRY_RECRUITER: "/industry/dashboard",
    RoleName.INDUSTRY_ADMIN: "/industry/dashboard",
    RoleName.INSTITUTION_ADMIN: "/institution/dashboard",
    RoleName.SUPER_ADMIN: "/admin/dashboard",
}

COMPANY_ROLES = {RoleName.INDUSTRY_RECRUITER, RoleName.INDUSTRY_ADMIN}
INSTITUTION_ROLES = {RoleName.STUDENT, RoleName.ACADEMICIAN, RoleName.INSTITUTION_ADMIN}


def permissions_for(role: RoleName | str) -> set[str]:
    key = RoleName(role) if not isinstance(role, RoleName) else role
    return set(ROLE_PERMISSIONS.get(key, set()))


def permissions_for_roles(roles: list[str]) -> set[str]:
    out: set[str] = set()
    for r in roles:
        try:
            out |= permissions_for(r)
        except ValueError:  # pragma: no cover - unknown role string
            continue
    return out


def default_home(roles: list[str]) -> str:
    for role in (
        RoleName.SUPER_ADMIN, RoleName.INSTITUTION_ADMIN, RoleName.INDUSTRY_ADMIN,
        RoleName.INDUSTRY_RECRUITER, RoleName.ACADEMICIAN, RoleName.STUDENT,
    ):
        if role.value in roles:
            return ROLE_HOME[role.value]
    return "/"
