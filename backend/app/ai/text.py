"""Deterministic text understanding: skill extraction and resume/JD parsing.

No model required. Skill detection is alias-aware exact matching against the
platform taxonomy, which is precise (no hallucinated skills) and fully
explainable - every hit points at the phrase that produced it.
"""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

# Sections a resume is normally divided into.
SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "education": re.compile(r"^\s*(education|academic|academics|qualifications?)\b", re.I),
    "experience": re.compile(
        r"^\s*(experience|work experience|employment|internships?|professional experience)\b", re.I
    ),
    "projects": re.compile(r"^\s*(projects?|personal projects?|academic projects?)\b", re.I),
    "skills": re.compile(r"^\s*(skills?|technical skills?|competencies|technologies)\b", re.I),
    "certifications": re.compile(
        r"^\s*(certifications?|certificates?|licenses?|courses?)\b", re.I
    ),
    "achievements": re.compile(
        r"^\s*(achievements?|awards?|honou?rs|accomplishments?)\b", re.I
    ),
    "summary": re.compile(r"^\s*(summary|objective|profile|about)\b", re.I),
}

DEGREE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("DOCTORATE", re.compile(r"\b(ph\.?d|doctorate|doctoral)\b", re.I)),
    ("MASTERS", re.compile(r"\b(m\.?tech|m\.?e\b|m\.?sc|mca|mba|master'?s?|post.?graduat)\b", re.I)),
    ("BACHELORS", re.compile(r"\b(b\.?tech|b\.?e\b|b\.?sc|bca|bba|b\.?com|bachelor'?s?|under.?graduat)\b", re.I)),
    ("DIPLOMA", re.compile(r"\bdiploma\b", re.I)),
    ("HIGHER_SECONDARY", re.compile(r"\b(12th|higher secondary|intermediate|hsc|senior secondary)\b", re.I)),
    ("SECONDARY", re.compile(r"\b(10th|secondary|ssc|matriculation)\b", re.I)),
]

YEAR_RANGE = re.compile(r"\b(19|20)\d{2}\b")
CGPA_PATTERN = re.compile(r"\b(?:cgpa|gpa)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\b", re.I)
PERCENT_PATTERN = re.compile(r"\b([0-9]{1,3}(?:\.[0-9]+)?)\s*%", re.I)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[\s-]?)?\b\d{10}\b")
URL_PATTERN = re.compile(r"https?://[^\s,;)]+")

# Phrases that indicate the writer only *wants* to learn something. Checked
# against the clause immediately preceding a skill, not the whole line, so
# "Python, Docker. Currently learning Kubernetes" only flags Kubernetes.
ASPIRATIONAL = re.compile(
    r"\b(currently learning|want to learn|wants? to learn|interested in learning|"
    r"learning|beginner in|exploring|familiar with basics of|planning to learn)\b",
    re.I,
)
# Characters that end a clause, bounding the aspirational look-behind.
CLAUSE_BOUNDARY = re.compile(r"[.;\n|•]")
ASPIRATIONAL_LOOKBEHIND = 45


def _is_aspirational(haystack: str, match_start: int) -> bool:
    """True when the clause directly before a skill marks it as not-yet-held."""
    window_start = max(0, match_start - ASPIRATIONAL_LOOKBEHIND)
    window = haystack[window_start:match_start]
    # Only consider text after the most recent clause boundary.
    boundaries = list(CLAUSE_BOUNDARY.finditer(window))
    if boundaries:
        window = window[boundaries[-1].end():]
    return bool(ASPIRATIONAL.search(window))

# Years-of-experience phrases, e.g. "3+ years of experience".
EXPERIENCE_YEARS = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b[^.]{0,30}?experience", re.I
)


@dataclass(slots=True)
class SkillHit:
    skill_id: str
    skill_name: str
    matched_term: str
    occurrences: int
    contexts: list[str] = field(default_factory=list)
    is_aspirational: bool = False


@dataclass(slots=True)
class ParsedDocument:
    raw_text: str
    sections: dict[str, str] = field(default_factory=dict)
    skills: list[SkillHit] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)
    projects: list[dict] = field(default_factory=list)
    certifications: list[dict] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    experience_years: float | None = None
    word_count: int = 0


def normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def split_sections(text: str) -> dict[str, str]:
    """Split a resume into labelled sections; unlabelled text goes to 'header'."""
    lines = text.split("\n")
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in lines:
        stripped = line.strip()
        matched = None
        if stripped and len(stripped) <= 60:
            for name, pattern in SECTION_PATTERNS.items():
                if pattern.match(stripped):
                    matched = name
                    break
        if matched:
            current = matched
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {name: "\n".join(body).strip() for name, body in sections.items() if body}


def _term_pattern(term: str) -> re.Pattern[str]:
    """Word-boundary pattern tolerant of punctuation inside names (C++, .NET, Node.js)."""
    escaped = re.escape(term.strip())
    escaped = escaped.replace(r"\ ", r"[\s\-_]+")
    left = r"(?<![\w+#.])" if term[0].isalnum() else r"(?<![\w])"
    right = r"(?![\w+#])" if term[-1].isalnum() else r"(?![\w])"
    return re.compile(left + escaped + right, re.I)


