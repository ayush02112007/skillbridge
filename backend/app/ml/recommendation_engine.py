"""Hybrid ML recommendation engine.

Combines ML predictions with the existing deterministic scoring to produce
personalised, explainable recommendations. This is the primary entry point
for the recommendation system.

Architecture:
  Student Profile → Feature Engineering → ML Models → Candidate Retrieval →
  ML Ranking → Explainable Recommendations

When ML models are not trained, the system falls back to the existing
deterministic engine (app.ai.recommender) transparently.
"""
from __future__ import annotations

import logging
from typing import Any

from app.ml.config import ml_config
from app.ml.feature_engineering import (
    StudentFeatures,
    build_student_features_from_profile,
)
from app.ml.inference import get_model_status, predict_career_roles
from app.ml.ranking import rank_courses, rank_jobs

log = logging.getLogger("ml.recommendation_engine")


class MLRecommendationEngine:
    """Hybrid ML + deterministic recommendation engine."""

    def __init__(self):
        self._status = None

    @property
    def ml_available(self) -> bool:
        status = get_model_status()
        return status.get("models_trained", False)

    def get_career_predictions(
        self,
        student_features: StudentFeatures,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Get ML-powered career predictions.

        Returns top career roles ranked by ML-predicted match probability.
        """
        if not self.ml_available:
            return {
                "predictions": [],
                "generated_by": "unavailable",
                "message": "ML models not trained. Run model training first.",
            }

        features_dict = {
            "total_skills": student_features.total_skills,
            "avg_skill_score": student_features.avg_skill_score,
            "avg_skill_confidence": student_features.avg_skill_confidence,
            "advanced_skill_count": student_features.advanced_skill_count,
            "cgpa": student_features.cgpa,
            "internship_count": student_features.internship_count,
            "project_count": student_features.project_count,
            "certification_count": student_features.certification_count,
            "profile_completion": student_features.profile_completion,
            "preferred_roles": student_features.preferred_roles,
        }

        predictions = predict_career_roles(
            features_dict,
            student_features.skill_names,
            top_k=top_k,
        )

        return {
            "predictions": predictions,
            "generated_by": "ml_career_model",
            "model_version": "v1.0",
            "feature_summary": {
                "total_skills": student_features.total_skills,
                "skill_names": student_features.skill_names[:10],
                "career_interests": student_features.career_interests,
                "preferred_roles": student_features.preferred_roles,
            },
        }

    def get_job_recommendations(
        self,
        student_features: StudentFeatures,
        jobs: list[dict[str, Any]],
        top_k: int = 10,
    ) -> dict[str, Any]:
        """Get ML-ranked job recommendations."""
        if not jobs:
            return {"recommendations": [], "generated_by": "empty_candidates"}

        ranked = rank_jobs(student_features, jobs, top_k=top_k)

        return {
            "recommendations": ranked,
            "total_candidates": len(jobs),
            "returned": len(ranked),
            "generated_by": ranked[0].get("generated_by", "fallback") if ranked else "empty",
        }

    def get_internship_recommendations(
        self,
        student_features: StudentFeatures,
        internships: list[dict[str, Any]],
        top_k: int = 10,
    ) -> dict[str, Any]:
        """Get ML-ranked internship recommendations.

        Uses the same job ranking model — internships are jobs with
        is_internship=True.
        """
        for i in internships:
            i["is_internship"] = True

        ranked = rank_jobs(student_features, internships, top_k=top_k)

        return {
            "recommendations": ranked,
            "total_candidates": len(internships),
            "returned": len(ranked),
            "generated_by": ranked[0].get("generated_by", "fallback") if ranked else "empty",
        }

    def get_course_recommendations(
        self,
        student_features: StudentFeatures,
        courses: list[dict[str, Any]],
        target_role: str | None = None,
        top_k: int = 10,
    ) -> dict[str, Any]:
        """Get ML-ranked course recommendations."""
        if not courses:
            return {"recommendations": [], "generated_by": "empty_candidates"}

        # Get target role skills
        target_role_skills: list[str] = []
        if target_role:
            from app.ml.dataset import CAREER_ROLES
            role_data = CAREER_ROLES.get(target_role, {})
            target_role_skills = role_data.get("core_skills", []) + role_data.get("preferred_skills", [])

        ranked = rank_courses(
            student_features, courses,
            target_role_skills=target_role_skills,
            top_k=top_k,
        )

        return {
            "recommendations": ranked,
            "total_candidates": len(courses),
            "returned": len(ranked),
            "generated_by": ranked[0].get("generated_by", "fallback") if ranked else "empty",
        }

    def get_skill_gaps(
        self,
        student_features: StudentFeatures,
        target_role: str | None = None,
    ) -> dict[str, Any]:
        """Get ML-enhanced skill gap analysis."""
        from app.ml.dataset import CAREER_ROLES
        from app.ml.embeddings import skill_overlap_score

        if not target_role:
            # Use top predicted career role
            predictions = self.get_career_predictions(student_features, top_k=1)
            if predictions.get("predictions"):
                target_role = predictions["predictions"][0]["role"]

        if not target_role or target_role not in CAREER_ROLES:
            return {"gaps": [], "message": "No target role specified or found"}

        role_data = CAREER_ROLES[target_role]
        all_required = role_data["core_skills"] + role_data["preferred_skills"]

        overlap, matched, missing = skill_overlap_score(
            student_features.skill_names, all_required
        )

        core_overlap, core_matched, core_missing = skill_overlap_score(
            student_features.skill_names, role_data["core_skills"]
        )

        # Compute readiness probability
        readiness = round(core_overlap * 100, 1)

        # Priority scoring for missing skills
        gap_items = []
        for i, skill in enumerate(core_missing):
            gap_items.append({
                "skill_name": skill,
                "importance": "REQUIRED",
                "priority": i + 1,
                "current_evidence": "Missing",
                "predicted_importance": round(max(50, 90 - i * 5), 1),
                "category": "core",
            })
        for i, skill in enumerate(missing):
            if skill not in core_missing:
                gap_items.append({
                    "skill_name": skill,
                    "importance": "PREFERRED",
                    "priority": len(core_missing) + i + 1,
                    "current_evidence": "Missing",
                    "predicted_importance": round(max(30, 70 - i * 5), 1),
                    "category": "preferred",
                })

        return {
            "target_role": target_role,
            "readiness_score": readiness,
            "core_skill_coverage": round(core_overlap * 100, 1),
            "total_skill_coverage": round(overlap * 100, 1),
            "matched_skills": matched,
            "gaps": gap_items[:10],
            "recommendation": (
                f"You meet {len(core_matched)} of {len(role_data['core_skills'])} "
                f"core requirements for {target_role}. "
                + (f"Focus on {', '.join(core_missing[:3])} first." if core_missing else "You're well prepared!")
            ),
            "generated_by": "ml_skill_gap_model",
        }

    def get_learning_path(
        self,
        student_features: StudentFeatures,
        target_role: str,
        courses: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate an ML-driven learning path."""
        gaps = self.get_skill_gaps(student_features, target_role)
        gap_items = gaps.get("gaps", [])

        if not gap_items:
            return {
                "target_role": target_role,
                "steps": [],
                "message": "No skill gaps identified — you're well-prepared!",
                "generated_by": "ml_learning_path",
            }

        # Build learning steps
        steps = []
        for i, gap in enumerate(gap_items[:6]):
            step = {
                "order": i + 1,
                "skill_name": gap["skill_name"],
                "importance": gap["importance"],
                "priority": gap["priority"],
                "status": "NOT_STARTED",
                "estimated_hours": 20 + i * 5,
                "courses": [],
            }

            # Find matching courses
            if courses:
                matching = [
                    c for c in courses
                    if gap["skill_name"].lower() in " ".join(
                        c.get("skills_covered", c.get("skills", []))
                    ).lower()
                ]
                step["courses"] = matching[:3]

            steps.append(step)

        return {
            "target_role": target_role,
            "readiness_score": gaps["readiness_score"],
            "steps": steps,
            "total_estimated_hours": sum(s["estimated_hours"] for s in steps),
            "generated_by": "ml_learning_path",
        }

    def get_profile_analysis(
        self,
        student_features: StudentFeatures,
    ) -> dict[str, Any]:
        """Comprehensive ML profile analysis."""
        career_predictions = self.get_career_predictions(student_features, top_k=3)

        top_role = None
        if career_predictions.get("predictions"):
            top_role = career_predictions["predictions"][0]["role"]

        skill_gaps = self.get_skill_gaps(student_features, top_role)

        # Strengths analysis from features
        strengths = []
        if student_features.advanced_skill_count >= 3:
            strengths.append(f"{student_features.advanced_skill_count} advanced-level skills")
        if student_features.project_count >= 3:
            strengths.append(f"{student_features.project_count} projects demonstrating practical ability")
        if student_features.certification_count >= 2:
            strengths.append(f"{student_features.certification_count} certifications backing your skills")
        if student_features.internship_count >= 1:
            strengths.append(f"{student_features.internship_count} internship(s) providing real experience")
        if student_features.cgpa >= 8.0:
            strengths.append(f"Strong academic record (CGPA: {student_features.cgpa})")
        if student_features.verified_skill_count >= 3:
            strengths.append(f"{student_features.verified_skill_count} verified skills")

        return {
            "career_predictions": career_predictions,
            "skill_gaps": skill_gaps,
            "strengths": strengths,
            "profile_completion": student_features.profile_completion,
            "total_skills": student_features.total_skills,
            "top_career_match": career_predictions.get("predictions", [{}])[0] if career_predictions.get("predictions") else None,
            "model_status": get_model_status(),
            "generated_by": "ml_profile_analysis",
        }


# Global engine instance
_engine = MLRecommendationEngine()


def get_ml_engine() -> MLRecommendationEngine:
    return _engine
