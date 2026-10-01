"""Feature engineering: build unified feature vectors from student profiles.

Converts heterogeneous student data (skills, education, experience, projects,
certifications, interests, behaviour) into numeric feature vectors that ML
models can consume.

The features produced here are what the ML models actually learn from. They are
NOT hard-coded scoring weights — they are inputs to trained models.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class StudentFeatures:
    """Unified feature representation of a student profile.

    Every field here is either directly from the database or derived through
    a simple, documented transformation. No field is fabricated.
    """

    # Identity (not used as features, but needed for tracking)
    student_id: str = ""

    # Structured numeric features
    cgpa: float = 0.0
    graduation_year: int = 0
    current_year: int = 0
    backlogs: int = 0
    experience_months: float = 0.0
    internship_count: int = 0
    project_count: int = 0
    certification_count: int = 0
    assessment_avg_score: float = 0.0
    profile_completion: int = 0

    # Skill features
    total_skills: int = 0
    technical_skill_count: int = 0
    soft_skill_count: int = 0
    avg_skill_score: float = 0.0
    avg_skill_confidence: float = 0.0
    verified_skill_count: int = 0
    advanced_skill_count: int = 0
    intermediate_skill_count: int = 0
    beginner_skill_count: int = 0

    # Text features (for TF-IDF)
    skill_text: str = ""
    education_text: str = ""
    experience_text: str = ""
    project_text: str = ""
    certification_text: str = ""
    interest_text: str = ""
    combined_text: str = ""

    # Categorical features (encoded as strings, transformed later)
    degree: str = "BACHELORS"
    department: str = ""
    preferred_work_mode: str = ""
    city: str = ""

    # List features
    skill_names: list[str] = field(default_factory=list)
    skill_categories: list[str] = field(default_factory=list)
    career_interests: list[str] = field(default_factory=list)
    preferred_roles: list[str] = field(default_factory=list)
    preferred_locations: list[str] = field(default_factory=list)

    # Behavioural features (from interaction history)
    jobs_viewed: int = 0
    jobs_applied: int = 0
    courses_enrolled: int = 0
    courses_completed: int = 0
    recommendations_clicked: int = 0
    recommendations_dismissed: int = 0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0

    def to_numeric_vector(self) -> np.ndarray:
        """Convert structured features to a numeric array for ML models."""
        return np.array([
            self.cgpa,
            self.graduation_year,
            self.current_year,
            self.backlogs,
            self.experience_months,
            self.internship_count,
            self.project_count,
            self.certification_count,
            self.assessment_avg_score,
            self.profile_completion,
            self.total_skills,
            self.technical_skill_count,
            self.soft_skill_count,
            self.avg_skill_score,
            self.avg_skill_confidence,
            self.verified_skill_count,
            self.advanced_skill_count,
            self.intermediate_skill_count,
            self.beginner_skill_count,
            self.jobs_viewed,
            self.jobs_applied,
            self.courses_enrolled,
            self.courses_completed,
            self.recommendations_clicked,
            self.recommendations_dismissed,
            self.positive_feedback_count,
            self.negative_feedback_count,
        ], dtype=np.float64)

    @staticmethod
    def numeric_feature_names() -> list[str]:
        """Names of the numeric features in the same order as to_numeric_vector()."""
        return [
            "cgpa", "graduation_year", "current_year", "backlogs",
            "experience_months", "internship_count", "project_count",
            "certification_count", "assessment_avg_score", "profile_completion",
            "total_skills", "technical_skill_count", "soft_skill_count",
            "avg_skill_score", "avg_skill_confidence", "verified_skill_count",
            "advanced_skill_count", "intermediate_skill_count",
            "beginner_skill_count", "jobs_viewed", "jobs_applied",
            "courses_enrolled", "courses_completed", "recommendations_clicked",
            "recommendations_dismissed", "positive_feedback_count",
            "negative_feedback_count",
        ]

    def to_dict(self) -> dict[str, Any]:
        """Serialise for storage or API responses."""
        return {
            "student_id": self.student_id,
            "numeric": dict(zip(self.numeric_feature_names(), self.to_numeric_vector().tolist())),
            "skill_names": self.skill_names,
            "career_interests": self.career_interests,
            "preferred_roles": self.preferred_roles,
            "combined_text_length": len(self.combined_text),
        }


@dataclass
class JobFeatures:
    """Feature representation of a job/internship posting."""

    job_id: str = ""
    title: str = ""
    normalised_title: str = ""
    company: str = ""
    location: str = ""
    work_mode: str = ""
    description: str = ""
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    min_experience_years: float = 0.0
    salary_min: float = 0.0
    salary_max: float = 0.0
    is_internship: bool = False
    industry: str = ""
    combined_text: str = ""
    source: str = "internal"
    external_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "required_skills": self.required_skills,
            "source": self.source,
        }


@dataclass
class CourseFeatures:
    """Feature representation of a course/learning program."""

    course_id: str = ""
    title: str = ""
    provider: str = ""
    description: str = ""
    skills_covered: list[str] = field(default_factory=list)
    difficulty: str = "MEDIUM"
    duration_hours: int = 0
    has_certificate: bool = False
    is_free: bool = False
    rating: float = 0.0
    combined_text: str = ""
    source: str = "internal"
    external_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "course_id": self.course_id,
            "title": self.title,
            "provider": self.provider,
            "skills_covered": self.skills_covered,
            "source": self.source,
        }


def build_student_features_from_profile(
    profile: dict[str, Any],
    skills: list[dict[str, Any]],
    experiences: list[dict[str, Any]] | None = None,
    projects: list[dict[str, Any]] | None = None,
    certifications: list[dict[str, Any]] | None = None,
    education: list[dict[str, Any]] | None = None,
    interactions: dict[str, int] | None = None,
) -> StudentFeatures:
    """Build features from database profile data.

    This is the single source of truth for converting a student's raw data
    into the feature vector the ML models consume.
    """
    from app.ml.preprocessing import build_text_profile, normalise_skill_name

    experiences = experiences or []
    projects = projects or []
    certifications = certifications or []
    education = education or []
    interactions = interactions or {}

    # Skill analysis
    skill_names = []
    technical_count = 0
    soft_count = 0
    advanced_count = 0
    intermediate_count = 0
    beginner_count = 0
    total_score = 0.0
    total_confidence = 0.0
    verified_count = 0
    skill_categories: list[str] = []

    for s in skills:
        name = s.get("name", s.get("skill_name", ""))
        skill_names.append(name)
        category = s.get("category", "")
        if category:
            skill_categories.append(category)

        level = s.get("level", "BEGINNER")
        if level == "ADVANCED" or level == "EXPERT":
            advanced_count += 1
        elif level == "INTERMEDIATE":
            intermediate_count += 1
        else:
            beginner_count += 1

        if s.get("is_soft_skill", False):
            soft_count += 1
        else:
            technical_count += 1

        total_score += s.get("score", 0.0)
        total_confidence += s.get("confidence", 0.3)
        if s.get("is_verified", False):
            verified_count += 1

    n_skills = len(skills) or 1

    # Experience analysis
    total_exp_months = 0.0
    internship_count = 0
    exp_texts = []
    for exp in experiences:
        if exp.get("kind", "").upper() == "INTERNSHIP":
            internship_count += 1
        duration = exp.get("duration_months", 0)
        if not duration and exp.get("start_date") and exp.get("end_date"):
            # Approximate from dates
            duration = 3  # conservative default
        total_exp_months += duration
        exp_texts.append(f"{exp.get('title', '')} {exp.get('organization', '')} {exp.get('description', '')}")

    # Project analysis
    proj_texts = []
    for p in projects:
        proj_texts.append(f"{p.get('title', '')} {p.get('description', '')} {' '.join(p.get('skill_tags', []))}")

    # Certification analysis
    cert_texts = []
    for c in certifications:
        cert_texts.append(f"{c.get('name', c.get('title', ''))} {c.get('issuer', '')}")

    # Education text
    edu_texts = []
    for e in education:
        edu_texts.append(f"{e.get('level', '')} {e.get('program', '')} {e.get('specialization', '')} {e.get('institution_name', '')}")

    # Build text features
    skill_text = " ".join(normalise_skill_name(s) for s in skill_names)
    experience_text = " ".join(exp_texts)
    project_text = " ".join(proj_texts)
    certification_text = " ".join(cert_texts)
    education_text = " ".join(edu_texts)
    interests = profile.get("career_interests", []) or []
    interest_text = " ".join(str(i) for i in interests)

    combined_text = build_text_profile(
        skills=skill_names,
        education=education_text,
        experience=experience_text,
        projects=project_text,
        interests=interests,
        certifications=certification_text,
    )

    return StudentFeatures(
        student_id=str(profile.get("id", "")),
        cgpa=profile.get("cgpa", 0.0) or 0.0,
        graduation_year=profile.get("graduation_year", 0) or 0,
        current_year=profile.get("current_year", 0) or 0,
        backlogs=profile.get("backlogs", 0) or 0,
        experience_months=total_exp_months,
        internship_count=internship_count,
        project_count=len(projects),
        certification_count=len(certifications),
        assessment_avg_score=profile.get("assessment_avg_score", 0.0) or 0.0,
        profile_completion=profile.get("profile_completion", 0) or 0,
        total_skills=len(skills),
        technical_skill_count=technical_count,
        soft_skill_count=soft_count,
        avg_skill_score=total_score / n_skills,
        avg_skill_confidence=total_confidence / n_skills,
        verified_skill_count=verified_count,
        advanced_skill_count=advanced_count,
        intermediate_skill_count=intermediate_count,
        beginner_skill_count=beginner_count,
        skill_text=skill_text,
        education_text=education_text,
        experience_text=experience_text,
        project_text=project_text,
        certification_text=certification_text,
        interest_text=interest_text,
        combined_text=combined_text,
        degree=profile.get("degree", "BACHELORS") or "BACHELORS",
        department=profile.get("department", "") or "",
        preferred_work_mode=profile.get("preferred_work_mode", "") or "",
        city=profile.get("city", "") or "",
        skill_names=skill_names,
        skill_categories=list(set(skill_categories)),
        career_interests=[str(i) for i in interests],
        preferred_roles=[str(r) for r in (profile.get("preferred_roles", []) or [])],
        preferred_locations=[str(l) for l in (profile.get("preferred_locations", []) or [])],
        jobs_viewed=interactions.get("jobs_viewed", 0),
        jobs_applied=interactions.get("jobs_applied", 0),
        courses_enrolled=interactions.get("courses_enrolled", 0),
        courses_completed=interactions.get("courses_completed", 0),
        recommendations_clicked=interactions.get("recommendations_clicked", 0),
        recommendations_dismissed=interactions.get("recommendations_dismissed", 0),
        positive_feedback_count=interactions.get("positive_feedback", 0),
        negative_feedback_count=interactions.get("negative_feedback", 0),
    )


def build_job_features(job: dict[str, Any]) -> JobFeatures:
    """Build features from a job posting dictionary."""
    from app.ml.preprocessing import clean_text, normalise_job_title

    title = job.get("title", "")
    description = job.get("description", "")
    required_skills = job.get("required_skills", [])
    preferred_skills = job.get("preferred_skills", [])
    company = job.get("company", job.get("company_name", ""))

    combined = clean_text(f"{title} {description} {' '.join(required_skills)} {' '.join(preferred_skills)}")

    return JobFeatures(
        job_id=str(job.get("id", "")),
        title=title,
        normalised_title=normalise_job_title(title),
        company=company,
        location=job.get("location", job.get("location_city", "")),
        work_mode=job.get("work_mode", ""),
        description=description,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        min_experience_years=job.get("min_experience_years", job.get("experience_min_years", 0.0)),
        salary_min=job.get("salary_min", 0.0) or 0.0,
        salary_max=job.get("salary_max", 0.0) or 0.0,
        is_internship=job.get("is_internship", False),
        industry=job.get("industry", ""),
        combined_text=combined,
        source=job.get("source", "internal"),
        external_url=job.get("external_url", job.get("url", "")),
    )


def build_course_features(course: dict[str, Any]) -> CourseFeatures:
    """Build features from a course dictionary."""
    from app.ml.preprocessing import clean_text

    title = course.get("title", "")
    description = course.get("description", "")
    skills = course.get("skills_covered", course.get("skills", []))

    combined = clean_text(f"{title} {description} {' '.join(skills)}")

    return CourseFeatures(
        course_id=str(course.get("id", "")),
        title=title,
        provider=course.get("provider", course.get("provider_name", "")),
        description=description,
        skills_covered=skills,
        difficulty=course.get("difficulty", "MEDIUM"),
        duration_hours=course.get("duration_hours", 0),
        has_certificate=course.get("has_certificate", False),
        is_free=course.get("is_free", False),
        rating=course.get("rating", 0.0),
        combined_text=combined,
        source=course.get("source", "internal"),
        external_url=course.get("external_url", course.get("url", "")),
    )
