"""Explainable candidate <-> opportunity matching.

The score is a weighted sum of independent factors. Weights come from settings
so an institution or company can re-tune them without a code change.

Two rules are non-negotiable and enforced here rather than by convention:

1. **No protected characteristics.** Gender, date of birth, religion, caste and
   similar attributes are never read by this module. Only skills, education,
   stated interests, experience, location preference, certifications and
   projects contribute.
2. **Support, not decision.** The output is a *recommendation score* with its
   full derivation attached. Nothing in the platform auto-rejects or auto-hires
   on the basis of it.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from app.ai.scoring import HeldSkill, Requirement
from app.ai.skill_gap import compare_to_requirements
from app.core.config import settings
from app.models.enums import Degree, WorkMode

# Factors, in the order they are shown to the user.
FACTORS = (
    "skills", "education", "interest", "experience", "location",
    "certification", "project",
)

FACTOR_LABELS: dict[str, str] = {
    "skills": "Skill compatibility",
    "education": "Education fit",
    "interest": "Career interest",
    "experience": "Relevant experience",
    "location": "Location and work mode",
    "certification": "Certifications",
    "project": "Project relevance",
}


@dataclass(slots=True)
class CandidateSnapshot:
    """Everything the matcher is allowed to see about a candidate."""

    skills: list[HeldSkill] = field(default_factory=list)
    degree: Degree | None = None
    cgpa: float | None = None
    graduation_year: int | None = None
    backlogs: int = 0
    department: str | None = None
    career_interests: list[str] = field(default_factory=list)
    preferred_roles: list[str] = field(default_factory=list)
    preferred_industries: list[str] = field(default_factory=list)
    preferred_locations: list[str] = field(default_factory=list)
    preferred_work_mode: WorkMode | None = None
    open_to_relocate: bool = True
    city: str | None = None
    experience_months: float = 0.0
    experience_skill_ids: set[str] = field(default_factory=set)
    certification_skill_ids: set[str] = field(default_factory=set)
    certification_count: int = 0
    project_skill_ids: set[str] = field(default_factory=set)
    project_count: int = 0


@dataclass(slots=True)
class OpportunitySnapshot:
    """Everything the matcher needs about a posting."""

    id: str
    title: str
    company_name: str = ""
    industry_sector: str = ""
    requirements: list[Requirement] = field(default_factory=list)
    job_role_title: str | None = None
    work_mode: WorkMode = WorkMode.ONSITE
    location_city: str | None = None
    min_cgpa: float | None = None
    max_backlogs: int | None = None
    eligible_degrees: list[str] = field(default_factory=list)
    eligible_graduation_years: list[int] = field(default_factory=list)
    eligible_departments: list[str] = field(default_factory=list)
    experience_min_years: float = 0.0
    opportunity_type: str = "INTERNSHIP"


@dataclass(slots=True)
class MatchResult:
    match_score: float
    breakdown: dict[str, float]
    contributions: dict[str, float]
    matching_skills: list[str]
    missing_skills: list[str]
    reasons: list[str]
    reason_summary: str
    next_steps: list[str] = field(default_factory=list)
    is_eligible: bool = True
    ineligibility_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_score": self.match_score,
            "breakdown": self.breakdown,
            "contributions": self.contributions,
            "matching_skills": self.matching_skills,
            "missing_skills": self.missing_skills,
            "reasons": self.reasons,
            "reason_summary": self.reason_summary,
            "next_steps": self.next_steps,
            "is_eligible": self.is_eligible,
            "ineligibility_reasons": self.ineligibility_reasons,
        }


def _weights() -> dict[str, float]:
    return settings.match_weights


# ------------------------------------------------------------------ factors --
def _education_factor(
    candidate: CandidateSnapshot, opportunity: OpportunitySnapshot
) -> tuple[float, list[str]]:
    notes: list[str] = []
    score, checks = 0.0, 0

    if opportunity.eligible_degrees:
        checks += 1
        degree = candidate.degree.value if candidate.degree else None
        if degree and degree in opportunity.eligible_degrees:
            score += 1.0
            notes.append("your degree matches the eligibility criteria")
    else:
        checks += 1
        score += 1.0

    if opportunity.min_cgpa is not None:
        checks += 1
        if candidate.cgpa is None:
            score += 0.5  # unknown, not penalised outright
            notes.append("add your CGPA so employers can confirm eligibility")
        elif candidate.cgpa >= opportunity.min_cgpa:
            score += 1.0
            notes.append(f"your CGPA of {candidate.cgpa} clears the {opportunity.min_cgpa} cut-off")

    if opportunity.eligible_graduation_years:
        checks += 1
        if candidate.graduation_year in opportunity.eligible_graduation_years:
            score += 1.0
            notes.append(f"your {candidate.graduation_year} graduation year is in scope")

    if opportunity.eligible_departments and candidate.department:
        checks += 1
        if candidate.department in opportunity.eligible_departments:
            score += 1.0

    return (score / checks if checks else 1.0), notes


def _interest_factor(
    candidate: CandidateSnapshot, opportunity: OpportunitySnapshot
) -> tuple[float, list[str]]:
    haystack = " ".join(
        filter(None, [opportunity.title, opportunity.job_role_title or ""])
    ).lower()
    stated = [
        *(candidate.preferred_roles or []),
        *(candidate.career_interests or []),
    ]
    if not stated:
        # No stated preference is neutral, not negative.
        return 0.5, []

    for entry in stated:
        token = str(entry).lower().strip()
        if not token:
            continue
        if token in haystack or haystack in token:
            return 1.0, [f"it matches your stated interest in {entry}"]

    # Partial credit for overlapping words (e.g. "Backend" vs "Backend Engineer").
    role_words = set(haystack.replace("/", " ").split())
    for entry in stated:
        words = set(str(entry).lower().split())
        if words & role_words - {"developer", "engineer", "and", "the"}:
            return 0.7, [f"it is adjacent to your interest in {entry}"]

    if candidate.preferred_industries and opportunity.industry_sector:
        if opportunity.industry_sector.lower() in [
            str(i).lower() for i in candidate.preferred_industries
        ]:
            return 0.6, [f"the company is in {opportunity.industry_sector}, an industry you selected"]

    return 0.25, []


def _experience_factor(
    candidate: CandidateSnapshot, opportunity: OpportunitySnapshot
) -> tuple[float, list[str]]:
    required_months = max(0.0, opportunity.experience_min_years * 12)
    required_skill_ids = {r.skill_id for r in opportunity.requirements}
    overlap = candidate.experience_skill_ids & required_skill_ids
    notes: list[str] = []

    if required_months <= 0:
        # Entry level: any relevant experience is a bonus, none is not a penalty.
        base = 0.6 + min(0.4, candidate.experience_months / 12 * 0.2)
    else:
        base = min(1.0, candidate.experience_months / required_months) * 0.75

    if overlap:
        base = min(1.0, base + 0.25)
        notes.append(
            f"your past experience already used {len(overlap)} of the required skills"
        )
    return round(min(1.0, base), 4), notes


def _location_factor(
    candidate: CandidateSnapshot, opportunity: OpportunitySnapshot
) -> tuple[float, list[str]]:
    if opportunity.work_mode == WorkMode.REMOTE:
        return 1.0, ["the role is remote, so location is not a constraint"]

    preferred = [str(x).lower() for x in (candidate.preferred_locations or [])]
    city = (opportunity.location_city or "").lower()

    if city and preferred and city in preferred:
        return 1.0, [f"{opportunity.location_city} is one of your preferred locations"]
    if city and candidate.city and city == candidate.city.lower():
        return 0.95, [f"the role is in {opportunity.location_city}, where you are based"]
    if candidate.preferred_work_mode and candidate.preferred_work_mode == opportunity.work_mode:
        return 0.75, []
    if candidate.open_to_relocate:
        return 0.6, []
    return 0.25, []


def _certification_factor(
    candidate: CandidateSnapshot, opportunity: OpportunitySnapshot
) -> tuple[float, list[str]]:
    required_skill_ids = {r.skill_id for r in opportunity.requirements}
    overlap = candidate.certification_skill_ids & required_skill_ids
    if overlap:
        ratio = min(1.0, len(overlap) / max(1, len(required_skill_ids)) * 3)
        return round(max(0.6, ratio), 4), [
            f"you hold {len(overlap)} certification(s) covering required skills"
        ]
    if candidate.certification_count:
        return 0.45, []
    return 0.2, []


def _project_factor(
    candidate: CandidateSnapshot, opportunity: OpportunitySnapshot
) -> tuple[float, list[str]]:
    required_skill_ids = {r.skill_id for r in opportunity.requirements}
    overlap = candidate.project_skill_ids & required_skill_ids
    if overlap:
        ratio = min(1.0, 0.5 + len(overlap) / max(1, len(required_skill_ids)) * 2)
        return round(ratio, 4), [
            f"you have built projects using {len(overlap)} of the required skills"
        ]
    if candidate.project_count:
        return 0.4, []
    return 0.15, []


# ------------------------------------------------------------- eligibility --
def check_eligibility(
    candidate: CandidateSnapshot, opportunity: OpportunitySnapshot
) -> list[str]:
    """Hard criteria the employer set. Separate from the score on purpose:
    a low score is advice, failing eligibility is a fact."""
    reasons: list[str] = []
    if opportunity.min_cgpa is not None and candidate.cgpa is not None:
        if candidate.cgpa < opportunity.min_cgpa:
            reasons.append(
                f"This role requires a minimum CGPA of {opportunity.min_cgpa}"
            )
    if opportunity.max_backlogs is not None and candidate.backlogs > opportunity.max_backlogs:
        reasons.append(
            f"This role allows at most {opportunity.max_backlogs} active backlog(s)"
        )
    if opportunity.eligible_graduation_years and candidate.graduation_year:
        if candidate.graduation_year not in opportunity.eligible_graduation_years:
            years = ", ".join(str(y) for y in sorted(opportunity.eligible_graduation_years))
            reasons.append(f"This role is open to the {years} graduating batch")
    if opportunity.eligible_degrees and candidate.degree:
        if candidate.degree.value not in opportunity.eligible_degrees:
            reasons.append("Your degree is not in the eligible list for this role")
    return reasons


# ----------------------------------------------------------------- matcher --
def match(
    candidate: CandidateSnapshot,
    opportunity: OpportunitySnapshot,
    *,
    weights: dict[str, float] | None = None,
) -> MatchResult:
    """Score one candidate against one opportunity, with the derivation attached."""
    weights = weights or _weights()

    matching_skills, missing_skills, skill_coverage = compare_to_requirements(
        candidate.skills, opportunity.requirements
    )

    education, education_notes = _education_factor(candidate, opportunity)
    interest, interest_notes = _interest_factor(candidate, opportunity)
    experience, experience_notes = _experience_factor(candidate, opportunity)
    location, location_notes = _location_factor(candidate, opportunity)
    certification, certification_notes = _certification_factor(candidate, opportunity)
    project, project_notes = _project_factor(candidate, opportunity)

    breakdown = {
        "skills": round(skill_coverage, 4),
        "education": round(education, 4),
        "interest": round(interest, 4),
        "experience": round(experience, 4),
        "location": round(location, 4),
        "certification": round(certification, 4),
        "project": round(project, 4),
    }
    contributions = {
        factor: round(breakdown[factor] * weights.get(factor, 0.0) * 100, 2)
        for factor in FACTORS
    }
    score = round(min(100.0, sum(contributions.values())), 1)

    # ------------------------------------------------------------- reasons --
    reasons: list[str] = []
    if matching_skills:
        shown = ", ".join(matching_skills[:4])
        extra = len(matching_skills) - 4
        reasons.append(
            f"You already meet the bar on {shown}"
            + (f" and {extra} more required skill(s)" if extra > 0 else "")
        )
    for notes in (
        interest_notes, project_notes, experience_notes, certification_notes,
        education_notes, location_notes,
    ):
        if notes:
            reasons.append(notes[0][0].upper() + notes[0][1:])
    if missing_skills:
        reasons.append(
            "The main gap is " + ", ".join(missing_skills[:3])
            + (f" (+{len(missing_skills) - 3} more)" if len(missing_skills) > 3 else "")
        )

    ineligibility = check_eligibility(candidate, opportunity)

    # ------------------------------------------------------------- summary --
    if ineligibility:
        summary = (
            "You do not currently meet this employer's stated eligibility criteria: "
            + "; ".join(ineligibility)
        )
    elif skill_coverage >= 0.8:
        summary = (
            f"Strong skill overlap with {opportunity.title}"
            + (f" at {opportunity.company_name}" if opportunity.company_name else "")
            + ". "
            + (
                f"{missing_skills[0]} is the one gap worth closing before you apply."
                if missing_skills
                else "You meet every listed requirement."
            )
        )
    elif skill_coverage >= 0.5:
        summary = (
            f"A realistic stretch: you cover the core of {opportunity.title}, with "
            + ", ".join(missing_skills[:2])
            + " as the remaining gap."
            if missing_skills
            else f"A realistic fit for {opportunity.title}."
        )
    else:
        summary = (
            f"{opportunity.title} is a longer-term target - "
            + (
                f"{len(missing_skills)} required skills are still missing."
                if missing_skills
                else "the requirements are some distance from your current profile."
            )
        )

    next_steps: list[str] = []
    for skill_name in missing_skills[:3]:
        next_steps.append(f"Build evidence in {skill_name} (a project or an assessment)")
    if not candidate.certification_count and certification < 0.5:
        next_steps.append("Add a certification that covers one of the required skills")
    if not candidate.project_count:
        next_steps.append("Publish at least one project to your portfolio")

    return MatchResult(
        match_score=score,
        breakdown=breakdown,
        contributions=contributions,
        matching_skills=matching_skills,
        missing_skills=missing_skills,
        reasons=reasons[:6],
        reason_summary=summary,
        next_steps=next_steps[:4],
        is_eligible=not ineligibility,
        ineligibility_reasons=ineligibility,
    )


def rank(
    candidate: CandidateSnapshot,
    opportunities: Iterable[OpportunitySnapshot],
    *,
    limit: int | None = None,
    min_score: float = 0.0,
    weights: dict[str, float] | None = None,
) -> list[tuple[OpportunitySnapshot, MatchResult]]:
    """Score many opportunities for one candidate, best first."""
    scored = [
        (opportunity, match(candidate, opportunity, weights=weights))
        for opportunity in opportunities
    ]
    scored = [pair for pair in scored if pair[1].match_score >= min_score]
    scored.sort(key=lambda pair: (-pair[1].match_score, pair[0].title))
    return scored[:limit] if limit else scored


def rank_candidates(
    candidates: Iterable[tuple[str, CandidateSnapshot]],
    opportunity: OpportunitySnapshot,
    *,
    limit: int | None = None,
    weights: dict[str, float] | None = None,
) -> list[tuple[str, MatchResult]]:
    """Score many candidates against one opportunity (recruiter view)."""
    scored = [
        (candidate_id, match(snapshot, opportunity, weights=weights))
        for candidate_id, snapshot in candidates
    ]
    scored.sort(key=lambda pair: -pair[1].match_score)
    return scored[:limit] if limit else scored
