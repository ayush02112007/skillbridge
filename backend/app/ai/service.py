"""High-level AI service.

Every method returns a useful result whether or not an LLM is configured:
a deterministic answer is computed first, and the provider - when available -
is used only to rewrite it more fluently. The structured fields (scores, skill
lists, priorities) always come from the deterministic engines, never from a
model, so numbers are reproducible and auditable.
"""
from __future__ import annotations

from typing import Any

from app.ai.provider import AIProvider, get_ai_provider
from app.ai.skill_gap import GapResult
from app.ai.text import ParsedDocument, keyword_frequencies
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("ai.service")

SYSTEM_PROMPT = (
    "You are a careers adviser inside SkillBridge, a university employability "
    "platform. Write in clear, plain, encouraging British English. Be specific "
    "and concrete. Never invent facts about the student: only use what you are "
    "given. Never state or imply a hiring decision. Do not mention age, gender, "
    "religion, caste, marital status or any other protected characteristic."
)


class AIService:
    """Facade over the configured provider with deterministic fallbacks."""

    def __init__(self, provider: AIProvider | None = None) -> None:
        self._provider = provider

    @property
    def provider(self) -> AIProvider:
        return self._provider or get_ai_provider()

    @property
    def mode(self) -> str:
        return self.provider.name if self._llm_enabled else "deterministic"

    @property
    def _llm_enabled(self) -> bool:
        return settings.AI_ENABLE_LLM_NARRATIVES and self.provider.available

    async def _narrate(self, prompt: str, fallback: str, *, max_tokens: int = 400) -> tuple[str, str]:
        """Return ``(text, generated_by)``; falls back silently on any failure."""
        if not self._llm_enabled:
            return fallback, "deterministic"
        text = await self.provider.complete(
            prompt, system=SYSTEM_PROMPT, max_tokens=max_tokens
        )
        if not text or len(text.strip()) < 20:
            return fallback, "deterministic"
        return text.strip(), self.provider.name

    # ------------------------------------------------------- skill gap -----
    async def explain_skill_gap(self, gap: GapResult) -> tuple[str, str]:
        fallback = gap.summary
        missing = ", ".join(i.skill_name for i in gap.missing[:5]) or "none"
        weak = ", ".join(i.skill_name for i in gap.weak[:5]) or "none"
        strong = ", ".join(i.skill_name for i in gap.strong[:5]) or "none"
        prompt = (
            f"A student is targeting the role of {gap.job_role_title}.\n"
            f"Readiness score: {gap.readiness_score}% "
            f"({gap.matched_count} of {gap.total_required} core requirements met).\n"
            f"Skills not started: {missing}\n"
            f"Skills partially developed: {weak}\n"
            f"Skills already at the required level: {strong}\n\n"
            "Write 3 to 4 sentences explaining where they stand and what to do "
            "next, in priority order. Do not invent skills or experience."
        )
        return await self._narrate(prompt, fallback)

    # -------------------------------------------------- recommendations ----
    async def explain_recommendation(
        self,
        *,
        opportunity_title: str,
        company_name: str,
        match_score: float,
        matching_skills: list[str],
        missing_skills: list[str],
        deterministic_summary: str,
    ) -> tuple[str, str]:
        prompt = (
            f"Explain to a student why '{opportunity_title}'"
            + (f" at {company_name}" if company_name else "")
            + f" was recommended. Their skill compatibility is {match_score}%.\n"
            f"Skills they already meet: {', '.join(matching_skills[:6]) or 'none'}\n"
            f"Skills still missing: {', '.join(missing_skills[:6]) or 'none'}\n\n"
            "Two sentences. Be honest about the gap. Make clear this is a "
            "recommendation, not a guarantee of selection."
        )
        return await self._narrate(prompt, deterministic_summary, max_tokens=200)

    # -------------------------------------------------------- resume -------
    async def resume_suggestions(
        self, parsed: ParsedDocument, *, target_role: str | None,
        missing_skills: list[str], ats_score: int,
    ) -> tuple[list[str], str]:
        """Deterministic suggestions, optionally rephrased by the provider."""
        suggestions: list[str] = []
        text = parsed.raw_text

        if parsed.word_count < 200:
            suggestions.append(
                "Your resume is quite short. Expand each role and project with one "
                "line on what you built and one on the measurable outcome."
            )
        if parsed.word_count > 900:
            suggestions.append(
                "Your resume runs long for an early-career profile. Aim for one "
                "page by cutting the oldest and least relevant entries."
            )
        if not parsed.emails:
            suggestions.append("Add a professional email address to the header.")
        if not parsed.urls:
            suggestions.append(
                "Link your GitHub or portfolio - recruiters check code before they call."
            )
        if not parsed.sections.get("projects"):
            suggestions.append(
                "Add a Projects section. For students it carries more weight than "
                "any other section."
            )
        if not parsed.sections.get("skills"):
            suggestions.append(
                "Add an explicit Skills section so keyword screening finds your stack."
            )
        if not any(ch.isdigit() for ch in text):
            suggestions.append(
                "Quantify your impact - users served, latency reduced, time saved. "
                "Numbers make claims credible."
            )
        aspirational = [h.skill_name for h in parsed.skills if h.is_aspirational]
        if aspirational:
            suggestions.append(
                "You list "
                + ", ".join(aspirational[:3])
                + " as things you are learning. Move them to a separate 'Currently "
                "learning' line so your core skills stand out."
            )
        if missing_skills and target_role:
            suggestions.append(
                f"For {target_role}, employers expect "
                + ", ".join(missing_skills[:3])
                + ". Build evidence for these, then add them with the project that proves it."
            )
        if ats_score < 60:
            suggestions.append(
                "Use a single-column layout with standard section headings so "
                "applicant tracking systems parse your resume correctly."
            )
        if not suggestions:
            suggestions.append(
                "Your resume covers the essentials. Tailor the top third to each "
                "role you apply for."
            )
        return suggestions[:8], "deterministic"

    # ------------------------------------------------ job description ------
    async def extract_job_requirements(
        self, description: str, detected_skills: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Structured requirements from a job description.

        Skills come from deterministic taxonomy matching (so a recruiter never
        sees a hallucinated requirement); the provider, if present, is asked
        only for the softer fields, and its output is presented for review
        before publication.
        """
        result: dict[str, Any] = {
            "skills": detected_skills,
            "keywords": [k for k, _ in keyword_frequencies(description, 12)],
            "extracted_by": "deterministic",
        }
        if not self._llm_enabled:
            return result
        data = await self.provider.complete_json(
            "Extract structured hiring requirements from this job description. "
            "Use only what the text states.\n\nJSON keys: responsibilities "
            "(array of short strings), education (string), experience_years "
            "(number), seniority (one of ENTRY, MID, SENIOR).\n\n"
            f"Job description:\n{description[:6000]}",
            system=SYSTEM_PROMPT,
        )
        if data:
            result.update(
                {
                    "responsibilities": data.get("responsibilities", [])[:10],
                    "education": data.get("education"),
                    "experience_years": data.get("experience_years"),
                    "seniority": data.get("seniority"),
                    "extracted_by": self.provider.name,
                }
            )
        return result

    # ------------------------------------------------ career guidance ------
    async def career_guidance(
        self, *, student_name: str, top_skills: list[str], interests: list[str],
        target_role: str | None, readiness: float | None,
    ) -> tuple[str, str]:
        parts = []
        if top_skills:
            parts.append(f"Your strongest evidenced skills are {', '.join(top_skills[:4])}.")
        if target_role and readiness is not None:
            parts.append(
                f"You are {readiness:.0f}% ready for {target_role}; closing your top "
                "three gaps is the fastest way to move that number."
            )
        elif interests:
            parts.append(
                f"Based on your interest in {', '.join(interests[:2])}, set a target "
                "role so the platform can compute a concrete gap and learning path."
            )
        else:
            parts.append(
                "Start by taking a skill assessment and selecting a target role - "
                "everything else on SkillBridge builds on those two inputs."
            )
        parts.append(
            "Apply to roles where your compatibility is above 60%: that is where "
            "effort converts into interviews."
        )
        fallback = " ".join(parts)
        prompt = (
            f"Student's strongest skills: {', '.join(top_skills[:6]) or 'not yet assessed'}\n"
            f"Stated interests: {', '.join(interests[:4]) or 'not stated'}\n"
            f"Target role: {target_role or 'not chosen'}\n"
            f"Readiness for that role: {readiness if readiness is not None else 'unknown'}\n\n"
            "Give 3 to 4 sentences of concrete career guidance for the next month."
        )
        return await self._narrate(prompt, fallback)

    # ------------------------------------------ interview preparation ------
    async def interview_questions(
        self, *, role_title: str, skills: list[str], count: int = 8
    ) -> tuple[list[dict[str, str]], str]:
        """Practice questions. Deterministic templates, optionally LLM-authored."""
        templates = [
            ("Walk me through a project where you used {skill}. What did you own?", "Experience"),
            ("How would you debug a production issue involving {skill}?", "Problem solving"),
            ("What trade-offs do you weigh when choosing {skill} for a task?", "Depth"),
            ("Explain {skill} to a teammate who has never used it.", "Communication"),
            ("What is the most common mistake people make with {skill}?", "Depth"),
        ]
        generic = [
            (f"Why do you want to work as a {role_title}?", "Motivation"),
            ("Tell me about a time you disagreed with a teammate. What happened?", "Teamwork"),
            ("Describe something you learned recently without being told to.", "Learning agility"),
            ("What part of your last project would you build differently now?", "Reflection"),
        ]
        questions: list[dict[str, str]] = []
        for index, skill in enumerate(skills[:5]):
            prompt_text, category = templates[index % len(templates)]
            questions.append(
                {"question": prompt_text.format(skill=skill), "category": category,
                 "skill": skill}
            )
        for question, category in generic:
            if len(questions) >= count:
                break
            questions.append({"question": question, "category": category, "skill": ""})

        if not self._llm_enabled:
            return questions[:count], "deterministic"

        data = await self.provider.complete_json(
            f"Generate {count} interview questions for a {role_title} candidate "
            f"whose skills are: {', '.join(skills[:8])}. Mix technical depth, "
            "practical scenarios and behavioural questions.\n"
            'JSON shape: {"questions": [{"question": "...", "category": "...", '
            '"skill": "..."}]}',
            system=SYSTEM_PROMPT,
        )
        if data and isinstance(data.get("questions"), list):
            generated = [
                {
                    "question": str(q.get("question", ""))[:400],
                    "category": str(q.get("category", "General"))[:60],
                    "skill": str(q.get("skill", ""))[:80],
                }
                for q in data["questions"]
                if q.get("question")
            ]
            if generated:
                return generated[:count], self.provider.name
        return questions[:count], "deterministic"


_service: AIService | None = None


def get_ai_service() -> AIService:
    global _service
    if _service is None:
        _service = AIService()
    return _service


def set_ai_service(service: AIService | None) -> None:
    global _service
    _service = service
