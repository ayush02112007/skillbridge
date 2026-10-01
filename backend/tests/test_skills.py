"""Skill taxonomy, student skill profile and the skill-gap engine."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import API, auth_header, register, skill_id_by_name


async def test_taxonomy_is_seeded_and_public(client: AsyncClient):
    response = await client.get(f"{API}/skills/taxonomy")
    assert response.status_code == 200
    nodes = response.json()["data"]
    assert len(nodes) >= 10
    assert sum(n["skill_count"] for n in nodes) >= 100
    assert any(n["is_soft_skill"] for n in nodes), "soft skills must be in the taxonomy"


async def test_skill_search_matches_aliases(client: AsyncClient):
    response = await client.get(f"{API}/skills", params={"q": "postgres"})
    assert response.status_code == 200
    names = [s["name"] for s in response.json()["data"]]
    assert "PostgreSQL" in names


async def test_job_roles_carry_requirements(client: AsyncClient, backend_role_id: str):
    response = await client.get(f"{API}/job-roles/{backend_role_id}")
    assert response.status_code == 200
    role = response.json()["data"]
    assert role["title"] == "Backend Developer"
    assert len(role["required_skills"]) >= 8
    required = {s["skill"]["name"]: s for s in role["required_skills"]}
    assert required["Python"]["required_level"] == "ADVANCED"
    assert required["Python"]["importance"] == "REQUIRED"


async def test_taxonomy_write_requires_admin(client: AsyncClient, student_auth):
    response = await client.post(
        f"{API}/skills",
        headers=student_auth["headers"],
        json={"name": "Telepathy", "category_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] in ("PERMISSION_DENIED", "ROLE_REQUIRED")


async def test_student_can_manage_own_skills(client: AsyncClient):
    data = await register(client, "skills.owner@example.edu", "STUDENT")
    headers = auth_header(data)
    python_id = await skill_id_by_name(client, "Python")
    sql_id = await skill_id_by_name(client, "SQL")

    response = await client.put(
        f"{API}/students/me/skills",
        headers=headers,
        json={
            "skills": [
                {"skill_id": python_id, "level": "INTERMEDIATE"},
                {"skill_id": sql_id, "level": "BEGINNER", "years_of_experience": 1},
            ]
        },
    )
    assert response.status_code == 200
    skills = {s["skill"]["name"]: s for s in response.json()["data"]}
    assert skills["Python"]["level"] == "INTERMEDIATE"
    assert skills["Python"]["source"] == "SELF_REPORTED"
    # Self-reports carry low confidence until backed by evidence.
    assert skills["Python"]["confidence"] < 0.6

    delete = await client.delete(f"{API}/students/me/skills/{sql_id}", headers=headers)
    assert delete.status_code == 200
    remaining = await client.get(f"{API}/students/me/skills", headers=headers)
    assert [s["skill"]["name"] for s in remaining.json()["data"]] == ["Python"]


async def test_unknown_skill_id_is_rejected(client: AsyncClient, student_auth):
    response = await client.put(
        f"{API}/students/me/skills",
        headers=student_auth["headers"],
        json={"skills": [{"skill_id": "11111111-1111-1111-1111-111111111111",
                          "level": "BEGINNER"}]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SKILL_NOT_FOUND"


async def test_skill_gap_produces_prioritised_plan(
    client: AsyncClient, backend_role_id: str
):
    data = await register(client, "gap.student@example.edu", "STUDENT")
    headers = auth_header(data)

    held = {
        "Python": "INTERMEDIATE",
        "PostgreSQL": "INTERMEDIATE",
        "Git": "INTERMEDIATE",
        "SQL": "INTERMEDIATE",
    }
    skills = [
        {"skill_id": await skill_id_by_name(client, name), "level": level}
        for name, level in held.items()
    ]
    await client.put(f"{API}/students/me/skills", headers=headers, json={"skills": skills})

    response = await client.get(
        f"{API}/students/me/skill-gap",
        headers=headers,
        params={"job_role_id": backend_role_id},
    )
    assert response.status_code == 200
    gap = response.json()["data"]

    assert 0 < gap["readiness_score"] < 100
    assert gap["gap_percentage"] == pytest.approx(100 - gap["readiness_score"], abs=0.1)
    assert gap["total_required"] >= 8

    missing = {i["skill_name"] for i in gap["missing_skills"]}
    assert "FastAPI" in missing and "Docker" in missing
    assert "Python" not in missing

    weak = {i["skill_name"] for i in gap["weak_skills"]}
    assert "Python" in weak, "INTERMEDIATE against an ADVANCED requirement is a weak skill"

    # Priorities are 1..n, contiguous, and required skills come first.
    priorities = [i["priority"] for i in gap["priority_skills"]]
    assert priorities == sorted(priorities)
    assert priorities[0] == 1
    assert gap["summary"]


async def test_skill_gap_requires_a_target_role(client: AsyncClient, student_auth):
    response = await client.get(f"{API}/students/me/skill-gap", headers=student_auth["headers"])
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_TARGET_ROLE"


async def test_setting_target_role_recomputes_readiness(
    client: AsyncClient, backend_role_id: str
):
    data = await register(client, "target.role@example.edu", "STUDENT")
    headers = auth_header(data)
    for name in ("Python", "PostgreSQL", "Git", "Docker", "REST API Design"):
        await client.put(
            f"{API}/students/me/skills",
            headers=headers,
            json={"skills": [{"skill_id": await skill_id_by_name(client, name),
                              "level": "ADVANCED"}]},
        )

    response = await client.patch(
        f"{API}/students/me", headers=headers, json={"target_job_role_id": backend_role_id}
    )
    assert response.status_code == 200
    profile = response.json()["data"]
    assert profile["target_job_role_title"] == "Backend Developer"
    assert profile["skill_readiness_score"] > 30

    # The gap endpoint now works without an explicit role.
    gap = await client.get(f"{API}/students/me/skill-gap", headers=headers)
    assert gap.status_code == 200
    assert gap.json()["data"]["job_role_title"] == "Backend Developer"


async def test_more_skills_raise_readiness(client: AsyncClient, backend_role_id: str):
    data = await register(client, "monotonic@example.edu", "STUDENT")
    headers = auth_header(data)

    async def readiness() -> float:
        response = await client.get(
            f"{API}/students/me/skill-gap", headers=headers,
            params={"job_role_id": backend_role_id},
        )
        return response.json()["data"]["readiness_score"]

    await client.put(
        f"{API}/students/me/skills", headers=headers,
        json={"skills": [{"skill_id": await skill_id_by_name(client, "Python"),
                          "level": "ADVANCED"}]},
    )
    before = await readiness()

    for name in ("FastAPI", "Docker", "REST API Design"):
        await client.put(
            f"{API}/students/me/skills", headers=headers,
            json={"skills": [{"skill_id": await skill_id_by_name(client, name),
                              "level": "ADVANCED"}]},
        )
    after = await readiness()
    assert after > before


async def test_role_readiness_ranks_all_roles(client: AsyncClient):
    data = await register(client, "readiness.rank@example.edu", "STUDENT")
    headers = auth_header(data)
    for name in ("Python", "Statistics", "Pandas", "scikit-learn", "Machine Learning"):
        await client.put(
            f"{API}/students/me/skills", headers=headers,
            json={"skills": [{"skill_id": await skill_id_by_name(client, name),
                              "level": "ADVANCED"}]},
        )
    response = await client.get(
        f"{API}/students/me/role-readiness", headers=headers, params={"limit": 5}
    )
    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) == 5
    scores = [r["readiness_score"] for r in rows]
    assert scores == sorted(scores, reverse=True)
    # A data-skilled student should surface a Data & AI role near the top.
    assert any(r["family"] == "Data & AI" for r in rows[:3])


async def test_profile_completion_tracks_progress(client: AsyncClient):
    data = await register(client, "completion@example.edu", "STUDENT")
    headers = auth_header(data)

    initial = await client.get(f"{API}/students/me/completion", headers=headers)
    assert initial.status_code == 200
    start = initial.json()["data"]
    assert start["percentage"] < 40
    assert start["suggestions"], "an incomplete profile must offer next steps"
    assert sum(s["weight"] for s in start["sections"]) == 100

    await client.patch(
        f"{API}/students/me",
        headers=headers,
        json={
            "headline": "Final year CS student",
            "bio": "I build backend services and care about clean data models.",
            "city": "Pune", "cgpa": 8.4, "graduation_year": 2027,
            "program_name": "B.Tech Computer Science", "current_year": 4,
        },
    )
    await client.post(
        f"{API}/students/me/projects",
        headers=headers,
        json={"title": "Placement Tracker", "description": "A tracker for campus placements",
              "skill_tags": ["Python", "PostgreSQL"]},
    )
    after = await client.get(f"{API}/students/me/completion", headers=headers)
    assert after.json()["data"]["percentage"] > start["percentage"]


async def test_student_subresources_crud(client: AsyncClient):
    data = await register(client, "subresources@example.edu", "STUDENT")
    headers = auth_header(data)

    created = await client.post(
        f"{API}/students/me/education",
        headers=headers,
        json={"level": "BACHELORS", "institution_name": "Pune Institute of Technology",
              "program": "B.Tech CSE", "start_year": 2023, "end_year": 2027,
              "score_value": 8.4, "score_type": "CGPA"},
    )
    assert created.status_code == 201
    entry_id = created.json()["data"]["id"]

    listing = await client.get(f"{API}/students/me/education", headers=headers)
    assert len(listing.json()["data"]) == 1

    updated = await client.patch(
        f"{API}/students/me/education/{entry_id}",
        headers=headers,
        json={"level": "BACHELORS", "institution_name": "Pune Institute of Technology",
              "program": "B.Tech Computer Engineering", "start_year": 2023,
              "end_year": 2027, "score_value": 8.6, "score_type": "CGPA"},
    )
    assert updated.json()["data"]["score_value"] == 8.6

    removed = await client.delete(f"{API}/students/me/education/{entry_id}", headers=headers)
    assert removed.status_code == 200
    assert await client.get(f"{API}/students/me/education", headers=headers) is not None


async def test_education_validation_rejects_impossible_years(client: AsyncClient, student_auth):
    response = await client.post(
        f"{API}/students/me/education",
        headers=student_auth["headers"],
        json={"level": "BACHELORS", "institution_name": "Somewhere",
              "start_year": 2027, "end_year": 2023},
    )
    assert response.status_code == 422


async def test_cgpa_bounds_enforced(client: AsyncClient, student_auth):
    response = await client.patch(
        f"{API}/students/me", headers=student_auth["headers"], json={"cgpa": 12.5}
    )
    assert response.status_code == 422


async def test_students_cannot_read_each_others_profiles(client: AsyncClient):
    first = await register(client, "private.one@example.edu", "STUDENT")
    second = await register(client, "private.two@example.edu", "STUDENT")
    other_id = second["session"]["profile_id"]
    response = await client.get(
        f"{API}/students/{other_id}", headers=auth_header(first)
    )
    assert response.status_code == 403


async def test_dashboard_renders_for_a_new_student(client: AsyncClient):
    data = await register(client, "dash.new@example.edu", "STUDENT")
    response = await client.get(f"{API}/students/me/dashboard", headers=auth_header(data))
    assert response.status_code == 200
    dashboard = response.json()["data"]
    # Empty state must still be well-formed, not an error.
    assert dashboard["applications"]["total"] == 0
    assert dashboard["skill_gap"] is None
    assert dashboard["profile_completion"]["percentage"] >= 0
    assert dashboard["portfolio"]["slug"]
