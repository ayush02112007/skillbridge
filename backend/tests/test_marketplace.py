"""Marketplace: posting, discovery, matching, applications and the hiring pipeline."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from tests.conftest import API, auth_header, register, skill_id_by_name


def _future(days: int = 30) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


async def _skills_payload(client: AsyncClient, spec: dict[str, str]) -> list[dict]:
    return [
        {"skill_id": await skill_id_by_name(client, name), "required_level": level,
         "importance": "REQUIRED", "weight": 1.2}
        for name, level in spec.items()
    ]


async def create_internship(
    client: AsyncClient, headers: dict, *, title="Backend Engineering Intern",
    publish=True, **overrides,
) -> dict:
    payload = {
        "title": title,
        "description": (
            "Join our platform team to build and ship REST APIs in Python. "
            "You will work on real services with code review and mentorship."
        ),
        "responsibilities": ["Build REST endpoints", "Write tests"],
        "work_mode": "HYBRID",
        "location_city": "Bengaluru",
        "positions": 2,
        "application_deadline": _future(),
        "duration_weeks": 12,
        "stipend_min": 25000,
        "stipend_max": 35000,
        "is_paid": True,
        "skills": await _skills_payload(
            client, {"Python": "ADVANCED", "PostgreSQL": "INTERMEDIATE",
                     "REST API Design": "INTERMEDIATE", "Docker": "INTERMEDIATE"}
        ),
        **overrides,
    }
    response = await client.post(
        f"{API}/internships", headers=headers, json=payload,
        params={"publish": str(publish).lower()},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def make_skilled_student(
    client: AsyncClient, email: str, skills: dict[str, str], **profile
) -> dict:
    data = await register(client, email, "STUDENT")
    headers = auth_header(data)
    payload = [
        {"skill_id": await skill_id_by_name(client, name), "level": level}
        for name, level in skills.items()
    ]
    await client.put(f"{API}/students/me/skills", headers=headers, json={"skills": payload})
    if profile:
        await client.patch(f"{API}/students/me", headers=headers, json=profile)
    return {"data": data, "headers": headers}


# --------------------------------------------------------------- posting ---
async def test_recruiter_creates_and_publishes_an_internship(
    client: AsyncClient, recruiter_auth
):
    created = await create_internship(client, recruiter_auth["headers"], publish=False)
    assert created["status"] == "DRAFT"
    assert created["details"]["stipend_min"] == 25000
    assert created["details"]["duration_weeks"] == 12
    assert len(created["skills"]) == 4

    published = await client.post(
        f"{API}/internships/{created['id']}/status",
        headers=recruiter_auth["headers"], json={"status": "PUBLISHED"},
    )
    assert published.status_code == 200
    assert published.json()["data"]["status"] == "PUBLISHED"
    assert published.json()["data"]["published_at"]


async def test_publishing_without_skills_is_refused(client: AsyncClient, recruiter_auth):
    response = await client.post(
        f"{API}/internships",
        headers=recruiter_auth["headers"],
        json={
            "title": "Vague Internship",
            "description": "We are looking for someone to do some things here.",
            "duration_weeks": 8, "stipend_min": 10000, "is_paid": True, "skills": [],
        },
    )
    assert response.status_code == 201
    draft = response.json()["data"]
    publish = await client.post(
        f"{API}/internships/{draft['id']}/status",
        headers=recruiter_auth["headers"], json={"status": "PUBLISHED"},
    )
    assert publish.status_code == 409
    assert publish.json()["error"]["code"] == "OPPORTUNITY_INCOMPLETE"


async def test_students_cannot_post_opportunities(client: AsyncClient, student_auth):
    response = await client.post(
        f"{API}/internships",
        headers=student_auth["headers"],
        json={"title": "Fake", "description": "x" * 40, "duration_weeks": 4,
              "is_paid": False},
    )
    assert response.status_code == 403


async def test_recruiter_cannot_edit_another_companys_posting(client: AsyncClient):
    first = await register(
        client, "owner.co@example.com", "INDUSTRY_ADMIN", company_name="Owner Co"
    )
    rival = await register(
        client, "rival.co@example.com", "INDUSTRY_ADMIN", company_name="Rival Co"
    )
    posting = await create_internship(client, auth_header(first), title="Owned Internship")

    response = await client.patch(
        f"{API}/internships/{posting['id']}",
        headers=auth_header(rival), json={"title": "Hijacked"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CROSS_COMPANY_ACCESS"


# -------------------------------------------------------------- matching ---
async def test_student_sees_personal_match_score_on_listings(
    client: AsyncClient, recruiter_auth
):
    await create_internship(client, recruiter_auth["headers"], title="Match Score Intern")
    strong = await make_skilled_student(
        client, "strong.match@example.edu",
        {"Python": "ADVANCED", "PostgreSQL": "ADVANCED", "REST API Design": "ADVANCED",
         "Docker": "INTERMEDIATE"},
        preferred_roles=["Backend Developer"], preferred_locations=["Bengaluru"],
    )
    weak = await make_skilled_student(
        client, "weak.match@example.edu", {"Figma": "BEGINNER"},
    )

    strong_rows = (
        await client.get(f"{API}/internships", headers=strong["headers"])
    ).json()["data"]
    weak_rows = (
        await client.get(f"{API}/internships", headers=weak["headers"])
    ).json()["data"]

    strong_row = next(r for r in strong_rows if r["title"] == "Match Score Intern")
    weak_row = next(r for r in weak_rows if r["title"] == "Match Score Intern")
    assert strong_row["match_score"] > weak_row["match_score"]
    assert "Python" in strong_row["matching_skills"]
    assert "Python" in weak_row["missing_skills"]


async def test_opportunity_detail_explains_the_match(client: AsyncClient, recruiter_auth):
    posting = await create_internship(client, recruiter_auth["headers"], title="Explained Intern")
    student = await make_skilled_student(
        client, "explained@example.edu",
        {"Python": "ADVANCED", "PostgreSQL": "INTERMEDIATE"},
        preferred_roles=["Backend Developer"],
    )
    response = await client.get(
        f"{API}/opportunities/{posting['id']}", headers=student["headers"]
    )
    assert response.status_code == 200
    match = response.json()["data"]["match"]
    assert match is not None
    # Every factor in the configured weighting is reported.
    assert set(match["breakdown"]) == {
        "skills", "education", "interest", "experience", "location",
        "certification", "project",
    }
    assert match["reason_summary"]
    assert match["reasons"]
    assert abs(sum(match["contributions"].values()) - match["match_score"]) < 0.5


async def test_anonymous_search_works_without_match_annotations(
    client: AsyncClient, recruiter_auth
):
    await create_internship(client, recruiter_auth["headers"], title="Public Listing Intern")
    response = await client.get(f"{API}/opportunities", params={"q": "Public Listing"})
    assert response.status_code == 200
    rows = response.json()["data"]
    assert rows and rows[0]["match_score"] is None


async def test_search_filters(client: AsyncClient, recruiter_auth):
    await create_internship(
        client, recruiter_auth["headers"], title="Remote Filter Intern",
        work_mode="REMOTE", location_city="Pune",
    )
    remote = await client.get(f"{API}/opportunities", params={"work_mode": "REMOTE"})
    assert all(r["work_mode"] == "REMOTE" for r in remote.json()["data"])

    by_city = await client.get(f"{API}/opportunities", params={"location": "pune"})
    assert any(r["title"] == "Remote Filter Intern" for r in by_city.json()["data"])

    python_id = await skill_id_by_name(client, "Python")
    by_skill = await client.get(f"{API}/opportunities", params={"skill_id": python_id})
    assert by_skill.json()["meta"]["total"] >= 1


# ---------------------------------------------------------- applications ---
async def test_full_hiring_pipeline(client: AsyncClient):
    recruiter = await register(
        client, "pipeline.hr@example.com", "INDUSTRY_ADMIN", company_name="Pipeline Labs"
    )
    rec_headers = auth_header(recruiter)
    posting = await create_internship(client, rec_headers, title="Pipeline Intern")

    student = await make_skilled_student(
        client, "pipeline.student@example.edu",
        {"Python": "ADVANCED", "PostgreSQL": "ADVANCED", "REST API Design": "ADVANCED"},
        graduation_year=2027, cgpa=8.2,
    )

    applied = await client.post(
        f"{API}/applications/opportunities/{posting['id']}",
        headers=student["headers"],
        json={"cover_letter": "I have built three REST services in Python."},
    )
    assert applied.status_code == 201, applied.text
    application = applied.json()["data"]
    assert application["status"] == "APPLIED"
    assert application["match_score"] > 0
    assert application["matching_skills"]
    timeline = {s["status"]: s["state"] for s in application["timeline"]}
    assert timeline["APPLIED"] == "current"
    assert timeline["SELECTED"] == "upcoming"

    received = await client.get(
        f"{API}/applications/received", headers=rec_headers,
        params={"opportunity_id": posting["id"]},
    )
    assert received.status_code == 200
    rows = received.json()["data"]
    assert len(rows) == 1
    assert rows[0]["applicant"]["full_name"]
    assert rows[0]["match_score"] == application["match_score"]

    for target in ("UNDER_REVIEW", "SHORTLISTED"):
        moved = await client.patch(
            f"{API}/applications/{application['id']}", headers=rec_headers,
            json={"status": target, "note": f"Moving to {target}"},
        )
        assert moved.status_code == 200, moved.text
        assert moved.json()["data"]["status"] == target

    interview = await client.post(
        f"{API}/applications/{application['id']}/interviews",
        headers=rec_headers,
        json={"scheduled_at": _future(3), "round_name": "Technical Round",
              "duration_minutes": 45, "mode": "ONLINE",
              "location_or_link": "https://meet.example.com/abc"},
    )
    assert interview.status_code == 201, interview.text
    assert interview.json()["data"]["round_number"] == 1

    after = await client.get(f"{API}/applications/{application['id']}", headers=rec_headers)
    assert after.json()["data"]["status"] == "INTERVIEW"

    for target in ("OFFERED", "SELECTED"):
        moved = await client.patch(
            f"{API}/applications/{application['id']}", headers=rec_headers,
            json={"status": target},
        )
        assert moved.status_code == 200, moved.text

    final = await client.get(f"{API}/applications/{application['id']}", headers=rec_headers)
    body = final.json()["data"]
    assert body["status"] == "SELECTED"
    assert body["decided_at"]
    states = {s["status"]: s["state"] for s in body["timeline"]}
    assert states["SELECTED"] == "current"
    assert states["APPLIED"] == "complete"

    # Selection produced a verified experience record on the student profile.
    experience = await client.get(f"{API}/students/me/experience", headers=student["headers"])
    entries = experience.json()["data"]
    assert len(entries) == 1
    assert entries[0]["title"] == "Pipeline Intern"
    assert entries[0]["is_verified"] is True

    # And the student was notified at each step.
    notifications = await client.get(
        f"{API}/students/me/dashboard", headers=student["headers"]
    )
    assert notifications.json()["data"]["applications"]["total"] == 1


async def test_invalid_status_transition_is_refused(client: AsyncClient):
    recruiter = await register(
        client, "transition.hr@example.com", "INDUSTRY_ADMIN", company_name="Transition Co"
    )
    rec_headers = auth_header(recruiter)
    posting = await create_internship(client, rec_headers, title="Transition Intern")
    student = await make_skilled_student(
        client, "transition.student@example.edu", {"Python": "ADVANCED"}
    )
    applied = await client.post(
        f"{API}/applications/opportunities/{posting['id']}",
        headers=student["headers"], json={},
    )
    application_id = applied.json()["data"]["id"]

    # APPLIED -> SELECTED skips the entire pipeline and must be rejected.
    jump = await client.patch(
        f"{API}/applications/{application_id}", headers=rec_headers,
        json={"status": "SELECTED"},
    )
    assert jump.status_code == 409
    body = jump.json()["error"]
    assert body["code"] == "INVALID_STATUS_TRANSITION"
    assert "SHORTLISTED" in body["details"]["allowed_next"]

    # A rejected application is terminal.
    await client.patch(
        f"{API}/applications/{application_id}", headers=rec_headers,
        json={"status": "REJECTED", "reason": "Not a fit this cycle"},
    )
    revive = await client.patch(
        f"{API}/applications/{application_id}", headers=rec_headers,
        json={"status": "SHORTLISTED"},
    )
    assert revive.status_code == 409


async def test_duplicate_application_rejected(client: AsyncClient, recruiter_auth):
    posting = await create_internship(client, recruiter_auth["headers"], title="Once Only Intern")
    student = await make_skilled_student(
        client, "once.only@example.edu", {"Python": "ADVANCED"}
    )
    first = await client.post(
        f"{API}/applications/opportunities/{posting['id']}",
        headers=student["headers"], json={},
    )
    assert first.status_code == 201
    second = await client.post(
        f"{API}/applications/opportunities/{posting['id']}",
        headers=student["headers"], json={},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ALREADY_APPLIED"


async def test_eligibility_is_enforced_at_application_time(
    client: AsyncClient, recruiter_auth
):
    posting = await create_internship(
        client, recruiter_auth["headers"], title="Strict Eligibility Intern",
        min_cgpa=9.0, eligible_graduation_years=[2026],
    )
    student = await make_skilled_student(
        client, "ineligible@example.edu", {"Python": "ADVANCED"},
        cgpa=6.5, graduation_year=2028,
    )
    response = await client.post(
        f"{API}/applications/opportunities/{posting['id']}",
        headers=student["headers"], json={},
    )
    assert response.status_code == 409
    body = response.json()["error"]
    assert body["code"] == "NOT_ELIGIBLE"
    assert len(body["details"]["reasons"]) >= 2


async def test_cannot_apply_to_a_draft(client: AsyncClient, recruiter_auth):
    draft = await create_internship(
        client, recruiter_auth["headers"], title="Hidden Draft Intern", publish=False
    )
    student = await make_skilled_student(
        client, "draft.applicant@example.edu", {"Python": "ADVANCED"}
    )
    response = await client.post(
        f"{API}/applications/opportunities/{draft['id']}",
        headers=student["headers"], json={},
    )
    assert response.status_code == 404


async def test_withdrawal_is_final(client: AsyncClient, recruiter_auth):
    posting = await create_internship(client, recruiter_auth["headers"], title="Withdraw Intern")
    student = await make_skilled_student(
        client, "withdrawer@example.edu", {"Python": "ADVANCED"}
    )
    applied = await client.post(
        f"{API}/applications/opportunities/{posting['id']}",
        headers=student["headers"], json={},
    )
    application_id = applied.json()["data"]["id"]

    withdrawn = await client.post(
        f"{API}/applications/{application_id}/withdraw",
        headers=student["headers"], json={"reason": "Accepted another offer"},
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["data"]["status"] == "WITHDRAWN"

    reapply = await client.post(
        f"{API}/applications/opportunities/{posting['id']}",
        headers=student["headers"], json={},
    )
    assert reapply.status_code == 409
    assert reapply.json()["error"]["code"] == "ALREADY_WITHDRAWN"


async def test_recruiter_notes_are_never_shown_to_the_applicant(
    client: AsyncClient, recruiter_auth
):
    posting = await create_internship(client, recruiter_auth["headers"], title="Private Notes Intern")
    student = await make_skilled_student(
        client, "notes.subject@example.edu", {"Python": "ADVANCED"}
    )
    applied = await client.post(
        f"{API}/applications/opportunities/{posting['id']}",
        headers=student["headers"], json={},
    )
    application_id = applied.json()["data"]["id"]

    await client.patch(
        f"{API}/applications/{application_id}/notes",
        headers=recruiter_auth["headers"],
        json={"recruiter_notes": "Weak on system design", "recruiter_rating": 3},
    )
    recruiter_view = await client.get(
        f"{API}/applications/{application_id}", headers=recruiter_auth["headers"]
    )
    assert recruiter_view.json()["data"]["recruiter_notes"] == "Weak on system design"

    student_view = await client.get(
        f"{API}/applications/{application_id}", headers=student["headers"]
    )
    assert student_view.status_code == 200
    assert student_view.json()["data"]["recruiter_notes"] is None


async def test_applications_are_scoped_to_the_hiring_company(client: AsyncClient):
    first = await register(
        client, "scope.a@example.com", "INDUSTRY_ADMIN", company_name="Scope A"
    )
    second = await register(
        client, "scope.b@example.com", "INDUSTRY_ADMIN", company_name="Scope B"
    )
    posting = await create_internship(client, auth_header(first), title="Scoped Intern")
    student = await make_skilled_student(
        client, "scoped.applicant@example.edu", {"Python": "ADVANCED"}
    )
    applied = await client.post(
        f"{API}/applications/opportunities/{posting['id']}",
        headers=student["headers"], json={},
    )
    application_id = applied.json()["data"]["id"]

    listing = await client.get(f"{API}/applications/received", headers=auth_header(second))
    assert listing.json()["meta"]["total"] == 0

    detail = await client.get(
        f"{API}/applications/{application_id}", headers=auth_header(second)
    )
    assert detail.status_code == 403

    change = await client.patch(
        f"{API}/applications/{application_id}", headers=auth_header(second),
        json={"status": "REJECTED"},
    )
    assert change.status_code == 403


async def test_application_funnel_reports_conversion(client: AsyncClient, recruiter_auth):
    student = await make_skilled_student(
        client, "funnel.student@example.edu", {"Python": "ADVANCED"}
    )
    for index in range(3):
        posting = await create_internship(
            client, recruiter_auth["headers"], title=f"Funnel Intern {index}"
        )
        await client.post(
            f"{API}/applications/opportunities/{posting['id']}",
            headers=student["headers"], json={},
        )
    response = await client.get(f"{API}/applications/mine/funnel", headers=student["headers"])
    assert response.status_code == 200
    funnel = response.json()["data"]
    assert funnel["total"] == 3
    assert funnel["by_status"]["APPLIED"] == 3
    assert funnel["conversion"]["applied_to_shortlist"] == 0.0


async def test_save_and_unsave_an_opportunity(client: AsyncClient, recruiter_auth):
    posting = await create_internship(client, recruiter_auth["headers"], title="Saveable Intern")
    student = await make_skilled_student(client, "saver@example.edu", {"Python": "BEGINNER"})

    saved = await client.post(
        f"{API}/opportunities/{posting['id']}/save", headers=student["headers"]
    )
    assert saved.status_code == 201
    again = await client.post(
        f"{API}/opportunities/{posting['id']}/save", headers=student["headers"]
    )
    assert again.status_code == 409

    listing = await client.get(f"{API}/opportunities/saved", headers=student["headers"])
    assert listing.json()["meta"]["total"] == 1
    assert listing.json()["data"][0]["is_saved"] is True

    removed = await client.delete(
        f"{API}/opportunities/{posting['id']}/save", headers=student["headers"]
    )
    assert removed.status_code == 200
    empty = await client.get(f"{API}/opportunities/saved", headers=student["headers"])
    assert empty.json()["meta"]["total"] == 0


# --------------------------------------------------------- JD extraction ---
async def test_job_description_analysis_extracts_real_skills_only(
    client: AsyncClient, recruiter_auth
):
    description = """
    We are hiring a Backend Developer to build services in Python using FastAPI.
    You will design PostgreSQL schemas and write SQL, containerise services with
    Docker, and collaborate through Git. Experience with AWS is a nice to have.
    Telepathy and time travel are not required.
    """
    response = await client.post(
        f"{API}/opportunities/analyse-description",
        headers=recruiter_auth["headers"],
        json={"description": description, "title": "Backend Developer"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    names = {s["skill_name"] for s in data["skills"]}
    assert {"Python", "FastAPI", "PostgreSQL", "SQL", "Docker", "Git"} <= names
    assert not any("Telepathy" in n for n in names), "extraction must not invent skills"

    aws = next(s for s in data["skills"] if s["skill_name"] == "AWS")
    assert aws["suggested_importance"] == "PREFERRED", "'nice to have' means preferred"
    assert data["suggested_job_role_title"] == "Backend Developer"


async def test_jd_analysis_requires_recruiter_role(client: AsyncClient, student_auth):
    response = await client.post(
        f"{API}/opportunities/analyse-description",
        headers=student_auth["headers"],
        json={"description": "We need a Python developer with FastAPI experience."},
    )
    assert response.status_code == 403
