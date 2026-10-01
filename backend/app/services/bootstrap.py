"""Idempotent bootstrap: sync the RBAC catalogue and badge definitions."""
from __future__ import annotations

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.core.rbac import PERMISSIONS, ROLE_LABELS, ROLE_PERMISSIONS
from app.models.enums import BadgeCode
from app.models.portfolio import Badge
from app.models.user import Permission, Role

log = get_logger("bootstrap")

BADGE_DEFINITIONS: list[tuple[BadgeCode, str, str, str, str]] = [
    (BadgeCode.PROFILE_COMPLETE, "Profile Complete", "Your profile is fully filled in.", "user-check", "Reach 100% profile completion"),
    (BadgeCode.ASSESSMENT_COMPLETED, "Assessment Complete", "You finished your first skill assessment.", "clipboard-check", "Submit one assessment"),
    (BadgeCode.FIRST_CERTIFICATION, "First Certification", "You added your first certification.", "badge-check", "Add one certification"),
    (BadgeCode.FIRST_INTERNSHIP, "First Internship", "You were selected for an internship.", "briefcase", "Be selected for an internship"),
    (BadgeCode.PROJECT_BUILDER, "Project Builder", "You published three or more projects.", "hammer", "Publish 3 projects"),
    (BadgeCode.INDUSTRY_READY, "Industry Ready", "Your readiness score for a target role passed 80%.", "target", "Reach 80% role readiness"),
    (BadgeCode.TOP_SKILL_PERFORMER, "Top Skill Performer", "You scored 90%+ on a skill assessment.", "trending-up", "Score 90%+ in an assessment"),
    (BadgeCode.MENTORSHIP_GRADUATE, "Mentorship Graduate", "You completed three mentorship sessions.", "users", "Complete 3 mentorship sessions"),
]


async def sync_rbac_catalogue() -> None:
    """Create/update permissions, roles and their mapping. Safe to run on every boot."""
    async with AsyncSessionLocal() as db:
        try:
            existing_perms = {
                p.code: p for p in (await db.execute(select(Permission))).scalars()
            }
        except Exception as exc:  # table not migrated yet (first run / CI)
            log.warning("bootstrap.skipped", reason=str(exc)[:160])
            return

        created = 0
        for code, description in PERMISSIONS.items():
            resource, _, action = code.partition(":")
            perm = existing_perms.get(code)
            if perm is None:
                perm = Permission(
                    code=code, resource=resource, action=action, description=description
                )
                db.add(perm)
                existing_perms[code] = perm
                created += 1
            elif perm.description != description:
                perm.description = description
        await db.flush()

        existing_roles = {r.name: r for r in (await db.execute(select(Role))).scalars()}
        for role_name, codes in ROLE_PERMISSIONS.items():
            label, description, signup = ROLE_LABELS[role_name]
            role = existing_roles.get(role_name)
            if role is None:
                role = Role(
                    name=role_name, label=label, description=description,
                    is_assignable_on_signup=signup,
                )
                db.add(role)
                await db.flush()
            else:
                role.label, role.description = label, description
                role.is_assignable_on_signup = signup
            wanted = {existing_perms[c] for c in codes if c in existing_perms}
            # awaitable_attrs loads the collection safely inside async context
            # (a freshly flushed Role has no loaded collection yet).
            current = set(await role.awaitable_attrs.permissions)
            if wanted != current:
                role.permissions = sorted(wanted, key=lambda p: p.code)

        existing_badges = {b.code for b in (await db.execute(select(Badge))).scalars()}
        for code, name, description, icon, criteria in BADGE_DEFINITIONS:
            if code not in existing_badges:
                db.add(
                    Badge(code=code, name=name, description=description,
                          icon=icon, criteria=criteria)
                )

        await db.commit()
        log.info(
            "bootstrap.rbac_synced",
            permissions=len(PERMISSIONS), roles=len(ROLE_PERMISSIONS), new_permissions=created,
        )
