"""Assessment engine: attempts, scoring integrity and skill-profile feedback."""
from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import API, auth_header, register


async def _correct_options(db, question_id) -> list[str]:
    """Look up the correct option ids for a question (test-only helper)."""
    from app.models.assessment import AssessmentOption

    rows = (
        await db.execute(
            select(AssessmentOption).where(
                AssessmentOption.question_id == uuid.UUID(str(question_id)),
                AssessmentOption.is_correct.is_(True),
            )
        )
    ).scalars().all()
    return [str(o.id) for o in rows]


async def _start(client: AsyncClient, headers: dict, title: str) -> dict:
    listing = await client.get(f"{API}/assessments", headers=headers, params={"q": title})
    assert listing.status_code == 200, listing.text
    assessment_id = listing.json()["data"][0]["id"]
    started = await client.post(f"{API}/assessments/{assessment_id}/attempts", headers=headers)
    assert started.status_code == 201, started.text
    return started.json()["data"]


async def test_assessment_catalogue_is_seeded(client: AsyncClient, student_auth):
    response = await client.get(
        f"{API}/assessments", headers=student_auth["headers"], params={"page_size": 50}
    )
    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) >= 8
    types = {r["assessment_type"] for r in rows}
    # The spec calls for several assessment styles, not just MCQ.
    assert {"TECHNICAL", "APTITUDE", "SELF_ASSESSMENT", "SCENARIO"} <= types
    assert all(r["question_count"] > 0 for r in rows)


async def test_correct_answers_are_never_sent_to_the_candidate(
    client: AsyncClient, student_auth
):
    attempt = await _start(client, student_auth["headers"], "Python Fundamentals")
    for question in attempt["questions"]:
        for option in question["options"]:
            assert "is_correct" not in option
            assert "proficiency_value" not in option
    assert "explanation" not in attempt["questions"][0]


async def test_answer_positions_are_not_biased(db):
    """Guards a real regression: the bank is authored correct-answer-first."""
    from collections import Counter

    from app.models.assessment import AssessmentOption, AssessmentQuestion
    from app.models.enums import QuestionType

    rows = (
        await db.execute(
            select(AssessmentOption.display_order)
            .join(AssessmentQuestion, AssessmentQuestion.id == AssessmentOption.question_id)
            .where(
                AssessmentOption.is_correct.is_(True),
                AssessmentQuestion.question_type != QuestionType.LIKERT,
            )
        )
    ).scalars().all()
    counts = Counter(rows)
    total = sum(counts.values())
    assert total > 30
    # No single position may hold more than half the correct answers.
    assert max(counts.values()) / total < 0.5, counts


async def test_scoring_is_weighted_by_difficulty(client: AsyncClient, db):
    data = await register(client, "scoring.all@example.edu", "STUDENT")
    headers = auth_header(data)
    attempt = await _start(client, headers, "Python Fundamentals")

    answers = []
    for question in attempt["questions"]:
        answers.append(
            {
                "question_id": question["id"],
                "selected_option_ids": await _correct_options(db, question["id"]),
                "time_spent_seconds": 30,
            }
        )
    response = await client.post(
        f"{API}/assessments/attempts/{attempt['attempt_id']}/submit",
        headers=headers, json={"answers": answers},
    )
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["percentage"] == 100.0
    assert result["is_passed"] is True
    # Max score exceeds the question count because hard questions weigh more.
    assert result["max_score"] > len(attempt["questions"])


async def test_all_wrong_scores_zero(client: AsyncClient, db):
    data = await register(client, "scoring.zero@example.edu", "STUDENT")
    headers = auth_header(data)
    attempt = await _start(client, headers, "SQL & Relational Databases")

    answers = []
    for question in attempt["questions"]:
        correct = set(await _correct_options(db, question["id"]))
        wrong = [o["id"] for o in question["options"] if o["id"] not in correct]
        answers.append({"question_id": question["id"], "selected_option_ids": wrong[:1]})
    response = await client.post(
        f"{API}/assessments/attempts/{attempt['attempt_id']}/submit",
        headers=headers, json={"answers": answers},
    )
    result = response.json()["data"]
    assert result["raw_score"] == 0.0
    assert result["percentage"] == 0.0
    assert result["is_passed"] is False


