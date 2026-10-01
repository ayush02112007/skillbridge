"""Authentication, session and RBAC behaviour."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import API, STRONG_PASSWORD, auth_header, register


async def test_register_creates_account_with_role_and_profile(client: AsyncClient):
    data = await register(client, "new.student@example.edu", "STUDENT")
    assert data["session"]["roles"] == ["STUDENT"]
    assert data["session"]["home_route"] == "/student/dashboard"
    assert data["session"]["profile_id"], "a student profile must be created on signup"
    assert "student_skill:manage_self" in data["session"]["permissions"]
    assert data["tokens"]["access_token"] and data["tokens"]["refresh_token"]


async def test_password_is_never_returned_or_stored_in_plain_text(
    client: AsyncClient, db
):
    from sqlalchemy import select

    from app.models.user import User

    data = await register(client, "hash.check@example.edu", "STUDENT")
    assert STRONG_PASSWORD not in str(data)
    user = (
        await db.execute(select(User).where(User.email == "hash.check@example.edu"))
    ).scalar_one()
    assert user.hashed_password.startswith("$argon2")
    assert STRONG_PASSWORD not in user.hashed_password


@pytest.mark.parametrize(
    "password,reason",
    [
        ("short1!A", "too short"),
        ("alllowercase123!", "no uppercase"),
        ("ALLUPPERCASE123!", "no lowercase"),
        ("NoDigitsHere!!!", "no digit"),
        ("NoSymbols12345", "no symbol"),
    ],
)
async def test_weak_passwords_rejected(client: AsyncClient, password: str, reason: str):
    response = await client.post(
        f"{API}/auth/register",
        json={
            "email": f"weak.{abs(hash(password))}@example.edu",
            "password": password,
            "full_name": "Weak Password",
            "role": "STUDENT",
            "accept_terms": True,
        },
    )
    assert response.status_code == 422, reason
    assert response.json()["success"] is False


async def test_duplicate_email_conflicts(client: AsyncClient):
    await register(client, "dupe@example.edu", "STUDENT")
    response = await client.post(
        f"{API}/auth/register",
        json={
            "email": "DUPE@example.edu",  # case-insensitive
            "password": STRONG_PASSWORD,
            "full_name": "Duplicate",
            "role": "STUDENT",
            "accept_terms": True,
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_privileged_roles_cannot_self_register(client: AsyncClient):
    response = await client.post(
        f"{API}/auth/register",
        json={
            "email": "wannabe.admin@example.edu",
            "password": STRONG_PASSWORD,
            "full_name": "Wannabe Admin",
            "role": "SUPER_ADMIN",
            "accept_terms": True,
        },
    )
    assert response.status_code == 422  # rejected by the schema's role literal


async def test_terms_must_be_accepted(client: AsyncClient):
    response = await client.post(
        f"{API}/auth/register",
        json={
            "email": "no.terms@example.edu",
            "password": STRONG_PASSWORD,
            "full_name": "No Terms",
            "role": "STUDENT",
            "accept_terms": False,
        },
    )
    assert response.status_code == 422


async def test_login_and_me(client: AsyncClient):
    await register(client, "login.flow@example.edu", "STUDENT")
    response = await client.post(
        f"{API}/auth/login",
        json={"email": "login.flow@example.edu", "password": STRONG_PASSWORD},
    )
    assert response.status_code == 200
    session = response.json()["data"]
    me = await client.get(f"{API}/auth/me", headers=auth_header(session))
    assert me.status_code == 200
    assert me.json()["data"]["user"]["email"] == "login.flow@example.edu"


async def test_login_with_wrong_password_is_generic(client: AsyncClient):
    await register(client, "wrong.pass@example.edu", "STUDENT")
    response = await client.post(
        f"{API}/auth/login",
        json={"email": "wrong.pass@example.edu", "password": "Definitely!Wrong9"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_unknown_email_gives_identical_error(client: AsyncClient):
    """No account enumeration: unknown user and wrong password look the same."""
    response = await client.post(
        f"{API}/auth/login",
        json={"email": "ghost@example.edu", "password": "Definitely!Wrong9"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_protected_route_requires_token(client: AsyncClient):
    response = await client.get(f"{API}/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_tampered_token_rejected(client: AsyncClient, student_auth):
    token = student_auth["data"]["tokens"]["access_token"]
    tampered = token[:-4] + ("abcd" if not token.endswith("abcd") else "efgh")
    response = await client.get(
        f"{API}/auth/me", headers={"Authorization": f"Bearer {tampered}"}
    )
    assert response.status_code == 401


async def test_refresh_rotates_and_detects_reuse(client: AsyncClient):
    data = await register(client, "rotate@example.edu", "STUDENT")
    original = data["tokens"]["refresh_token"]

    first = await client.post(f"{API}/auth/refresh", json={"refresh_token": original})
    assert first.status_code == 200
    rotated = first.json()["data"]["refresh_token"]
    assert rotated != original

    replay = await client.post(f"{API}/auth/refresh", json={"refresh_token": original})
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "REFRESH_TOKEN_REUSED"

    # The whole family is revoked, not just the replayed token.
    after = await client.post(f"{API}/auth/refresh", json={"refresh_token": rotated})
    assert after.status_code == 401


async def test_access_token_is_not_accepted_as_refresh_token(client: AsyncClient):
    data = await register(client, "typeconf@example.edu", "STUDENT")
    response = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": data["tokens"]["access_token"]}
    )
    assert response.status_code == 401


async def test_logout_revokes_session(client: AsyncClient):
    data = await register(client, "logout@example.edu", "STUDENT")
    headers = auth_header(data)
    response = await client.post(
        f"{API}/auth/logout",
        headers=headers,
        json={"refresh_token": data["tokens"]["refresh_token"]},
    )
    assert response.status_code == 200
    replay = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": data["tokens"]["refresh_token"]}
    )
    assert replay.status_code == 401


async def test_change_password_requires_current_and_revokes_sessions(
    client: AsyncClient,
):
    data = await register(client, "changepw@example.edu", "STUDENT")
    headers = auth_header(data)

    bad = await client.post(
        f"{API}/auth/change-password",
        headers=headers,
        json={"current_password": "Not!TheOne9", "new_password": "Brand!NewPass1"},
    )
    assert bad.status_code == 401

    good = await client.post(
        f"{API}/auth/change-password",
        headers=headers,
        json={"current_password": STRONG_PASSWORD, "new_password": "Brand!NewPass1"},
    )
    assert good.status_code == 200

    # Old sessions are gone; the new password works.
    assert (
        await client.post(
            f"{API}/auth/refresh",
            json={"refresh_token": data["tokens"]["refresh_token"]},
        )
    ).status_code == 401
    relogin = await client.post(
        f"{API}/auth/login",
        json={"email": "changepw@example.edu", "password": "Brand!NewPass1"},
    )
    assert relogin.status_code == 200


async def test_forgot_password_does_not_leak_account_existence(client: AsyncClient):
    known = await client.post(
        f"{API}/auth/forgot-password", json={"email": "student.fixture@example.edu"}
    )
    unknown = await client.post(
        f"{API}/auth/forgot-password", json={"email": "nobody.here@example.edu"}
    )
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


async def test_password_reset_end_to_end(client: AsyncClient, db):
    from sqlalchemy import select

    from app.models.user import User
    from app.services import auth as auth_service

    await register(client, "resetme@example.edu", "STUDENT")
    user = (
        await db.execute(select(User).where(User.email == "resetme@example.edu"))
    ).scalar_one()
    raw = await auth_service.issue_one_time_token(db, user, "reset_password")
    await db.commit()

    response = await client.post(
        f"{API}/auth/reset-password",
        json={"token": raw, "new_password": "Reset!Password1"},
    )
    assert response.status_code == 200

    # Token is single use.
    again = await client.post(
        f"{API}/auth/reset-password",
        json={"token": raw, "new_password": "Another!Password1"},
    )
    assert again.status_code == 401

    login = await client.post(
        f"{API}/auth/login",
        json={"email": "resetme@example.edu", "password": "Reset!Password1"},
    )
    assert login.status_code == 200


async def test_email_verification_flow(client: AsyncClient, db):
    from sqlalchemy import select

    from app.models.user import User
    from app.services import auth as auth_service

    await register(client, "verifyme@example.edu", "STUDENT")
    user = (
        await db.execute(select(User).where(User.email == "verifyme@example.edu"))
    ).scalar_one()
    raw = await auth_service.issue_one_time_token(db, user, "verify_email")
    await db.commit()

    response = await client.post(f"{API}/auth/verify-email", json={"token": raw})
    assert response.status_code == 200
    await db.refresh(user)
    assert user.is_email_verified is True


async def test_sessions_listing_and_revocation(client: AsyncClient):
    data = await register(client, "sessions@example.edu", "STUDENT")
    headers = auth_header(data)
    await client.post(
        f"{API}/auth/login",
        json={"email": "sessions@example.edu", "password": STRONG_PASSWORD},
    )
    listing = await client.get(f"{API}/auth/sessions", headers=headers)
    assert listing.status_code == 200
    sessions = listing.json()["data"]
    assert len(sessions) >= 2

    revoke = await client.delete(
        f"{API}/auth/sessions/{sessions[0]['id']}", headers=headers
    )
    assert revoke.status_code == 200


async def test_account_lockout_after_repeated_failures(client: AsyncClient):
    await register(client, "lockout@example.edu", "STUDENT")
    codes = []
    for _ in range(9):
        response = await client.post(
            f"{API}/auth/login",
            json={"email": "lockout@example.edu", "password": "Nope!Nope123"},
        )
        codes.append(response.json()["error"]["code"])
    assert "ACCOUNT_LOCKED" in codes, codes


async def test_update_account_details(client: AsyncClient, student_auth):
    response = await client.patch(
        f"{API}/auth/me",
        headers=student_auth["headers"],
        json={"full_name": "Renamed Student", "timezone_name": "Asia/Kolkata"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["full_name"] == "Renamed Student"


async def test_recruiter_registration_creates_company(client: AsyncClient, db):
    from sqlalchemy import select

    from app.models.organization import Company

    data = await register(
        client, "hiring@acme.com", "INDUSTRY_ADMIN", company_name="Acme Robotics"
    )
    assert data["session"]["home_route"] == "/industry/dashboard"
    company = (
        await db.execute(select(Company).where(Company.name == "Acme Robotics"))
    ).scalar_one()
    assert company.slug == "acme-robotics"


async def test_role_permissions_differ_between_roles(client: AsyncClient):
    student = await register(client, "perm.student@example.edu", "STUDENT")
    recruiter = await register(
        client, "perm.recruiter@example.com", "INDUSTRY_ADMIN", company_name="Perm Corp"
    )
    student_perms = set(student["session"]["permissions"])
    recruiter_perms = set(recruiter["session"]["permissions"])
    assert "application:create" in student_perms
    assert "application:create" not in recruiter_perms
    assert "opportunity:create" in recruiter_perms
    assert "opportunity:create" not in student_perms


async def test_audit_log_records_login(client: AsyncClient, db):
    from sqlalchemy import func, select

    from app.models.audit import AuditLog
    from app.models.enums import AuditAction

    await register(client, "audited@example.edu", "STUDENT")
    await client.post(
        f"{API}/auth/login",
        json={"email": "audited@example.edu", "password": STRONG_PASSWORD},
    )
    count = (
        await db.execute(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == AuditAction.LOGIN)
        )
    ).scalar_one()
    assert count >= 1
