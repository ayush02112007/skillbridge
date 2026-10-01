"""Recommendation engine: ranking correctness and the explainability contract."""
from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import API, auth_header, register, skill_id_by_name
from tests.test_marketplace import create_internship, make_skilled_student


async def test_recommendations_are_ranked_by_fit(client: AsyncClient):
    recruiter = await register(
        client, "rec.engine@example.com", "INDUSTRY_ADMIN", company_name="Rec Engine Co"
    )
    headers = auth_header(recruiter)
    await create_internship(client, headers, title="Rec Backend Intern")
    await client.post(
        f"{API}/internships",
        headers=headers,
        params={"publish": "true"},
        json={
            "title": "Rec Design Intern",
            "description": "Design interfaces and run user research for our product team.",
            "duration_weeks": 8, "stipend_min": 20000, "is_paid": True,
            "skills": [
                {"skill_id": await skill_id_by_name(client, "Figma"),
                 "required_level": "ADVANCED", "importance": "REQUIRED", "weight": 1.4},
                {"skill_id": await skill_id_by_name(client, "UX Research"),
                 "required_level": "INTERMEDIATE", "importance": "REQUIRED", "weight": 1.2},
            ],
        },
    )

    backend_student = await make_skilled_student(
        client, "rec.backend@example.edu",
        {"Python": "ADVANCED", "PostgreSQL": "ADVANCED", "REST API Design": "ADVANCED",
         "Docker": "INTERMEDIATE"},
    )
    response = await client.get(
        f"{API}/recommendations/internships", headers=backend_student["headers"]
    )
    assert response.status_code == 200
    rows = response.json()["data"]
    assert rows, "a skilled student must receive recommendations"

    # The property under test is relative ranking for this student, not a
    # global position (the suite shares a database with other postings).
    by_title = {r["target_title"]: r for r in rows}
    backend = by_title.get("Rec Backend Intern")
    assert backend is not None, "a strong match must be recommended"
    design = by_title.get("Rec Design Intern")
    if design is not None:
        assert backend["match_score"] > design["match_score"]

    scores = [r["match_score"] for r in rows]
    assert scores == sorted(scores, reverse=True), "results must be ranked"
    assert "Python" in backend["matching_skills"]


async def test_every_recommendation_is_explainable(client: AsyncClient, recruiter_auth):
    await create_internship(client, recruiter_auth["headers"], title="Explain Contract Intern")
    student = await make_skilled_student(
        client, "explain.contract@example.edu",
        {"Python": "ADVANCED", "PostgreSQL": "INTERMEDIATE"},
        preferred_roles=["Backend Developer"],
    )
    response = await client.get(
        f"{API}/recommendations/internships", headers=student["headers"]
    )
    rows = response.json()["data"]
    assert rows
    for row in rows:
        # This is the contract the product promises: no black-box scores.
        assert 0 <= row["match_score"] <= 100
        assert isinstance(row["matching_skills"], list)
        assert isinstance(row["missing_skills"], list)
        assert row["reasons"], "a recommendation without reasons is a black box"
        assert row["reason_summary"]
        assert row["breakdown"], "factor contributions must be disclosed"
        assert row["generated_by"] == "deterministic"


async def test_already_applied_opportunities_are_not_recommended(
    client: AsyncClient, recruiter_auth
):
    posting = await create_internship(
        client, recruiter_auth["headers"], title="Applied Already Intern"
    )
    student = await make_skilled_student(
        client, "applied.already@example.edu",
        {"Python": "ADVANCED", "PostgreSQL": "ADVANCED", "REST API Design": "ADVANCED"},
    )
    before = await client.get(
        f"{API}/recommendations/internships", headers=student["headers"]
    )
    assert any(
        r["target_id"] == posting["id"] for r in before.json()["data"]
    ), "should be recommended before applying"

    await client.post(
        f"{API}/applications/opportunities/{posting['id']}",
        headers=student["headers"], json={},
    )
    after = await client.get(
        f"{API}/recommendations/internships", headers=student["headers"]
    )
    assert not any(r["target_id"] == posting["id"] for r in after.json()["data"])


async def test_ineligible_opportunities_are_not_recommended(
    client: AsyncClient, recruiter_auth
):
    await create_internship(
        client, recruiter_auth["headers"], title="Impossible Eligibility Intern",
        min_cgpa=9.8, eligible_graduation_years=[2020],
    )
    student = await make_skilled_student(
        client, "never.eligible@example.edu",
        {"Python": "ADVANCED", "PostgreSQL": "ADVANCED"},
        cgpa=6.0, graduation_year=2028,
    )
    response = await client.get(
        f"{API}/recommendations/internships", headers=student["headers"]
    )
    titles = [r["target_title"] for r in response.json()["data"]]
    assert "Impossible Eligibility Intern" not in titles


async def test_career_recommendations_reflect_the_skill_profile(client: AsyncClient):
    student = await make_skilled_student(
        client, "career.rec@example.edu",
        {"Python": "ADVANCED", "Statistics": "ADVANCED", "Pandas": "ADVANCED",
         "scikit-learn": "ADVANCED", "Machine Learning": "ADVANCED", "SQL": "ADVANCED"},
    )
    response = await client.get(f"{API}/recommendations/careers", headers=student["headers"])
    assert response.status_code == 200
    rows = response.json()["data"]
    assert rows
    assert any(r["family"] == "Data & AI" for r in rows[:3])
    top = rows[0]
    assert top["readiness_score"] > 0
    assert top["reason_summary"]
    assert top["next_steps"] is not None


