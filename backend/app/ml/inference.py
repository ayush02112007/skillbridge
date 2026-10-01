"""ML inference engine — loads trained models and generates predictions.

Models are lazy-loaded: the first inference call loads from disk, subsequent
calls use the cached model. This avoids startup cost when ML endpoints aren't
used.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.ml.config import ml_config
from app.ml.dataset import CAREER_ROLES

log = logging.getLogger("ml.inference")


class _ModelCache:
    """Lazy-loading model cache. Thread-safe via GIL for CPU inference."""

    def __init__(self):
        self._career_model = None
        self._career_scaler = None
        self._role_encoder = None
        self._job_model = None
        self._job_scaler = None
        self._course_model = None
        self._course_scaler = None
        self._metrics: dict[str, Any] | None = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def _load_if_exists(self, path: Path):
        if path.exists():
            return joblib.load(path)
        return None

    def load(self) -> bool:
        """Attempt to load all models. Returns True if at least career model loaded."""
        try:
            career_path = ml_config.models_dir / "career_model" / "model.joblib"
            if not career_path.exists():
                log.warning("Career model not found at %s — ML inference unavailable. "
                            "Run 'python -m app.ml.train' to train models.", career_path)
                return False

            self._career_model = joblib.load(career_path)
            self._career_scaler = self._load_if_exists(ml_config.scalers_dir / "career_scaler.joblib")
            self._role_encoder = self._load_if_exists(ml_config.encoders_dir / "role_encoder.joblib")

            self._job_model = self._load_if_exists(ml_config.models_dir / "job_model" / "model.joblib")
            self._job_scaler = self._load_if_exists(ml_config.scalers_dir / "job_scaler.joblib")

            self._course_model = self._load_if_exists(ml_config.models_dir / "course_model" / "model.joblib")
            self._course_scaler = self._load_if_exists(ml_config.scalers_dir / "course_scaler.joblib")

            # Load metrics
            metrics_path = ml_config.metrics_dir / "metrics.json"
            if metrics_path.exists():
                with open(metrics_path) as f:
                    self._metrics = json.load(f)

            self._loaded = True
            log.info("ML models loaded successfully")
            return True
        except Exception as e:
            log.error("Failed to load ML models: %s", e)
            return False

    def ensure_loaded(self) -> bool:
        if not self._loaded:
            return self.load()
        return True

    def reload(self) -> bool:
        """Force reload of all models."""
        self._loaded = False
        return self.load()

    @property
    def metrics(self) -> dict[str, Any]:
        return self._metrics or {}


# Global model cache
_cache = _ModelCache()


def get_model_status() -> dict[str, Any]:
    """Get current model status."""
    has_models = (ml_config.models_dir / "career_model" / "model.joblib").exists()
    metrics_path = ml_config.metrics_dir / "metrics.json"
    metrics = {}
    if metrics_path.exists():
        with open(metrics_path) as f:
            metrics = json.load(f)

    return {
        "models_trained": has_models,
        "models_loaded": _cache.is_loaded,
        "career_model": {
            "exists": (ml_config.models_dir / "career_model" / "model.joblib").exists(),
            "metrics": metrics.get("models", {}).get("career_model", {}).get("metrics", {}),
        },
        "job_ranking_model": {
            "exists": (ml_config.models_dir / "job_model" / "model.joblib").exists(),
            "metrics": metrics.get("models", {}).get("job_ranking_model", {}).get("metrics", {}),
        },
        "course_ranking_model": {
            "exists": (ml_config.models_dir / "course_model" / "model.joblib").exists(),
            "metrics": metrics.get("models", {}).get("course_ranking_model", {}).get("metrics", {}),
        },
        "training_date": metrics.get("training_date", ""),
        "label_type": "SYNTHETIC",
        "datasets": metrics.get("datasets", {}),
    }


def predict_career_match(features: dict[str, float]) -> dict[str, Any]:
    """Predict career match for a single student-role pair.

    features must contain the career model feature columns.
    Returns match class (0/1/2) and probabilities.
    """
    if not _cache.ensure_loaded() or _cache._career_model is None:
        return {"error": "Career model not trained", "available": False}

    feature_cols = [
        "n_skills", "n_core_skills_matched", "n_preferred_skills_matched",
        "avg_skill_score", "avg_skill_confidence", "n_advanced_skills",
        "cgpa", "n_experiences", "n_projects", "n_certifications",
        "profile_completion", "is_preferred_role",
    ]

    X = np.array([[features.get(col, 0.0) for col in feature_cols]])
    if _cache._career_scaler is not None:
        X = _cache._career_scaler.transform(X)

    pred_class = int(_cache._career_model.predict(X)[0])
    probas = _cache._career_model.predict_proba(X)[0]

    return {
        "available": True,
        "match_class": pred_class,
        "match_label": {0: "poor_match", 1: "partial_match", 2: "strong_match"}.get(pred_class, "unknown"),
        "probabilities": {
            "poor_match": round(float(probas[0]), 4),
            "partial_match": round(float(probas[1]), 4),
            "strong_match": round(float(probas[2]), 4),
        },
        "confidence": round(float(max(probas)), 4),
        "generated_by": "ml_career_model",
    }


def predict_career_roles(
    student_features: dict[str, Any],
    skill_names: list[str],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Predict top career roles for a student.

    Returns ranked list of roles with match probabilities.
    """
    if not _cache.ensure_loaded() or _cache._career_model is None:
        return []

    from app.ml.embeddings import skill_overlap_score

    results = []
    for role_name, role_data in CAREER_ROLES.items():
        core_overlap, matched_core, missing_core = skill_overlap_score(
            skill_names, role_data["core_skills"]
        )
        pref_overlap, matched_pref, missing_pref = skill_overlap_score(
            skill_names, role_data["preferred_skills"]
        )

        features = {
            "n_skills": student_features.get("total_skills", len(skill_names)),
            "n_core_skills_matched": len(matched_core),
            "n_preferred_skills_matched": len(matched_pref),
            "avg_skill_score": student_features.get("avg_skill_score", 50.0),
            "avg_skill_confidence": student_features.get("avg_skill_confidence", 0.5),
            "n_advanced_skills": student_features.get("advanced_skill_count", 0),
            "cgpa": student_features.get("cgpa", 0.0),
            "n_experiences": student_features.get("internship_count", 0) + student_features.get("experience_count", 0),
            "n_projects": student_features.get("project_count", 0),
            "n_certifications": student_features.get("certification_count", 0),
            "profile_completion": student_features.get("profile_completion", 0),
            "is_preferred_role": 1 if role_name in student_features.get("preferred_roles", []) else 0,
        }

        prediction = predict_career_match(features)
        if not prediction.get("available"):
            continue

        match_prob = prediction["probabilities"]["strong_match"]
        partial_prob = prediction["probabilities"]["partial_match"]
        # Combined score: strong match weighted more
        score = round((match_prob * 100 * 0.7 + partial_prob * 100 * 0.3), 1)

        results.append({
            "role": role_name,
            "family": role_data["family"],
            "match_score": min(100.0, score),
            "ml_confidence": prediction["confidence"],
            "match_class": prediction["match_label"],
            "matched_skills": matched_core + matched_pref,
            "missing_skills": missing_core[:5],
            "core_skill_coverage": round(core_overlap, 3),
            "preferred_skill_coverage": round(pref_overlap, 3),
            "explanation": _build_career_explanation(
                role_name, matched_core, missing_core, core_overlap, score
            ),
            "generated_by": "ml_career_model",
        })

    results.sort(key=lambda r: -r["match_score"])
    return results[:top_k]