def extract_skills(
    text: str, vocabulary: Iterable[tuple[str, str, list[str]]]
) -> list[SkillHit]:
    """Find taxonomy skills in free text.

    ``vocabulary`` is ``(skill_id, canonical_name, aliases)``. Matching is exact
    and alias-aware: a skill is only reported when its name or one of its
    recorded aliases actually appears, so nothing is invented.
    """
    if not text:
        return []
    haystack = normalise(text)
    hits: list[SkillHit] = []

    for skill_id, name, aliases in vocabulary:
        terms = [name, *(aliases or [])]
        best_term, total, contexts = None, 0, []
        aspirational_hits = solid_hits = 0
        for term in terms:
            if not term or len(term) < 2:
                continue
            pattern = _term_pattern(term)
            found = list(pattern.finditer(haystack))
            if found:
                total += len(found)
                best_term = best_term or term
                for m in found:
                    if _is_aspirational(haystack, m.start()):
                        aspirational_hits += 1
                    else:
                        solid_hits += 1
                for m in found[:2]:
                    start = max(0, m.start() - 60)
                    end = min(len(haystack), m.end() + 60)
                    contexts.append(haystack[start:end].replace("\n", " ").strip())
        if total and best_term:
            # Only aspirational when *every* mention was aspirational.
            aspirational = aspirational_hits > 0 and solid_hits == 0
            hits.append(
                SkillHit(
                    skill_id=skill_id, skill_name=name, matched_term=best_term,
                    occurrences=total, contexts=contexts[:2],
                    is_aspirational=aspirational,
                )
            )

    hits.sort(key=lambda h: (-h.occurrences, h.skill_name))
    return hits


def extract_education(text: str) -> list[dict]:
    entries: list[dict] = []
    # Split on blank lines only: a "CGPA: 8.4" continuation line must stay
    # attached to the degree line above it.
    for block in [b for b in re.split(r"\n\s*\n", text) if b.strip()]:
        level = next((name for name, p in DEGREE_PATTERNS if p.search(block)), None)
        if not level:
            continue
        years = [int(y.group()) for y in YEAR_RANGE.finditer(block)]
        cgpa = CGPA_PATTERN.search(block)
        percent = PERCENT_PATTERN.search(block)
        first_line = next((line.strip() for line in block.split("\n") if line.strip()), "")
        entries.append(
            {
                "level": level,
                "text": first_line[:200],
                "start_year": min(years) if years else None,
                "end_year": max(years) if years else None,
                "score_value": float(cgpa.group(1)) if cgpa
                else (float(percent.group(1)) if percent else None),
                "score_type": "CGPA" if cgpa else ("PERCENTAGE" if percent else None),
            }
        )
    return entries[:6]


def _blocks(text: str) -> list[str]:
    return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


def extract_experience(text: str) -> list[dict]:
    entries: list[dict] = []
    for block in _blocks(text):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        years = [int(y.group()) for y in YEAR_RANGE.finditer(block)]
        title = lines[0][:180]
        organization = lines[1][:180] if len(lines) > 1 else ""
        entries.append(
            {
                "title": title,
                "organization": organization,
                "description": " ".join(lines[2:])[:600],
                "start_year": min(years) if years else None,
                "end_year": max(years) if years else None,
                "is_current": bool(re.search(r"\b(present|current|ongoing)\b", block, re.I)),
            }
        )
    return entries[:8]


def extract_projects(text: str) -> list[dict]:
    entries: list[dict] = []
    for block in _blocks(text):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        urls = URL_PATTERN.findall(block)
        entries.append(
            {
                "title": lines[0][:180],
                "description": " ".join(lines[1:])[:600],
                "url": urls[0] if urls else None,
            }
        )
    return entries[:8]


def extract_certifications(text: str) -> list[dict]:
    entries: list[dict] = []
    for line in [raw.strip() for raw in text.split("\n") if raw.strip()]:
        if len(line) < 4:
            continue
        years = [int(y.group()) for y in YEAR_RANGE.finditer(line)]
        issuer = None
        if " - " in line:
            _, _, issuer = line.partition(" - ")
        elif " by " in line.lower():
            issuer = line.lower().split(" by ", 1)[1]
        entries.append(
            {
                "name": line[:200],
                "issuer": (issuer or "").strip()[:180] or None,
                "year": years[0] if years else None,
            }
        )
    return entries[:12]


def parse_document(
    text: str, vocabulary: Iterable[tuple[str, str, list[str]]]
) -> ParsedDocument:
    """Full deterministic parse of a resume-like document."""
    text = normalise(text)
    sections = split_sections(text)
    doc = ParsedDocument(raw_text=text, sections=sections, word_count=len(text.split()))
    doc.skills = extract_skills(text, vocabulary)
    doc.education = extract_education(sections.get("education", "") or text)
    doc.experience = extract_experience(sections.get("experience", ""))
    doc.projects = extract_projects(sections.get("projects", ""))
    doc.certifications = extract_certifications(sections.get("certifications", ""))
    doc.emails = EMAIL_PATTERN.findall(text)[:3]
    doc.phones = PHONE_PATTERN.findall(text)[:3]
    doc.urls = URL_PATTERN.findall(text)[:8]
    years = EXPERIENCE_YEARS.search(text)
    doc.experience_years = float(years.group(1)) if years else None
    return doc


def keyword_frequencies(text: str, top: int = 20) -> list[tuple[str, int]]:
    """Simple term frequency, used for job-description keyword surfacing."""
    stop = {
        "the", "and", "for", "with", "you", "our", "will", "are", "have", "this",
        "that", "from", "your", "who", "all", "can", "has", "not", "but", "any",
        "job", "role", "work", "team", "using", "use", "well", "must", "should",
        "good", "strong", "plus", "years", "year", "experience", "knowledge",
    }
    words = re.findall(r"[a-zA-Z][a-zA-Z+#.\-]{2,}", text.lower())
    counts = Counter(w for w in words if w not in stop and len(w) > 2)
    return counts.most_common(top)