async def test_unanswered_questions_still_count_against_the_total(
    client: AsyncClient, db
):
    data = await register(client, "scoring.partial@example.edu", "STUDENT")
    headers = auth_header(data)
    attempt = await _start(client, headers, "Cybersecurity Essentials")

    first = attempt["questions"][0]
    answers = [
        {
            "question_id": first["id"],
            "selected_option_ids": await _correct_options(db, first["id"]),
        }
    ]
    response = await client.post(
        f"{API}/assessments/attempts/{attempt['attempt_id']}/submit",
        headers=headers, json={"answers": answers},
    )
    result = response.json()["data"]
    assert 0 < result["percentage"] < 100
    # Skipping is not rewarded: the maximum covers every served question.
    assert result["max_score"] > result["raw_score"]


async def test_results_feed_the_skill_profile_with_high_confidence(
    client: AsyncClient, db
):
    data = await register(client, "feedback.loop@example.edu", "STUDENT")
    headers = auth_header(data)
    attempt = await _start(client, headers, "Python Fundamentals")
    answers = [
        {
            "question_id": q["id"],
            "selected_option_ids": await _correct_options(db, q["id"]),
        }
        for q in attempt["questions"]
    ]
    submitted = await client.post(
        f"{API}/assessments/attempts/{attempt['attempt_id']}/submit",
        headers=headers, json={"answers": answers},
    )
    result = submitted.json()["data"]
    assert result["skill_scores"], "an attempt must produce a per-skill breakdown"
    python_score = next(s for s in result["skill_scores"] if s["skill_name"] == "Python")
    assert python_score["level"] == "EXPERT"

    profile = await client.get(f"{API}/students/me/skills", headers=headers)
    skills = {s["skill"]["name"]: s for s in profile.json()["data"]}
    assert skills["Python"]["source"] == "ASSESSMENT"
    assert skills["Python"]["level"] == "EXPERT"
    # Tested evidence carries far more confidence than a self-report.
    assert skills["Python"]["confidence"] >= 0.9
    assert skills["Python"]["last_assessed_at"] is not None
    assert skills["Python"]["evidence"]["assessment_title"] == "Python Fundamentals"


async def test_assessment_overrides_a_self_reported_level(client: AsyncClient, db):
    from tests.conftest import skill_id_by_name

    data = await register(client, "override.claim@example.edu", "STUDENT")
    headers = auth_header(data)
    python_id = await skill_id_by_name(client, "Python")

    # Student claims EXPERT without evidence.
    await client.put(
        f"{API}/students/me/skills", headers=headers,
        json={"skills": [{"skill_id": python_id, "level": "EXPERT"}]},
    )
    claimed = await client.get(f"{API}/students/me/skills", headers=headers)
    assert claimed.json()["data"][0]["level"] == "EXPERT"
    assert claimed.json()["data"][0]["source"] == "SELF_REPORTED"

    # The assessment measures otherwise, and measurement wins.
    attempt = await _start(client, headers, "Python Fundamentals")
    answers = []
    for index, question in enumerate(attempt["questions"]):
        correct = set(await _correct_options(db, question["id"]))
        wrong = [o["id"] for o in question["options"] if o["id"] not in correct]
        answers.append(
            {"question_id": question["id"],
             "selected_option_ids": wrong[:1] if index else sorted(correct)}
        )
    await client.post(
        f"{API}/assessments/attempts/{attempt['attempt_id']}/submit",
        headers=headers, json={"answers": answers},
    )
    measured = await client.get(f"{API}/students/me/skills", headers=headers)
    python = next(s for s in measured.json()["data"] if s["skill"]["name"] == "Python")
    assert python["source"] == "ASSESSMENT"
    assert python["level"] != "EXPERT", "an unevidenced claim must not survive measurement"


