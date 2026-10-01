"""ML pipeline configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MLConfig:
    """Central configuration for the ML pipeline."""

    # Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent)
    artifacts_dir: Path = field(default_factory=lambda: Path(__file__).parent / "artifacts")
    models_dir: Path = field(default_factory=lambda: Path(__file__).parent / "artifacts" / "models")
    encoders_dir: Path = field(default_factory=lambda: Path(__file__).parent / "artifacts" / "encoders")
    vectorizers_dir: Path = field(default_factory=lambda: Path(__file__).parent / "artifacts" / "vectorizers")
    scalers_dir: Path = field(default_factory=lambda: Path(__file__).parent / "artifacts" / "scalers")
    metrics_dir: Path = field(default_factory=lambda: Path(__file__).parent / "artifacts" / "metrics")
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")

    # Model parameters
    random_state: int = 42
    test_size: float = 0.2
    val_size: float = 0.1
    min_training_samples: int = 50

    # Feature engineering
    tfidf_max_features: int = 5000
    tfidf_ngram_range: tuple[int, int] = (1, 2)
    max_skill_features: int = 200

    # Career model
    career_n_estimators: int = 200
    career_max_depth: int = 8
    career_learning_rate: float = 0.1

    # Job ranking model
    job_n_estimators: int = 150
    job_max_depth: int = 6
    job_learning_rate: float = 0.1

    # Course ranking model
    course_n_estimators: int = 150
    course_max_depth: int = 6
    course_learning_rate: float = 0.1

    # Demo mode
    demo_mode: bool = field(default_factory=lambda: os.getenv("DEMO_MODE", "false").lower() == "true")

    # External providers
    adzuna_app_id: str = field(default_factory=lambda: os.getenv("ADZUNA_APP_ID", ""))
    adzuna_app_key: str = field(default_factory=lambda: os.getenv("ADZUNA_APP_KEY", ""))
    coursera_api_key: str = field(default_factory=lambda: os.getenv("COURSERA_API_KEY", ""))
    udemy_client_id: str = field(default_factory=lambda: os.getenv("UDEMY_CLIENT_ID", ""))
    udemy_client_secret: str = field(default_factory=lambda: os.getenv("UDEMY_CLIENT_SECRET", ""))

    # Cache TTL (seconds)
    job_cache_ttl: int = 1800  # 30 minutes
    course_cache_ttl: int = 14400  # 4 hours

    def ensure_dirs(self) -> None:
        """Create all artifact directories."""
        for d in [
            self.artifacts_dir, self.models_dir, self.encoders_dir,
            self.vectorizers_dir, self.scalers_dir, self.metrics_dir,
            self.data_dir,
            self.data_dir / "raw", self.data_dir / "processed",
            self.data_dir / "training", self.data_dir / "validation",
            self.data_dir / "test",
        ]:
            d.mkdir(parents=True, exist_ok=True)


ml_config = MLConfig()
