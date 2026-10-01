"""TF-IDF vectorization and text similarity for the ML pipeline.

Uses scikit-learn TF-IDF for text representation and cosine similarity for
matching. This module handles all text-to-vector transformations.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.sparse import issparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.ml.config import ml_config

log = logging.getLogger("ml.embeddings")


class TextVectorizer:
    """TF-IDF vectorizer with save/load support."""

    def __init__(
        self,
        max_features: int = ml_config.tfidf_max_features,
        ngram_range: tuple[int, int] = ml_config.tfidf_ngram_range,
        name: str = "default",
    ):
        self.name = name
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            stop_words="english",
            sublinear_tf=True,
            min_df=2,
            max_df=0.95,
        )
        self._fitted = False

    def fit(self, texts: list[str]) -> "TextVectorizer":
        """Fit the vectorizer on a corpus."""
        if not texts:
            log.warning("Empty corpus for %s vectorizer", self.name)
            return self
        # Filter out empty strings
        valid = [t for t in texts if t.strip()]
        if len(valid) < 2:
            log.warning("Too few documents (%d) for %s vectorizer", len(valid), self.name)
            # Use a minimal fit so we don't crash
            self.vectorizer.fit(valid if valid else ["placeholder"])
            self._fitted = True
            return self
        self.vectorizer.fit(valid)
        self._fitted = True
        log.info("Fitted %s vectorizer on %d documents, vocabulary size %d",
                 self.name, len(valid), len(self.vectorizer.vocabulary_))
        return self

    def transform(self, texts: list[str]) -> np.ndarray:
        """Transform texts to TF-IDF vectors."""
        if not self._fitted:
            raise RuntimeError(f"Vectorizer {self.name} not fitted yet")
        matrix = self.vectorizer.transform(texts)
        return matrix.toarray() if issparse(matrix) else matrix

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(texts)
        return self.transform(texts)

    def save(self, path: Path | None = None) -> Path:
        """Save the fitted vectorizer."""
        if path is None:
            ml_config.ensure_dirs()
            path = ml_config.vectorizers_dir / f"{self.name}_vectorizer.joblib"
        joblib.dump(self.vectorizer, path)
        log.info("Saved %s vectorizer to %s", self.name, path)
        return path

    @classmethod
    def load(cls, name: str, path: Path | None = None) -> "TextVectorizer":
        """Load a previously saved vectorizer."""
        if path is None:
            path = ml_config.vectorizers_dir / f"{name}_vectorizer.joblib"
        if not path.exists():
            raise FileNotFoundError(f"Vectorizer not found: {path}")
        instance = cls(name=name)
        instance.vectorizer = joblib.load(path)
        instance._fitted = True
        log.info("Loaded %s vectorizer from %s", name, path)
        return instance


def compute_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    if vec_a.ndim == 1:
        vec_a = vec_a.reshape(1, -1)
    if vec_b.ndim == 1:
        vec_b = vec_b.reshape(1, -1)
    sim = cosine_similarity(vec_a, vec_b)
    return float(sim[0, 0])


def compute_similarity_batch(
    query_vec: np.ndarray, candidate_vecs: np.ndarray
) -> np.ndarray:
    """Compute cosine similarity between a query and multiple candidates."""
    if query_vec.ndim == 1:
        query_vec = query_vec.reshape(1, -1)
    return cosine_similarity(query_vec, candidate_vecs).flatten()


def skill_overlap_score(
    student_skills: list[str], required_skills: list[str]
) -> tuple[float, list[str], list[str]]:
    """Compute skill overlap between student and requirement.

    Returns (score, matched_skills, missing_skills).
    """
    from app.ml.preprocessing import normalise_skill_name

    student_set = {normalise_skill_name(s) for s in student_skills}
    required_set = {normalise_skill_name(s) for s in required_skills}

    if not required_set:
        return 1.0, [], []

    matched = student_set & required_set
    missing = required_set - student_set

    score = len(matched) / len(required_set) if required_set else 0.0

    # Map back to original names for display
    matched_names = [s for s in required_skills if normalise_skill_name(s) in matched]
    missing_names = [s for s in required_skills if normalise_skill_name(s) in missing]

    return score, matched_names, missing_names