async def test_self_assessment_records_lower_confidence(client: AsyncClient, db):
    from app.models.assessment import AssessmentOption

    data = await register(client, "selfassess@example.edu", "STUDENT")
    headers = auth_header(data)
    attempt = await _start(client, headers, "Professional Skills Self-Assessment")

    answers = []
    for question in attempt["questions"]:
        options = (
            await db.execute(
                select(AssessmentOption)
                .where(AssessmentOption.question_id == uuid.UUID(question["id"]))
                .order_by(AssessmentOption.proficiency_value.desc())
            )
        ).scalars().all()
        answers.append(
            {"question_id": question["id"], "selected_option_ids": [str(options[0].id)]}
        )
    response = await client.post(
        f"{API}/assessments/attempts/{attempt['attempt_id']}/submit",
        headers=headers, json={"answers": answers},
    )
    result = response.json()["data"]
    assert result["percentage"] == 100.0
    # One question per soft skill => lowest confidence band.
    assert all(s["confidence"] <= 0.6 for s in result["skill_scores"])


async def test_attempt_cannot_be_submitted_twice(client: AsyncClient, db):
    data = await register(client, "double.submit@example.edu", "STUDENT")
    headers = auth_header(data)
    attempt = await _start(client, headers, "Analytical Aptitude")
    answers = [
        {"question_id": q["id"], "selected_option_ids": await _correct_options(db, q["id"])}
        for q in attempt["questions"]
    ]
    first = await client.post(
        f"{API}/assessments/attempts/{attempt['attempt_id']}/submit",
        headers=headers, json={"answers": answers},
    )
    assert first.status_code == 200
    second = await client.post(
        f"{API}/assessments/attempts/{attempt['attempt_id']}/submit",
        headers=headers, json={"answers": answers},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ATTEMPT_ALREADY_SUBMITTED"


async def test_cannot_submit_another_students_attempt(client: AsyncClient, db):
    victim = await register(client, "victim.attempt@example.edu", "STUDENT")
    attacker = await register(client, "attacker.attempt@example.edu", "STUDENT")
    attempt = await _start(client, auth_header(victim), "Analytical Aptitude")

    response = await client.post(
        f"{API}/assessments/attempts/{attempt['attempt_id']}/submit",
        headers=auth_header(attacker),
        json={"answers": [{"question_id": attempt["questions"][0]["id"],
                           "selected_option_ids": []}]},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ATTEMPT_NOT_OWNED"


async def test_answers_for_foreign_questions_are_rejected(client: AsyncClient):
    data = await register(client, "foreign.question@example.edu", "STUDENT")
    headers = auth_header(data)
    attempt = await _start(client, headers, "Analytical Aptitude")
    other = await _start(client, headers, "Python Fundamentals")

    response = await client.post(
        f"{API}/assessments/attempts/{attempt['attempt_id']}/submit",
        headers=headers,
        json={"answers": [{"question_id": other["questions"][0]["id"],
                           "selected_option_ids": []}]},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNKNOWN_QUESTION"


async def test_restarting_an_open_attempt_does_not_consume_one(client: AsyncClient):
    data = await register(client, "refresh.safe@example.edu", "STUDENT")
    headers = auth_header(data)
    first = await _start(client, headers, "Analytical Aptitude")
    second = await _start(client, headers, "Analytical Aptitude")
    assert first["attempt_id"] == second["attempt_id"]
    assert second["attempt_number"] == 1


async def test_attempt_history_and_review(client: AsyncClient, db):
    data = await register(client, "history@example.edu", "STUDENT")
    headers = auth_header(data)
    attempt = await _start(client, headers, "DevOps, Containers & Delivery")
    answers = [
        {"question_id": q["id"], "selected_option_ids": await _correct_options(db, q["id"])}
        for q in attempt["questions"]
    ]
    await client.post(
        f"{API}/assessments/attempts/{attempt['attempt_id']}/submit",
        headers=headers, json={"answers": answers},
    )

    history = await client.get(f"{API}/assessments/my-attempts", headers=headers)
    assert history.status_code == 200
    assert history.json()["meta"]["total"] >= 1

    review = await client.get(
        f"{API}/assessments/attempts/{attempt['attempt_id']}", headers=headers
    )
    assert review.status_code == 200
    body = review.json()["data"]
    # The review discloses correct answers and explanations *after* submission.
    assert body["answers"][0]["correct_option_ids"]
    assert body["answers"][0]["explanation"]
