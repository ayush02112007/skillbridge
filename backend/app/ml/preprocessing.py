"""Text preprocessing utilities for ML pipeline.

Cleans, normalises and tokenises text from resumes, job descriptions, and
course descriptions for feature engineering. Works alongside the existing
deterministic text module in app.ai.text without replacing it.
"""
from __future__ import annotations

import re
from collections import Counter


# Common stop words for career/tech context
STOP_WORDS = frozenset({
    "the", "and", "for", "with", "you", "our", "will", "are", "have", "this",
    "that", "from", "your", "who", "all", "can", "has", "not", "but", "any",
    "job", "role", "work", "team", "using", "use", "well", "must", "should",
    "good", "strong", "plus", "years", "year", "experience", "knowledge",
    "able", "also", "new", "one", "two", "may", "etc", "including", "various",
    "working", "about", "per", "such", "like", "would", "could", "need",
    "required", "preferred", "looking", "join", "company", "opportunity",
    "responsibilities", "requirements", "qualifications", "description",
})


def clean_text(text: str) -> str:
    """Clean text for ML processing."""
    if not text:
        return ""
    # Normalise whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove special chars but keep meaningful punctuation
    text = re.sub(r"[^\w\s.+#/\-]", " ", text)
    # Collapse whitespace again
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def tokenize(text: str) -> list[str]:
    """Tokenise text into meaningful terms."""
    cleaned = clean_text(text)
    tokens = re.findall(r"[a-zA-Z][a-zA-Z+#.\-]{1,}", cleaned)
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


def extract_keywords(text: str, top_n: int = 50) -> list[str]:
    """Extract top keywords from text."""
    tokens = tokenize(text)
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(top_n)]


def normalise_skill_name(name: str) -> str:
    """Normalise a skill name for matching."""
    name = name.strip().lower()
    # Common normalisations
    replacements = {
        "javascript": "javascript",
        "js": "javascript",
        "node.js": "nodejs",
        "node": "nodejs",
        "react.js": "react",
        "reactjs": "react",
        "vue.js": "vue",
        "vuejs": "vue",
        "angular.js": "angular",
        "angularjs": "angular",
        "next.js": "nextjs",
        "nextjs": "nextjs",
        "express.js": "express",
        "expressjs": "express",
        "c++": "cpp",
        "c#": "csharp",
        "c sharp": "csharp",
        "dot net": "dotnet",
        ".net": "dotnet",
        "machine learning": "ml",
        "artificial intelligence": "ai",
        "deep learning": "dl",
        "natural language processing": "nlp",
        "amazon web services": "aws",
        "google cloud platform": "gcp",
        "microsoft azure": "azure",
        "ci/cd": "cicd",
        "ci cd": "cicd",
        "devops": "devops",
        "dev ops": "devops",
        "sql server": "mssql",
        "mongo db": "mongodb",
        "postgre sql": "postgresql",
        "postgres": "postgresql",
        "my sql": "mysql",
        "scikit-learn": "sklearn",
        "scikit learn": "sklearn",
        "tensor flow": "tensorflow",
        "py torch": "pytorch",
    }
    return replacements.get(name, re.sub(r"[^a-z0-9+#]", "", name))


def normalise_job_title(title: str) -> str:
    """Normalise a job title for matching."""
    title = title.strip().lower()
    # Remove seniority prefixes for base role matching
    title = re.sub(r"^(junior|senior|lead|principal|staff|intern|entry.level|mid.level)\s+", "", title)
    # Remove common suffixes
    title = re.sub(r"\s+(i{1,3}|iv|v|[1-5])$", "", title)
    # Normalise common titles
    title = re.sub(r"\s+", " ", title).strip()
    return title


def build_text_profile(
    skills: list[str],
    education: str = "",
    experience: str = "",
    projects: str = "",
    interests: list[str] | None = None,
    certifications: str = "",
) -> str:
    """Combine all text signals into a single profile document for TF-IDF."""
    parts = []
    if skills:
        # Repeat skills to boost their weight
        parts.append(" ".join(skills) + " " + " ".join(skills))
    if education:
        parts.append(education)
    if experience:
        parts.append(experience)
    if projects:
        parts.append(projects)
    if interests:
        parts.append(" ".join(interests))
    if certifications:
        parts.append(certifications)
    return clean_text(" ".join(parts))
