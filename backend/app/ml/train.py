"""Model training pipeline.

Trains real ML models on the generated/collected datasets:
1. Career prediction model (LightGBM classifier)
2. Job ranking model (LightGBM regressor)
3. Course ranking model (LightGBM regressor)

Each model follows: data → features → train → evaluate → serialize.

Can be run as: python -m app.ml.train
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from app.ml.config import ml_config
from app.ml.dataset import (
    CAREER_ROLES,
    generate_career_dataset,
    generate_course_relevance_dataset,
    generate_job_relevance_dataset,
    save_datasets,
)

log = logging.getLogger("ml.train")


def _ensure_artifacts():
    ml_config.ensure_dirs()
    for subdir in ["career_model", "job_model", "course_model", "skill_model"]:
        (ml_config.models_dir / subdir).mkdir(parents=True, exist_ok=True)


class TrainingResult:
    """Result of a model training run."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.algorithm = ""
        self.version = "v1.0"
        self.training_date = datetime.now(timezone.utc).isoformat()
        self.dataset_size = 0
        self.train_size = 0
        self.test_size = 0
        self.metrics: dict[str, float] = {}
        self.feature_names: list[str] = []
        self.feature_importances: dict[str, float] = {}
        self.artifact_path = ""
        self.training_time_seconds = 0.0
        self.label_type = "SYNTHETIC"

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "algorithm": self.algorithm,
            "version": self.version,
            "training_date": self.training_date,
            "dataset_size": self.dataset_size,
            "train_size": self.train_size,
            "test_size": self.test_size,
            "metrics": self.metrics,
            "feature_names": self.feature_names,
            "feature_importances": self.feature_importances,
            "artifact_path": self.artifact_path,
            "training_time_seconds": self.training_time_seconds,
            "label_type": self.label_type,
        }


def train_career_model(df: pd.DataFrame | None = None) -> TrainingResult:
    """Train the career prediction model.

    Input: student features + role → match probability
    Model: LightGBM classifier (3-class: poor/partial/strong match)
    """
    import lightgbm as lgb
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        f1_score,
        precision_score,
        recall_score,
    )

    _ensure_artifacts()
    result = TrainingResult("career_model")
    result.algorithm = "LightGBM Classifier"
    start = time.time()

    log.info("Training career prediction model...")

    if df is None:
        df = generate_career_dataset()

    # Features
    feature_cols = [
        "n_skills", "n_core_skills_matched", "n_preferred_skills_matched",
        "avg_skill_score", "avg_skill_confidence", "n_advanced_skills",
        "cgpa", "n_experiences", "n_projects", "n_certifications",
        "profile_completion", "is_preferred_role",
    ]

    X = df[feature_cols].values
    y = df["match_label"].values

    result.dataset_size = len(df)
    result.feature_names = feature_cols

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=ml_config.test_size, random_state=ml_config.random_state,
        stratify=y
    )
    result.train_size = len(X_train)
    result.test_size = len(X_test)

    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Also encode role labels for the role predictor
    role_encoder = LabelEncoder()
    role_encoder.fit(list(CAREER_ROLES.keys()))

    # Train LightGBM
    model = lgb.LGBMClassifier(
        n_estimators=ml_config.career_n_estimators,
        max_depth=ml_config.career_max_depth,
        learning_rate=ml_config.career_learning_rate,
        random_state=ml_config.random_state,
        num_leaves=31,
        min_child_samples=20,
        verbose=-1,
    )
    model.fit(X_train_scaled, y_train)

    # Evaluate
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

    result.metrics = {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
    }

    # Feature importances
    importances = model.feature_importances_
    result.feature_importances = {
        name: round(float(imp), 4) for name, imp in zip(feature_cols, importances)
    }

    # Save artifacts
    model_dir = ml_config.models_dir / "career_model"
    joblib.dump(model, model_dir / "model.joblib")
    joblib.dump(scaler, ml_config.scalers_dir / "career_scaler.joblib")
    joblib.dump(role_encoder, ml_config.encoders_dir / "role_encoder.joblib")
    result.artifact_path = str(model_dir / "model.joblib")

    result.training_time_seconds = round(time.time() - start, 2)

    log.info("Career model trained — Accuracy: %.4f, F1: %.4f, Time: %.1fs",
             accuracy, f1, result.training_time_seconds)
    log.info("Classification report:\n%s", classification_report(y_test, y_pred, zero_division=0))

    return result


