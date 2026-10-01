"""Training dataset generation and management.

Generates synthetic but realistic training data from:
1. Real job role / skill taxonomy data from SkillBridge database
2. Publicly available career data patterns
3. Realistic student profile variations

IMPORTANT: All synthetic data is clearly labelled as synthetic.
No synthetic label is ever presented as real user behaviour.

Label types documented:
- career_match: SYNTHETIC - derived from skill/role compatibility rules
- job_relevance: SYNTHETIC - derived from skill overlap + role alignment
- course_relevance: SYNTHETIC - derived from skill coverage + difficulty match
- role_readiness: SYNTHETIC - derived from skill coverage ratio
"""
from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.ml.config import ml_config
from app.ml.preprocessing import normalise_skill_name

log = logging.getLogger("ml.dataset")

# ── Career taxonomy: real tech career data ──────────────────────────────────

CAREER_ROLES = {
    "Backend Developer": {
        "family": "Engineering",
        "core_skills": ["python", "java", "nodejs", "sql", "postgresql", "mongodb",
                        "rest-api", "docker", "git", "linux"],
        "preferred_skills": ["redis", "kafka", "kubernetes", "aws", "cicd",
                             "microservices", "graphql", "elasticsearch"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 0,
    },
    "Frontend Developer": {
        "family": "Engineering",
        "core_skills": ["javascript", "html", "css", "react", "typescript",
                        "git", "rest-api", "responsive-design"],
        "preferred_skills": ["nextjs", "vue", "angular", "webpack", "tailwindcss",
                             "figma", "jest", "cypress"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 0,
    },
    "Full Stack Developer": {
        "family": "Engineering",
        "core_skills": ["javascript", "python", "html", "css", "react", "nodejs",
                        "sql", "git", "rest-api", "docker"],
        "preferred_skills": ["typescript", "mongodb", "postgresql", "aws",
                             "nextjs", "graphql", "redis", "cicd"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 0,
    },
    "Data Scientist": {
        "family": "Data",
        "core_skills": ["python", "ml", "statistics", "pandas", "numpy",
                        "sklearn", "sql", "data-visualization", "jupyter"],
        "preferred_skills": ["tensorflow", "pytorch", "nlp", "deep-learning",
                             "spark", "aws", "docker", "tableau", "r"],
        "education": ["BACHELORS", "MASTERS", "DOCTORATE"],
        "min_experience": 0,
    },
    "Data Analyst": {
        "family": "Data",
        "core_skills": ["sql", "python", "excel", "data-visualization", "statistics",
                        "pandas", "tableau", "power-bi"],
        "preferred_skills": ["r", "jupyter", "aws", "git", "ml", "etl",
                             "data-warehousing", "looker"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 0,
    },
    "Machine Learning Engineer": {
        "family": "Data",
        "core_skills": ["python", "ml", "tensorflow", "pytorch", "sklearn",
                        "docker", "git", "linux", "sql", "statistics"],
        "preferred_skills": ["kubernetes", "aws", "mlops", "spark", "nlp",
                             "deep-learning", "cicd", "data-engineering"],
        "education": ["BACHELORS", "MASTERS", "DOCTORATE"],
        "min_experience": 0,
    },
    "DevOps Engineer": {
        "family": "Engineering",
        "core_skills": ["linux", "docker", "kubernetes", "cicd", "aws",
                        "terraform", "git", "bash", "python", "monitoring"],
        "preferred_skills": ["ansible", "jenkins", "prometheus", "grafana",
                             "gcp", "azure", "helm", "networking"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 0,
    },
    "Cloud Engineer": {
        "family": "Engineering",
        "core_skills": ["aws", "docker", "kubernetes", "linux", "terraform",
                        "networking", "cicd", "python", "bash", "security"],
        "preferred_skills": ["gcp", "azure", "ansible", "serverless",
                             "microservices", "monitoring", "cost-optimization"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 0,
    },
    "Mobile Developer": {
        "family": "Engineering",
        "core_skills": ["react-native", "flutter", "dart", "javascript",
                        "mobile-development", "rest-api", "git", "ui-design"],
        "preferred_skills": ["kotlin", "swift", "firebase", "graphql",
                             "app-store", "cicd", "testing"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 0,
    },
    "Cybersecurity Analyst": {
        "family": "Security",
        "core_skills": ["networking", "linux", "security", "python", "firewalls",
                        "penetration-testing", "siem", "incident-response"],
        "preferred_skills": ["aws-security", "compliance", "cryptography",
                             "forensics", "malware-analysis", "bash"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 0,
    },
    "Data Engineer": {
        "family": "Data",
        "core_skills": ["python", "sql", "spark", "etl", "data-warehousing",
                        "aws", "docker", "airflow", "kafka"],
        "preferred_skills": ["dbt", "snowflake", "databricks", "kubernetes",
                             "streaming", "data-modeling", "cicd"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 0,
    },
    "QA Engineer": {
        "family": "Engineering",
        "core_skills": ["testing", "selenium", "python", "java", "git",
                        "jira", "rest-api", "automation", "sql"],
        "preferred_skills": ["cypress", "jest", "cicd", "docker", "performance-testing",
                             "api-testing", "mobile-testing"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 0,
    },
    "UI/UX Designer": {
        "family": "Design",
        "core_skills": ["figma", "ui-design", "ux-research", "prototyping",
                        "wireframing", "user-testing", "design-systems"],
        "preferred_skills": ["sketch", "adobe-xd", "html", "css", "javascript",
                             "accessibility", "analytics"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 0,
    },
    "Product Manager": {
        "family": "Management",
        "core_skills": ["product-management", "agile", "data-analysis", "sql",
                        "user-research", "roadmapping", "stakeholder-management"],
        "preferred_skills": ["jira", "analytics", "a-b-testing", "technical-writing",
                             "leadership", "presentation"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 6,
    },
    "Blockchain Developer": {
        "family": "Engineering",
        "core_skills": ["solidity", "ethereum", "javascript", "nodejs",
                        "web3", "smart-contracts", "cryptography"],
        "preferred_skills": ["rust", "defi", "nft", "typescript", "react",
                             "docker", "security"],
        "education": ["BACHELORS", "MASTERS"],
        "min_experience": 0,
    },
}

# Courses that cover specific skills
COURSE_TEMPLATES = [
    {"title": "Python for Data Science and ML", "skills": ["python", "ml", "pandas", "numpy", "sklearn"],
     "difficulty": "MEDIUM", "hours": 40, "provider": "Coursera"},
    {"title": "Web Development with React", "skills": ["react", "javascript", "html", "css", "nodejs"],
     "difficulty": "MEDIUM", "hours": 35, "provider": "Udemy"},
    {"title": "Docker and Kubernetes Masterclass", "skills": ["docker", "kubernetes", "cicd", "linux"],
     "difficulty": "ADVANCED", "hours": 25, "provider": "Udemy"},
    {"title": "AWS Cloud Practitioner", "skills": ["aws", "cloud", "networking", "security"],
     "difficulty": "EASY", "hours": 20, "provider": "Coursera"},
    {"title": "Machine Learning Specialization", "skills": ["ml", "tensorflow", "deep-learning", "statistics"],
     "difficulty": "ADVANCED", "hours": 80, "provider": "Coursera"},
    {"title": "SQL for Data Analysis", "skills": ["sql", "data-analysis", "postgresql"],
     "difficulty": "EASY", "hours": 15, "provider": "edX"},
    {"title": "FastAPI Backend Development", "skills": ["python", "fastapi", "rest-api", "postgresql", "docker"],
     "difficulty": "MEDIUM", "hours": 30, "provider": "Udemy"},
    {"title": "TypeScript Complete Course", "skills": ["typescript", "javascript"],
     "difficulty": "MEDIUM", "hours": 20, "provider": "Udemy"},
    {"title": "DevOps CI/CD Pipeline", "skills": ["cicd", "jenkins", "docker", "git", "linux"],
     "difficulty": "ADVANCED", "hours": 30, "provider": "Coursera"},
    {"title": "Data Structures and Algorithms", "skills": ["algorithms", "data-structures", "python", "java"],
     "difficulty": "MEDIUM", "hours": 50, "provider": "Coursera"},
    {"title": "React Native Mobile Development", "skills": ["react-native", "javascript", "mobile-development"],
     "difficulty": "MEDIUM", "hours": 30, "provider": "Udemy"},
    {"title": "Cybersecurity Fundamentals", "skills": ["security", "networking", "linux", "penetration-testing"],
     "difficulty": "MEDIUM", "hours": 35, "provider": "edX"},
    {"title": "MongoDB Complete Guide", "skills": ["mongodb", "nosql", "nodejs"],
     "difficulty": "MEDIUM", "hours": 20, "provider": "Udemy"},
    {"title": "Tableau Data Visualization", "skills": ["tableau", "data-visualization", "data-analysis"],
     "difficulty": "EASY", "hours": 20, "provider": "Coursera"},
    {"title": "Redis for Backend Engineers", "skills": ["redis", "caching", "python", "nodejs"],
     "difficulty": "MEDIUM", "hours": 15, "provider": "Udemy"},
    {"title": "Kubernetes in Production", "skills": ["kubernetes", "docker", "aws", "monitoring", "helm"],
     "difficulty": "ADVANCED", "hours": 40, "provider": "edX"},
    {"title": "NLP with Python", "skills": ["nlp", "python", "ml", "deep-learning"],
     "difficulty": "ADVANCED", "hours": 45, "provider": "Coursera"},
    {"title": "GraphQL API Design", "skills": ["graphql", "nodejs", "rest-api", "typescript"],
     "difficulty": "MEDIUM", "hours": 20, "provider": "Udemy"},
    {"title": "Apache Spark Big Data", "skills": ["spark", "python", "data-engineering", "sql"],
     "difficulty": "ADVANCED", "hours": 35, "provider": "edX"},
    {"title": "Flutter Mobile App Development", "skills": ["flutter", "dart", "mobile-development"],
     "difficulty": "MEDIUM", "hours": 30, "provider": "Udemy"},
]

ALL_SKILLS = sorted(set(
    skill
    for role_data in CAREER_ROLES.values()
    for skill in role_data["core_skills"] + role_data["preferred_skills"]
))


def _random_student_profile(rng: random.Random) -> dict[str, Any]:
    """Generate a realistic synthetic student profile."""
    # Pick 1-3 career interests from role families
    families = list(set(r["family"] for r in CAREER_ROLES.values()))
    n_interests = rng.randint(1, 2)
    interests = rng.sample(families, min(n_interests, len(families)))

    # Pick a primary target role
    target_role = rng.choice(list(CAREER_ROLES.keys()))
    role_data = CAREER_ROLES[target_role]

    # Generate skills: some from target role, some random
    n_core = rng.randint(2, len(role_data["core_skills"]))
    n_preferred = rng.randint(0, min(3, len(role_data["preferred_skills"])))
    n_random = rng.randint(0, 4)

    skills = list(set(
        rng.sample(role_data["core_skills"], n_core)
        + rng.sample(role_data["preferred_skills"], min(n_preferred, len(role_data["preferred_skills"])))
        + rng.sample(ALL_SKILLS, min(n_random, len(ALL_SKILLS)))
    ))

    levels = ["BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"]
    skill_data = []
    for s in skills:
        level = rng.choices(levels, weights=[15, 40, 35, 10])[0]
        score = {"BEGINNER": rng.uniform(10, 35), "INTERMEDIATE": rng.uniform(35, 65),
                 "ADVANCED": rng.uniform(65, 85), "EXPERT": rng.uniform(85, 98)}[level]
        skill_data.append({
            "name": s, "level": level, "score": round(score, 1),
            "confidence": round(rng.uniform(0.3, 0.95), 2),
            "is_verified": rng.random() < 0.2,
            "is_soft_skill": s in ("leadership", "communication", "teamwork", "presentation"),
        })

    cgpa = round(rng.uniform(5.5, 9.8), 1)
    grad_year = rng.choice([2024, 2025, 2026, 2027])
    current_year = max(1, min(4, 2026 - grad_year + 4))

    n_exp = rng.choices([0, 1, 2, 3], weights=[30, 35, 25, 10])[0]
    experiences = []
    for _ in range(n_exp):
        experiences.append({
            "title": rng.choice(["Software Intern", "Data Intern", "Web Developer Intern",
                                 "ML Intern", "Backend Intern", "Frontend Intern"]),
            "organization": rng.choice(["TechCorp", "DataInc", "StartupXYZ", "BigTech",
                                        "AILabs", "CloudFirst", "WebStudio"]),
            "kind": rng.choice(["INTERNSHIP", "JOB"]),
            "duration_months": rng.randint(1, 6),
            "description": f"Worked on {rng.choice(skills)} projects",
        })

    n_proj = rng.randint(0, 4)
    projects = []
    for _ in range(n_proj):
        proj_skills = rng.sample(skills, min(rng.randint(1, 3), len(skills)))
        projects.append({
            "title": f"{rng.choice(['E-commerce', 'Chat', 'ML', 'API', 'Dashboard', 'Mobile'])} {rng.choice(['App', 'Platform', 'System', 'Tool'])}",
            "description": f"Built using {', '.join(proj_skills[:3])}",
            "skill_tags": proj_skills,
        })

    n_certs = rng.choices([0, 1, 2], weights=[40, 40, 20])[0]
    certifications = []
    for _ in range(n_certs):
        certifications.append({
            "name": rng.choice([
                "AWS Cloud Practitioner", "Google Data Analytics", "Meta Frontend Developer",
                "IBM Data Science", "Microsoft Azure Fundamentals", "Docker Certified",
            ]),
            "issuer": rng.choice(["AWS", "Google", "Meta", "IBM", "Microsoft", "Docker"]),
        })

    return {
        "id": str(rng.getrandbits(128)),
        "cgpa": cgpa,
        "graduation_year": grad_year,
        "current_year": current_year,
        "backlogs": rng.choices([0, 1, 2], weights=[80, 15, 5])[0],
        "degree": rng.choices(["BACHELORS", "MASTERS"], weights=[80, 20])[0],
        "department": rng.choice(["Computer Science", "IT", "ECE", "Data Science", "AI/ML"]),
        "city": rng.choice(["Mumbai", "Bangalore", "Delhi", "Hyderabad", "Pune", "Chennai"]),
        "career_interests": interests,
        "preferred_roles": [target_role],
        "preferred_locations": rng.sample(["Mumbai", "Bangalore", "Delhi", "Hyderabad", "Pune",
                                            "Chennai", "Remote"], rng.randint(1, 3)),
        "preferred_work_mode": rng.choice(["REMOTE", "ONSITE", "HYBRID"]),
        "profile_completion": rng.randint(40, 100),
        "target_role": target_role,
        "skills_data": skill_data,
        "experiences": experiences,
        "projects": projects,
        "certifications": certifications,
    }


def _compute_career_match(student: dict, role_name: str) -> float:
    """Compute a realistic career match score.

    LABEL TYPE: SYNTHETIC — derived from skill coverage, not real user data.
    """
    role_data = CAREER_ROLES.get(role_name, {})
    if not role_data:
        return 0.0

    student_skills = {s["name"] for s in student.get("skills_data", [])}
    core = set(role_data["core_skills"])
    preferred = set(role_data["preferred_skills"])

    core_match = len(student_skills & core) / max(1, len(core))
    pref_match = len(student_skills & preferred) / max(1, len(preferred))

    # Skill level bonus
    level_bonus = 0.0
    for s in student.get("skills_data", []):
        if s["name"] in core:
            if s["level"] in ("ADVANCED", "EXPERT"):
                level_bonus += 0.03
            elif s["level"] == "INTERMEDIATE":
                level_bonus += 0.01

    # Experience bonus
    exp_bonus = min(0.1, len(student.get("experiences", [])) * 0.03)

    # Project bonus
    proj_bonus = min(0.05, len(student.get("projects", [])) * 0.015)

    score = core_match * 0.6 + pref_match * 0.15 + level_bonus + exp_bonus + proj_bonus
    return min(1.0, max(0.0, round(score, 3)))


def generate_career_dataset(n_samples: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Generate career prediction training data.

    Each row: student features + target role → match probability.

    LABEL TYPE: SYNTHETIC — computed from skill/requirement compatibility.
    """
    rng = random.Random(seed)
    records = []

    for _ in range(n_samples):
        student = _random_student_profile(rng)
        # Generate matches against multiple roles
        for role_name in rng.sample(list(CAREER_ROLES.keys()), rng.randint(2, 5)):
            match = _compute_career_match(student, role_name)
            record = {
                "student_id": student["id"],
                "target_role": role_name,
                "n_skills": len(student["skills_data"]),
                "n_core_skills_matched": len(
                    set(s["name"] for s in student["skills_data"])
                    & set(CAREER_ROLES[role_name]["core_skills"])
                ),
                "n_preferred_skills_matched": len(
                    set(s["name"] for s in student["skills_data"])
                    & set(CAREER_ROLES[role_name]["preferred_skills"])
                ),
                "avg_skill_score": np.mean([s["score"] for s in student["skills_data"]]) if student["skills_data"] else 0,
                "avg_skill_confidence": np.mean([s["confidence"] for s in student["skills_data"]]) if student["skills_data"] else 0,
                "n_advanced_skills": sum(1 for s in student["skills_data"] if s["level"] in ("ADVANCED", "EXPERT")),
                "cgpa": student["cgpa"],
                "n_experiences": len(student["experiences"]),
                "n_projects": len(student["projects"]),
                "n_certifications": len(student["certifications"]),
                "profile_completion": student["profile_completion"],
                "is_preferred_role": 1 if role_name in student.get("preferred_roles", []) else 0,
                "match_score": match,
                "match_label": 2 if match >= 0.6 else (1 if match >= 0.3 else 0),
                "skill_text": " ".join(s["name"] for s in student["skills_data"]),
                "role_text": f"{role_name} {' '.join(CAREER_ROLES[role_name]['core_skills'])}",
                "label_type": "SYNTHETIC",
            }
            records.append(record)

    df = pd.DataFrame(records)
    log.info("Generated career dataset: %d records, %d unique students", len(df), df["student_id"].nunique())
    return df


def generate_job_relevance_dataset(n_samples: int = 3000, seed: int = 42) -> pd.DataFrame:
    """Generate job relevance training data.

    LABEL TYPE: SYNTHETIC — derived from skill overlap and role alignment.
    """
    rng = random.Random(seed)
    records = []

    for _ in range(n_samples):
        student = _random_student_profile(rng)
        student_skills = {s["name"] for s in student.get("skills_data", [])}

        # Generate some jobs (good and bad matches)
        for _ in range(rng.randint(2, 4)):
            role_name = rng.choice(list(CAREER_ROLES.keys()))
            role_data = CAREER_ROLES[role_name]

            job_skills = rng.sample(
                role_data["core_skills"],
                rng.randint(3, len(role_data["core_skills"]))
            ) + rng.sample(
                role_data["preferred_skills"],
                rng.randint(0, min(2, len(role_data["preferred_skills"])))
            )

            matched = student_skills & set(job_skills)
            skill_overlap = len(matched) / max(1, len(job_skills))

            # Role alignment bonus
            role_bonus = 0.15 if role_name in student.get("preferred_roles", []) else 0.0

            relevance = min(1.0, skill_overlap * 0.7 + role_bonus + rng.uniform(-0.05, 0.05))
            relevance = max(0.0, round(relevance, 3))

            records.append({
                "skill_overlap": round(skill_overlap, 3),
                "n_matched_skills": len(matched),
                "n_required_skills": len(job_skills),
                "n_student_skills": len(student_skills),
                "is_preferred_role": 1 if role_name in student.get("preferred_roles", []) else 0,
                "cgpa": student["cgpa"],
                "n_experiences": len(student["experiences"]),
                "n_projects": len(student["projects"]),
                "relevance_score": relevance,
                "relevance_label": 2 if relevance >= 0.5 else (1 if relevance >= 0.2 else 0),
                "label_type": "SYNTHETIC",
            })

    return pd.DataFrame(records)


def generate_course_relevance_dataset(n_samples: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Generate course relevance training data.

    LABEL TYPE: SYNTHETIC — derived from skill coverage and difficulty match.
    """
    rng = random.Random(seed)
    records = []

    for _ in range(n_samples):
        student = _random_student_profile(rng)
        student_skills = {s["name"] for s in student.get("skills_data", [])}

        # Pick courses to evaluate
        for course in rng.sample(COURSE_TEMPLATES, rng.randint(2, 5)):
            course_skills = set(course["skills"])
            already_has = student_skills & course_skills
            will_learn = course_skills - student_skills

            # Course is relevant if it teaches missing skills for their target role
            target_role = student.get("target_role", "")
            role_skills = set(CAREER_ROLES.get(target_role, {}).get("core_skills", []))
            role_skills |= set(CAREER_ROLES.get(target_role, {}).get("preferred_skills", []))
            gap_coverage = len(will_learn & role_skills) / max(1, len(role_skills - student_skills))

            difficulty_map = {"EASY": 1, "MEDIUM": 2, "ADVANCED": 3}
            avg_level = np.mean([{"BEGINNER": 1, "INTERMEDIATE": 2, "ADVANCED": 3, "EXPERT": 4}.get(
                s["level"], 1) for s in student["skills_data"]]) if student["skills_data"] else 1

            # Difficulty compatibility
            diff_val = difficulty_map.get(course["difficulty"], 2)
            diff_compat = 1.0 - abs(diff_val - avg_level) * 0.2

            relevance = min(1.0, gap_coverage * 0.5 + diff_compat * 0.2 +
                          (0.15 if will_learn else 0.0) + rng.uniform(-0.05, 0.05))
            relevance = max(0.0, round(relevance, 3))

            records.append({
                "n_skills_to_learn": len(will_learn),
                "n_skills_already_has": len(already_has),
                "gap_coverage": round(gap_coverage, 3),
                "difficulty_compatibility": round(diff_compat, 3),
                "course_duration_hours": course["hours"],
                "is_for_target_role": 1 if will_learn & role_skills else 0,
                "avg_student_level": round(avg_level, 2),
                "relevance_score": relevance,
                "relevance_label": 2 if relevance >= 0.5 else (1 if relevance >= 0.2 else 0),
                "label_type": "SYNTHETIC",
            })

    return pd.DataFrame(records)


def save_datasets(output_dir: Path | None = None, seed: int = 42) -> dict[str, Any]:
    """Generate and save all training datasets."""
    ml_config.ensure_dirs()
    output_dir = output_dir or ml_config.data_dir

    career_df = generate_career_dataset(seed=seed)
    job_df = generate_job_relevance_dataset(seed=seed)
    course_df = generate_course_relevance_dataset(seed=seed)

    # Split into train/val/test
    results = {}
    for name, df in [("career", career_df), ("job_relevance", job_df), ("course_relevance", course_df)]:
        n = len(df)
        train_end = int(n * 0.7)
        val_end = int(n * 0.85)

        shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)

        train = shuffled[:train_end]
        val = shuffled[train_end:val_end]
        test = shuffled[val_end:]

        train.to_csv(output_dir / "training" / f"{name}_train.csv", index=False)
        val.to_csv(output_dir / "validation" / f"{name}_val.csv", index=False)
        test.to_csv(output_dir / "test" / f"{name}_test.csv", index=False)

        results[name] = {
            "total": n,
            "train": len(train),
            "validation": len(val),
            "test": len(test),
        }
        log.info("Saved %s dataset: %d train, %d val, %d test", name, len(train), len(val), len(test))

    # Save metadata
    meta = {
        "label_types": {
            "career_match": "SYNTHETIC - derived from skill/role compatibility, not real user behaviour",
            "job_relevance": "SYNTHETIC - derived from skill overlap + role alignment",
            "course_relevance": "SYNTHETIC - derived from skill coverage + difficulty match",
        },
        "datasets": results,
        "career_roles": list(CAREER_ROLES.keys()),
        "total_skills": len(ALL_SKILLS),
    }
    with open(output_dir / "dataset_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    return results
