"""Shared pytest fixtures.

The suite runs against a throwaway SQLite database created from the ORM
metadata, with the FastAPI dependency graph pointed at it. No external service
(PostgreSQL, Redis, MinIO, SMTP) is required to run the tests.
"""
from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import AsyncIterator

# Configure the environment before app modules import settings.
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST_DB = ROOT / "var" / "test.db"
os.environ.update(
    ENVIRONMENT="test",
    DEBUG="true",
    DATABASE_URL=f"sqlite+aiosqlite:///{TEST_DB}",
    CACHE_ENABLED="false",
    RATE_LIMIT_ENABLED="false",
    CSRF_ENABLED="false",
    REQUIRE_EMAIL_VERIFICATION="false",
    EMAIL_PROVIDER="console",
    STORAGE_PROVIDER="local",
    STORAGE_LOCAL_PATH=str(ROOT / "var" / "test-uploads"),
    AI_PROVIDER="deterministic",
    LOG_LEVEL="WARNING",
    SEED_DEMO_PASSWORD="DemoPass!2024",
)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.models  # noqa: E402  - must precede `from app.main import app`
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402  (shadows the `app` package by design)

engine = create_async_engine(os.environ["DATABASE_URL"], future=True)
TestSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@pytest.fixture(scope="session", autouse=True)
async def _database() -> AsyncIterator[None]:
    TEST_DB.parent.mkdir(parents=True, exist_ok=True)
    if TEST_DB.exists():
        TEST_DB.unlink()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed the permission/role catalogue exactly as the app does at boot.
    from app.services import bootstrap

    bootstrap.AsyncSessionLocal = TestSessionLocal  # type: ignore[attr-defined]
    await bootstrap.sync_rbac_catalogue()

    # Reference catalogue: skills, categories and job roles.
    from seeds.assessment_seed import seed_assessments
    from seeds.catalog_seed import seed_catalog

    async with TestSessionLocal() as session:
        await seed_catalog(session)
        await seed_assessments(session)
        await session.commit()
    yield
    await engine.dispose()


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async def _get_db() -> AsyncIterator[AsyncSession]:
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ------------------------------------------------------------------ helpers --
API = "/api/v1"
STRONG_PASSWORD = "Str0ng!Passw0rd"


async def register(
    client: AsyncClient, email: str, role: str = "STUDENT", **extra
) -> dict:
    payload = {
        "email": email,
        "password": STRONG_PASSWORD,
        "full_name": extra.pop("full_name", email.split("@")[0].replace(".", " ").title()),
        "role": role,
        "accept_terms": True,
        **extra,
    }
    response = await client.post(f"{API}/auth/register", json=payload)
    if response.status_code == 409:
        # Fixture accounts are shared across tests in a session-scoped database;
        # fall back to signing in so the helper stays idempotent.
        response = await client.post(
            f"{API}/auth/login", json={"email": email, "password": STRONG_PASSWORD}
        )
        assert response.status_code == 200, response.text
        return response.json()["data"]
    assert response.status_code == 201, response.text
    return response.json()["data"]


def auth_header(session: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['tokens']['access_token']}"}


@pytest.fixture
async def student_auth(client: AsyncClient) -> dict:
    data = await register(client, "student.fixture@example.edu", "STUDENT")
    return {"data": data, "headers": auth_header(data)}


@pytest.fixture
async def recruiter_auth(client: AsyncClient) -> dict:
    data = await register(
        client, "recruiter.fixture@example.com", "INDUSTRY_ADMIN",
        company_name="Fixture Technologies",
    )
    return {"data": data, "headers": auth_header(data)}


@pytest.fixture
async def academician_auth(client: AsyncClient) -> dict:
    data = await register(client, "faculty.fixture@example.edu", "ACADEMICIAN")
    return {"data": data, "headers": auth_header(data)}


@pytest.fixture
async def backend_role_id(client: AsyncClient) -> str:
    """The Backend Developer job role, used as a target in several tests."""
    response = await client.get(f"{API}/job-roles", params={"q": "Backend Developer"})
    assert response.status_code == 200
    return response.json()["data"][0]["id"]


async def skill_id_by_name(client: AsyncClient, name: str) -> str:
    response = await client.get(f"{API}/skills", params={"q": name, "page_size": 5})
    assert response.status_code == 200, response.text
    for row in response.json()["data"]:
        if row["name"].lower() == name.lower():
            return row["id"]
    raise AssertionError(f"skill {name!r} not found in the seeded taxonomy")
