"""ML-based ranking for jobs, courses, and internships.

Takes candidate lists and student features, uses trained ML models to rank
them by predicted relevance, and returns explainable results.
"""
from __future__ import annotations

import logging
from typing import Any

from app.ml.embeddings import skill_overlap_score
from app.ml.feature_engineering import StudentFeatures
from app.ml.inference import predict_course_relevance, predict_job_relevance

log = logging.getLogger("ml.ranking")


def rank_jobs(
    student: StudentFeatures,
    jobs: list[dict[str, Any]],
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Rank jobs using the trained ML model.

    For each job, computes:
    - Skill overlap score (exact matching)
    - ML predicted relevance (trained model)
    - Combined score

    Returns ranked list with explanations.
    """
    if not jobs:
        return []

    ranked = []
    for job in jobs:
        required_skills = job.get("required_skills", [])
        overlap_score, matched, missing = skill_overlap_score(
            student.skill_names, required_skills
        )

        # Build features for the ML model
        is_preferred = 0
        job_title_lower = job.get("title", "").lower()
        for role in student.preferred_roles:
            if role.lower() in job_title_lower or job_title_lower in role.lower():
                is_preferred = 1
                break

        features = {
            "skill_overlap": overlap_score,
            "n_matched_skills": len(matched),
            "n_required_skills": len(required_skills),
            "n_student_skills": student.total_skills,
            "is_preferred_role": is_preferred,
            "cgpa": student.cgpa,
            "n_experiences": student.internship_count,
            "n_projects": student.project_count,
        }

        prediction = predict_job_relevance(features)
        ml_score = prediction.get("relevance_score", overlap_score * 100)
        generated_by = prediction.get("generated_by", "fallback")

        # Combined score: ML prediction weighted with skill overlap
        combined_score = round(ml_score * 0.6 + overlap_score * 100 * 0.4, 1)
        combined_score = min(100.0, combined_score)

        # Build explanation from actual features
        reasons = []
        if matched:
            shown = ", ".join(matched[:4])
            reasons.append(f"You have {len(matched)} of {len(required_skills)} required skills: {shown}")
        if is_preferred:
            reasons.append("Aligns with your career interests")
        if student.internship_count > 0:
            reasons.append(f"Your {student.internship_count} previous experience(s) are relevant")
        if missing:
            reasons.append(f"Skills to develop: {', '.join(missing[:3])}")

        ranked.append({
            **job,
            "match_score": combined_score,
            "ml_score": ml_score,
            "skill_overlap": round(overlap_score * 100, 1),
            "matched_skills": matched,
            "missing_skills": missing[:5],
            "reasons": reasons,
            "reason_summary": _job_summary(job, matched, missing, combined_score),
            "generated_by": generated_by,
        })

    ranked.sort(key=lambda r: -r["match_score"])
    return ranked[:top_k]


def rank_courses(
    student: StudentFeatures,
    courses: list[dict[str, Any]],
    target_role_skills: list[str] | None = None,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Rank courses using the trained ML model."""
    if not courses:
        return []

    target_skills = set(target_role_skills or [])
    student_skill_set = set(student.skill_names)
    gap_skills = target_skills - student_skill_set

    # Average student level
    avg_level = 2.0  # default intermediate
    if student.advanced_skill_count + student.intermediate_skill_count + student.beginner_skill_count > 0:
        total = student.advanced_skill_count + student.intermediate_skill_count + student.beginner_skill_count
        avg_level = (student.advanced_skill_count * 3 + student.intermediate_skill_count * 2 +
                     student.beginner_skill_count * 1) / total

    ranked = []
    for course in courses:
        course_skills = set(course.get("skills_covered", course.get("skills", [])))
        already_has = student_skill_set & course_skills
        will_learn = course_skills - student_skill_set

        # Gap coverage: how much of the gap this course addresses
        gap_coverage = len(will_learn & gap_skills) / max(1, len(gap_skills)) if gap_skills else 0.0

        # Difficulty compatibility
        difficulty_map = {"EASY": 1, "MEDIUM": 2, "ADVANCED": 3, "HARD": 3}
        diff_val = difficulty_map.get(course.get("difficulty", "MEDIUM"), 2)
        diff_compat = 1.0 - abs(diff_val - avg_level) * 0.2

        is_for_target = 1 if will_learn & target_skills else 0

        features = {
            "n_skills_to_learn": len(will_learn),
            "n_skills_already_has": len(already_has),
            "gap_coverage": gap_coverage,
            "difficulty_compatibility": max(0, diff_compat),
            "course_duration_hours": course.get("duration_hours", 20),
            "is_for_target_role": is_for_target,
            "avg_student_level": avg_level,
        }

        prediction = predict_course_relevance(features)
        ml_score = prediction.get("relevance_score", gap_coverage * 100)
        generated_by = prediction.get("generated_by", "fallback")

        combined_score = round(ml_score * 0.6 + gap_coverage * 100 * 0.4, 1)
        combined_score = min(100.0, combined_score)

        reasons = []
        if will_learn:
            reasons.append(f"Teaches {len(will_learn)} new skill(s): {', '.join(list(will_learn)[:3])}")
        if is_for_target:
            reasons.append("Covers skills needed for your target role")
        if gap_coverage > 0.3:
            reasons.append(f"Addresses {round(gap_coverage * 100)}% of your skill gaps")
        if course.get("has_certificate"):
            reasons.append("Includes a certificate")

        ranked.append({
            **course,
            "match_score": combined_score,
            "ml_score": ml_score,
            "gap_coverage": round(gap_coverage * 100, 1),
            "skills_to_learn": list(will_learn)[:5],
            "skills_already_known": list(already_has),
            "reasons": reasons,
            "reason_summary": _course_summary(course, will_learn, combined_score),
            "generated_by": generated_by,
        })

    ranked.sort(key=lambda r: -r["match_score"])
    return ranked[:top_k]


def _job_summary(job: dict, matched: list, missing: list, score: float) -> str:
    title = job.get("title", "this role")
    company = job.get("company", job.get("company_name", ""))
    if score >= 80:
        return (
            f"Strong fit for {title}"
            + (f" at {company}" if company else "")
            + f". You match {len(matched)} required skills."
            + (f" Building {missing[0]} would strengthen your profile further." if missing else "")
        )
    elif score >= 50:
        return (
            f"Good potential for {title}"
            + (f" at {company}" if company else "")
            + f". You have {len(matched)} of the required skills"
            + (f", with {', '.join(missing[:2])} as the main gap." if missing else ".")
        )
    else:
        return (
            f"{title} is a growth target — "
            + (f"{len(missing)} skills still needed." if missing else "build more experience in this area.")
        )


def _course_summary(course: dict, will_learn: set, score: float) -> str:
    title = course.get("title", "this course")
    provider = course.get("provider", "")
    if score >= 70:
        return (
            f"{title} is highly relevant — it covers {len(will_learn)} skill(s) you need"
            + (f". Offered by {provider}" if provider else "") + "."
        )
    elif score >= 40:
        return f"{title} can help build {', '.join(list(will_learn)[:2])} skills."
    else:
        return f"{title} offers some value but doesn't directly address your top gaps."