def predict_job_relevance(features: dict[str, float]) -> dict[str, Any]:
    """Predict job relevance score for a student-job pair."""
    if not _cache.ensure_loaded() or _cache._job_model is None:
        return {"relevance_score": features.get("skill_overlap", 0.0) * 100, "generated_by": "fallback"}

    feature_cols = [
        "skill_overlap", "n_matched_skills", "n_required_skills",
        "n_student_skills", "is_preferred_role", "cgpa",
        "n_experiences", "n_projects",
    ]

    X = np.array([[features.get(col, 0.0) for col in feature_cols]])
    if _cache._job_scaler is not None:
        X = _cache._job_scaler.transform(X)

    score = float(_cache._job_model.predict(X)[0])
    score = max(0.0, min(1.0, score))

    return {
        "relevance_score": round(score * 100, 1),
        "generated_by": "ml_job_ranking_model",
    }


def predict_course_relevance(features: dict[str, float]) -> dict[str, Any]:
    """Predict course relevance score for a student-course pair."""
    if not _cache.ensure_loaded() or _cache._course_model is None:
        return {"relevance_score": features.get("gap_coverage", 0.0) * 100, "generated_by": "fallback"}

    feature_cols = [
        "n_skills_to_learn", "n_skills_already_has", "gap_coverage",
        "difficulty_compatibility", "course_duration_hours",
        "is_for_target_role", "avg_student_level",
    ]

    X = np.array([[features.get(col, 0.0) for col in feature_cols]])
    if _cache._course_scaler is not None:
        X = _cache._course_scaler.transform(X)

    score = float(_cache._course_model.predict(X)[0])
    score = max(0.0, min(1.0, score))

    return {
        "relevance_score": round(score * 100, 1),
        "generated_by": "ml_course_ranking_model",
    }


def _build_career_explanation(
    role_name: str,
    matched: list[str],
    missing: list[str],
    coverage: float,
    score: float,
) -> dict[str, Any]:
    """Build an explanation for a career prediction from actual model features."""
    factors = []
    if matched:
        factors.append(f"You have {len(matched)} of the core skills: {', '.join(matched[:4])}")
    if coverage >= 0.8:
        factors.append("Strong skill alignment with this role")
    elif coverage >= 0.5:
        factors.append("Moderate skill alignment — a few more skills would strengthen your profile")
    else:
        factors.append("This role requires building several new skills")

    if missing:
        factors.append(f"Key skills to develop: {', '.join(missing[:3])}")

    return {
        "contributing_factors": factors,
        "skill_coverage": round(coverage, 3),
        "matched_skills": matched[:6],
        "missing_skills": missing[:5],
        "recommended_action": (
            f"Focus on building {', '.join(missing[:2])} to strengthen your fit for {role_name}"
            if missing else f"Your skills are well-aligned with {role_name}"
        ),
    }