def train_job_ranking_model(df: pd.DataFrame | None = None) -> TrainingResult:
    """Train the job relevance ranking model.

    Input: student-job feature pair → relevance score
    Model: LightGBM regressor
    """
    import lightgbm as lgb
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    _ensure_artifacts()
    result = TrainingResult("job_ranking_model")
    result.algorithm = "LightGBM Regressor"
    start = time.time()

    log.info("Training job ranking model...")

    if df is None:
        df = generate_job_relevance_dataset()

    feature_cols = [
        "skill_overlap", "n_matched_skills", "n_required_skills",
        "n_student_skills", "is_preferred_role", "cgpa",
        "n_experiences", "n_projects",
    ]

    X = df[feature_cols].values
    y = df["relevance_score"].values

    result.dataset_size = len(df)
    result.feature_names = feature_cols

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=ml_config.test_size, random_state=ml_config.random_state
    )
    result.train_size = len(X_train)
    result.test_size = len(X_test)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = lgb.LGBMRegressor(
        n_estimators=ml_config.job_n_estimators,
        max_depth=ml_config.job_max_depth,
        learning_rate=ml_config.job_learning_rate,
        random_state=ml_config.random_state,
        verbose=-1,
    )
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = r2_score(y_test, y_pred)

    # Compute NDCG@10
    ndcg = _compute_ndcg(y_test, y_pred, k=10)

    result.metrics = {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
        "ndcg_at_10": round(ndcg, 4),
    }

    importances = model.feature_importances_
    result.feature_importances = {
        name: round(float(imp), 4) for name, imp in zip(feature_cols, importances)
    }

    model_dir = ml_config.models_dir / "job_model"
    joblib.dump(model, model_dir / "model.joblib")
    joblib.dump(scaler, ml_config.scalers_dir / "job_scaler.joblib")
    result.artifact_path = str(model_dir / "model.joblib")

    result.training_time_seconds = round(time.time() - start, 2)

    log.info("Job ranking model trained — MAE: %.4f, NDCG@10: %.4f, Time: %.1fs",
             mae, ndcg, result.training_time_seconds)

    return result


def train_course_ranking_model(df: pd.DataFrame | None = None) -> TrainingResult:
    """Train the course relevance ranking model.

    Input: student-course feature pair → relevance score
    Model: LightGBM regressor
    """
    import lightgbm as lgb
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    _ensure_artifacts()
    result = TrainingResult("course_ranking_model")
    result.algorithm = "LightGBM Regressor"
    start = time.time()

    log.info("Training course ranking model...")

    if df is None:
        df = generate_course_relevance_dataset()

    feature_cols = [
        "n_skills_to_learn", "n_skills_already_has", "gap_coverage",
        "difficulty_compatibility", "course_duration_hours",
        "is_for_target_role", "avg_student_level",
    ]

    X = df[feature_cols].values
    y = df["relevance_score"].values

    result.dataset_size = len(df)
    result.feature_names = feature_cols

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=ml_config.test_size, random_state=ml_config.random_state
    )
    result.train_size = len(X_train)
    result.test_size = len(X_test)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = lgb.LGBMRegressor(
        n_estimators=ml_config.course_n_estimators,
        max_depth=ml_config.course_max_depth,
        learning_rate=ml_config.course_learning_rate,
        random_state=ml_config.random_state,
        verbose=-1,
    )
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = r2_score(y_test, y_pred)
    ndcg = _compute_ndcg(y_test, y_pred, k=10)

    result.metrics = {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
        "ndcg_at_10": round(ndcg, 4),
    }

    importances = model.feature_importances_
    result.feature_importances = {
        name: round(float(imp), 4) for name, imp in zip(feature_cols, importances)
    }

    model_dir = ml_config.models_dir / "course_model"
    joblib.dump(model, model_dir / "model.joblib")
    joblib.dump(scaler, ml_config.scalers_dir / "course_scaler.joblib")
    result.artifact_path = str(model_dir / "model.joblib")

    result.training_time_seconds = round(time.time() - start, 2)

    log.info("Course ranking model trained — MAE: %.4f, NDCG@10: %.4f, Time: %.1fs",
             mae, ndcg, result.training_time_seconds)

    return result