async def test_skill_recommendations_use_live_demand(client: AsyncClient, recruiter_auth):
    await create_internship(client, recruiter_auth["headers"], title="Demand Signal Intern")
    student = await make_skilled_student(
        client, "skill.rec@example.edu", {"Python": "ADVANCED"}
    )
    response = await client.get(f"{API}/recommendations/skills", headers=student["headers"])
    assert response.status_code == 200
    rows = response.json()["data"]
    assert rows
    assert all(r["reasons"] for r in rows)
    # Skills required by live postings must surface with a posting count.
    assert any(r["open_postings"] > 0 for r in rows)


async def test_learning_path_is_ordered_and_explained(
    client: AsyncClient, backend_role_id: str
):
    student = await make_skilled_student(
        client, "path.student@example.edu", {"Python": "INTERMEDIATE"},
        target_job_role_id=backend_role_id,
    )
    response = await client.get(
        f"{API}/recommendations/learning-path", headers=student["headers"]
    )
    assert response.status_code == 200
    plan = response.json()["data"]
    assert plan["job_role_title"] == "Backend Developer"
    assert plan["steps"], "a student with gaps must get steps"
    assert plan["total_hours"] > 0
    assert plan["estimated_weeks"] > 0

    orders = [s["order"] for s in plan["steps"]]
    assert orders == list(range(1, len(orders) + 1))
    for step in plan["steps"]:
        assert step["why"], "every step must justify itself"
        assert step["estimated_hours"] > 0
        assert step["current_level"] != step["target_level"]


async def test_learning_path_respects_prerequisites(client: AsyncClient):
    """FastAPI must never be scheduled before Python."""
    roles = await client.get(f"{API}/job-roles", params={"q": "Backend Developer"})
    role_id = roles.json()["data"][0]["id"]
    student = await make_skilled_student(
        client, "prereq.student@example.edu", {}, target_job_role_id=role_id
    )
    response = await client.get(
        f"{API}/recommendations/learning-path", headers=student["headers"]
    )
    steps = {s["skill_name"]: s["order"] for s in response.json()["data"]["steps"]}
    if "Python" in steps and "FastAPI" in steps:
        assert steps["Python"] < steps["FastAPI"]


async def test_learning_path_requires_a_target(client: AsyncClient, student_auth):
    response = await client.get(
        f"{API}/recommendations/learning-path", headers=student_auth["headers"]
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_TARGET_ROLE"


async def test_career_guidance_falls_back_to_deterministic_text(
    client: AsyncClient, backend_role_id: str
):
    student = await make_skilled_student(
        client, "guidance@example.edu", {"Python": "ADVANCED", "SQL": "INTERMEDIATE"},
        target_job_role_id=backend_role_id,
    )
    response = await client.get(
        f"{API}/recommendations/career-guidance", headers=student["headers"]
    )
    assert response.status_code == 200
    body = response.json()["data"]
    # No LLM key configured in tests: the platform must still produce guidance.
    assert body["generated_by"] == "deterministic"
    assert len(body["guidance"]) > 50
    assert "Python" in body["top_skills"]


async def test_interview_prep_uses_the_students_skills(
    client: AsyncClient, backend_role_id: str
):
    student = await make_skilled_student(
        client, "interview.prep@example.edu",
        {"Python": "ADVANCED", "PostgreSQL": "ADVANCED"},
        target_job_role_id=backend_role_id,
    )
    response = await client.get(
        f"{API}/recommendations/interview-prep", headers=student["headers"],
        params={"count": 6},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["role_title"] == "Backend Developer"
    assert len(body["questions"]) == 6
    assert any("Python" in q["question"] for q in body["questions"])


async def test_recommendation_feedback_dismisses(client: AsyncClient, recruiter_auth, db):
    from sqlalchemy import select

    from app.models.recommendation import Recommendation

    await create_internship(client, recruiter_auth["headers"], title="Feedback Intern")
    student = await make_skilled_student(
        client, "feedback.student@example.edu",
        {"Python": "ADVANCED", "PostgreSQL": "ADVANCED"},
    )
    listing = await client.get(
        f"{API}/recommendations/internships", headers=student["headers"]
    )
    assert listing.json()["data"]

    record = (
        await db.execute(
            select(Recommendation).where(
                Recommendation.user_id
                == uuid_of(student["data"]["session"]["user"]["id"])
            )
        )
    ).scalars().first()
    assert record is not None

    response = await client.post(
        f"{API}/recommendations/{record.id}/feedback",
        headers=student["headers"],
        json={"signal": "DISMISSED", "comment": "Not relevant to me"},
    )
    assert response.status_code == 201
    await db.refresh(record)
    assert record.is_dismissed is True


def uuid_of(value: str):
    import uuid

    return uuid.UUID(value)


async def test_ai_never_blocks_an_application(client: AsyncClient, recruiter_auth):
    """A poor match must still be free to apply - scores advise, they do not gate."""
    posting = await create_internship(
        client, recruiter_auth["headers"], title="Low Match Open Intern"
    )
    student = await make_skilled_student(
        client, "low.match@example.edu", {"Figma": "BEGINNER"}
    )
    detail = await client.get(
        f"{API}/opportunities/{posting['id']}", headers=student["headers"]
    )
    assert detail.json()["data"]["match"]["match_score"] < 50

    applied = await client.post(
        f"{API}/applications/opportunities/{posting['id']}",
        headers=student["headers"], json={},
    )
    assert applied.status_code == 201, "a low score must never prevent applying"