def _compute_ndcg(y_true: np.ndarray, y_pred: np.ndarray, k: int = 10) -> float:
    """Compute NDCG@K for ranking evaluation."""
    if len(y_true) < k:
        k = len(y_true)
    if k == 0:
        return 0.0

    # Sort by predicted scores
    pred_order = np.argsort(-y_pred)[:k]
    ideal_order = np.argsort(-y_true)[:k]

    # DCG
    dcg = sum(y_true[pred_order[i]] / np.log2(i + 2) for i in range(k))
    # IDCG
    idcg = sum(y_true[ideal_order[i]] / np.log2(i + 2) for i in range(k))

    return dcg / idcg if idcg > 0 else 0.0


def train_all_models() -> dict[str, Any]:
    """Train all ML models and save artifacts.

    Returns a summary of all training results.
    """
    _ensure_artifacts()
    log.info("=" * 60)
    log.info("Starting ML model training pipeline")
    log.info("=" * 60)

    # Generate datasets
    log.info("Generating training datasets...")
    dataset_info = save_datasets()

    # Train models
    career_result = train_career_model()
    job_result = train_job_ranking_model()
    course_result = train_course_ranking_model()

    # Save combined metrics
    all_metrics = {
        "training_date": datetime.now(timezone.utc).isoformat(),
        "models": {
            career_result.model_name: career_result.to_dict(),
            job_result.model_name: job_result.to_dict(),
            course_result.model_name: course_result.to_dict(),
        },
        "datasets": dataset_info,
        "label_disclaimer": (
            "All training labels are SYNTHETIC - derived from skill/role compatibility "
            "rules applied to synthetic student profiles. No label represents real user "
            "behaviour. As real user interaction data accumulates, models should be "
            "retrained on observed data."
        ),
    }

    metrics_path = ml_config.metrics_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(all_metrics, f, indent=2, default=str)

    log.info("=" * 60)
    log.info("Training complete!")
    log.info("Career model — F1: %.4f", career_result.metrics.get("f1_score", 0))
    log.info("Job ranking model — NDCG@10: %.4f", job_result.metrics.get("ndcg_at_10", 0))
    log.info("Course ranking model — NDCG@10: %.4f", course_result.metrics.get("ndcg_at_10", 0))
    log.info("Metrics saved to: %s", metrics_path)
    log.info("=" * 60)

    return all_metrics


# ── CLI entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    print("SkillBridge ML Training Pipeline")
    print("=" * 60)

    results = train_all_models()

    print("\n" + "=" * 60)
    print("TRAINING SUMMARY")
    print("=" * 60)
    for name, result in results.get("models", {}).items():
        print(f"\n{name}:")
        print(f"  Algorithm: {result['algorithm']}")
        print(f"  Dataset: {result['dataset_size']} records")
        print(f"  Train/Test: {result['train_size']}/{result['test_size']}")
        print(f"  Metrics:")
        for metric, value in result["metrics"].items():
            print(f"    {metric}: {value}")
        print(f"  Time: {result['training_time_seconds']}s")
    print(f"\nLabel type: {results.get('label_disclaimer', '')[:100]}...")
    print("=" * 60)
