# The recommendation engine

## Design position

The engine is **deterministic and explainable by construction**. Every number
it produces is a pure function of stored data, reproducible from the same
inputs, and returned together with the derivation that produced it.

No machine-learning model is trained on user data, and no large language model
computes a score. With `AI_PROVIDER=deterministic` — the default — the platform
makes no external calls and is fully functional. An LLM, if configured, may
only rephrase narrative text around numbers it did not produce.

This is a deliberate trade. A learned ranker might squeeze out more relevance,
but it would be far harder to explain to a student who asks why they were not
recommended something, and far easier to let bias in through a proxy variable
nobody noticed. For a platform that mediates access to employment, being able
to show the working matters more than the last few points of precision.

---

## Where the engine lives

```
app/ai/
├── scoring.py         level values, evidence weighting, coverage, readiness
├── skill_gap.py       requirement comparison, gap items, severity, priority
├── matching.py        the seven-factor match, eligibility, reasons
├── learning_path.py   prerequisite graph, ordering, effort estimation
├── recommender.py     opportunities, careers, learning, mentors, skills
├── text.py            resume parsing: skills, education, experience
├── provider.py        LLM provider abstraction (optional)
└── service.py         narrative generation, deterministic by default
```

Nothing in `app/ai/` touches the database. Every function takes plain
dataclasses and returns plain dataclasses. That is what makes the engine
testable without fixtures and reproducible between runs.

---

## 1. Skill coverage

Everything starts here, because the skills factor carries half the weight.

### Proficiency as an ordinal

```
NONE = 0   BEGINNER = 1   INTERMEDIATE = 2   ADVANCED = 3   EXPERT = 4
```

### Coverage of a single requirement

```
coverage = min(1.0, held_level / required_level)
```

Capped at 1.0: exceeding a requirement earns no bonus, because a role needs
what it needs. An `EXPERT` (4) against an `INTERMEDIATE` (2) requirement scores
1.0, not 2.0 — otherwise one over-qualified skill could mask three missing ones.

### Evidence weighting

A self-reported skill and an assessed one are not the same claim:

```
evidence_weighted = coverage × (0.7 + 0.3 × confidence)
```

Confidence comes from the source (`SOURCE_CONFIDENCE` in `scoring.py`):
`ASSESSMENT` 0.95, `CERTIFICATION` 0.85, `WORK_EXPERIENCE` 0.8, `PROJECT` 0.65,
`ENDORSEMENT` 0.6, `RESUME` 0.5, `SELF_REPORTED` 0.35.

The discount is bounded at 30%. An unassessed skill still counts for at least
70% of its value — the aim is to inform, not to punish someone who has not yet
sat a test. The clean way to remove the discount is to take the assessment,
which is exactly the behaviour the platform wants to encourage.

### Requirement weight

```
effective_weight = weight × importance_multiplier
                              REQUIRED  1.0
                              PREFERRED 0.6
                              OPTIONAL  0.3
```

### Overall coverage

```
              Σ (evidence_weighted_coverageᵢ × effective_weightᵢ)
coverage  =  ──────────────────────────────────────────────────────
                         Σ effective_weightᵢ
```

A skill counts as **matched** if the held level meets the required level, or if
its evidence-weighted coverage is at least 0.75; otherwise it is **missing**.
The 0.75 threshold means a well-evidenced near-miss reads as a match, while a
thinly evidenced one reads as a gap — which is the honest description in both
cases.

---

## 2. The seven factors

| Factor | Weight | Inputs |
| --- | --- | --- |
| Skills | 0.50 | Evidence-weighted coverage of the posting's requirements |
| Education | 0.15 | Degree, discipline, graduation year, CGPA against stated criteria |
| Interest | 0.10 | Declared career interests, target role, preferred industries |
| Experience | 0.10 | Internships and roles held, and whether they used the required skills |
| Location | 0.05 | City and work-mode compatibility, willingness to relocate |
| Certification | 0.05 | Certifications covering required skills |
| Project | 0.05 | Published projects using required skills |

```
score = Σ (factorᵢ × weightᵢ) × 100        capped at 100
```

Weights are read from settings (`MATCH_WEIGHT_*`), so an institution or company
can re-tune them without touching code, and `validate_runtime()` refuses to
start the application if they do not sum to exactly 1.0. That check exists
because weights that sum to 0.95 would silently deflate every score on the
platform in a way nobody would notice for months.

---

## 3. A worked example

This is real output from `app.ai.matching.match`, not an illustration.

**Candidate**

| Skill | Level | Source | Confidence |
| --- | --- | --- | --- |
| Python | ADVANCED | ASSESSMENT | 0.90 |
| SQL | INTERMEDIATE | ASSESSMENT | 0.80 |
| REST APIs | INTERMEDIATE | PROJECT | 0.70 |
| Git | INTERMEDIATE | PROJECT | 0.70 |
| Docker | BEGINNER | SELF_REPORTED | 0.35 |

BACHELORS, CGPA 8.1, graduating 2026, Computer Science, no backlogs.
Interested in backend engineering, based in Pune, prefers hybrid.
6 months of experience, 3 projects, 1 certification.

**Posting — Backend Engineering Intern, Nimbus Labs**

| Requirement | Level | Importance | Weight |
| --- | --- | --- | --- |
| Python | INTERMEDIATE | REQUIRED | 1.4 |
| SQL | INTERMEDIATE | REQUIRED | 1.2 |
| REST APIs | INTERMEDIATE | REQUIRED | 1.3 |
| PostgreSQL | INTERMEDIATE | REQUIRED | 1.2 |
| Docker | INTERMEDIATE | PREFERRED | 0.9 |

Pune, hybrid. BACHELORS, graduating 2026, minimum CGPA 7.0.

**Result**

```
Factor           Score     × Weight   = Contribution
─────────────────────────────────────────────────────
skills          0.6891      0.50         34.46
education       1.0000      0.15         15.00
interest        1.0000      0.10         10.00
experience      0.9500      0.10          9.50
location        1.0000      0.05          5.00
certification   0.6000      0.05          3.00
project         1.0000      0.05          5.00
─────────────────────────────────────────────────────
                                 TOTAL   81.96  →  82.0

matched : Python, SQL, REST APIs
missing : PostgreSQL, Docker
eligible: yes
```

**What the student is shown**

> A realistic stretch: you cover the core of Backend Engineering Intern, with
> PostgreSQL, Docker as the remaining gap.
>
> - You already meet the bar on Python, SQL, REST APIs
> - It matches your stated interest in Backend Developer
> - You have built projects using 3 of the required skills
> - Your past experience already used 2 of the required skills
> - You hold 1 certification(s) covering required skills
> - Your degree matches the eligibility criteria
>
> **Next steps**
> - Build evidence in PostgreSQL (a project or an assessment)
> - Build evidence in Docker (a project or an assessment)

Note what the skills factor does. Three of five requirements are met, but the
score is 0.689 rather than 0.6 — because the met skills carry higher weight and
better evidence, while Docker contributes partial credit for a beginner-level,
self-reported claim against a *preferred* requirement. The number is neither a
simple fraction nor a black box; it is a weighted average anyone can recompute.

**What the recruiter is shown** is the same breakdown — the factors, the
matched and missing skills — under an explicit statement that the score is
decision support and the hiring decision is theirs.

---

## 4. Skill-gap analysis

The gap analysis compares a student against a *role* rather than a posting, and
produces an ordered list of what to work on.

```
severity  = required_level − current_level          (1 to 4)

priority  = severity × role_importance × market_signal
```

`market_signal` is derived from how many live postings ask for that skill, so
two equally severe gaps are ordered by which one more employers are asking for.
That is deliberately a statement about the market, not about the student.

Readiness for the role is the same weighted coverage formula, expressed as a
percentage — and it is the figure on the student's dashboard.

---

## 5. Learning paths

Gaps become an ordered plan. The ordering is the interesting part.

```python
PREREQUISITES: dict[str, set[str]] = {
    "react":            {"javascript"},
    "nextjs":           {"react"},
    "redux":            {"react"},
    "typescript":       {"javascript"},
    "fastapi":          {"python"},
    "pandas":           {"python"},
    "scikit-learn":     {"python", "numpy"},
    "machine-learning": {"python", "statistics"},
    "deep-learning":    {"machine-learning"},
    ...
}
```

A naive path sorted by priority would happily put React before JavaScript,
because React is in more job postings. The engine performs a topological pass
over the prerequisite graph first, then orders within each tier by priority.
The result is a plan a student can actually follow.

Each step carries an estimated effort derived from the size of the gap, and,
where the student's institution offers a matching programme, that programme is
attached to the step.

---

## 6. Recommendation types

| Type | What it ranks | Explains itself with |
| --- | --- | --- |
| Opportunities | Internships, jobs, live projects | Match factors, matched and missing skills |
| Careers | Job roles to aim at | Readiness, transferable skills, market demand |
| Learning | Programmes and modules | Which gap it closes, prerequisites satisfied |
| Mentors | Academicians and industry mentors | Shared skills, target-role experience |
| Skills | What to learn next | Gap priority, how many postings ask for it |

### The explainability guard

```python
if not reasons:
    # A recommendation that cannot say why it is here does not belong here.
    continue
```

This is in `recommender.py` and it is not decorative. During development the
skill recommender could emit a recommendation with an empty `reasons` array in
one branch. The fix was to give that branch a real reason (market demand) and
to drop anything that still could not explain itself — rather than to relax the
test that caught it. A silent, unexplained ranking is precisely the failure
mode the design exists to prevent.

---

## 7. Ethical constraints

These are enforced in code, in the module that implements the scoring, and
stated in its docstring.

### Protected characteristics are not inputs

Gender, date of birth, religion, caste, marital status and similar attributes
are never read by `matching.py`. Look at `CandidateSnapshot`: it is the *only*
view the matcher has of a candidate, and the fields it declares are skills,
degree, CGPA, graduation year, backlogs, department, interests, location
preference, experience, certifications and projects. A protected attribute
cannot leak in accidentally, because there is no field for it to arrive in.

Where the platform stores demographic data at all, it is for an institution's
own statutory reporting, and it is excluded from every scoring path.

### The system does not decide

- No automatic rejection. A low score never removes a candidate from a
  recruiter's queue.
- No automatic shortlisting or hiring. Every status transition is performed by
  a person and recorded with their identity.
- Recruiters may sort and set a minimum threshold, which is a human choice made
  visibly, and the filtered-out candidates remain one click away.
- The applicant detail panel carries the disclosure text in the UI itself, not
  buried in terms: *the match score is decision support … the hiring decision
  remains yours.*

### Students can interrogate their own results

A student sees the same breakdown a recruiter sees, plus the next steps. A
recommendation a student cannot question is not meaningfully explainable, and
"the algorithm decided" is not an answer anybody should have to accept about
their own employment prospects.

### Feedback is collected, not silently acted on

`recommendation_feedback` records whether a recommendation was useful. It
informs future tuning by people. It does not silently retrain a ranker that
then becomes impossible to explain.

---

## 8. The optional LLM layer

```
AI_PROVIDER = deterministic   (default)  no external calls at all
            | openai | anthropic | local  narrative rephrasing only
```

The provider abstraction (`app/ai/provider.py`) is used by exactly one thing:
`app/ai/service.py`, which generates narrative text. The contract is:

- the LLM never computes, adjusts or re-ranks a score;
- it receives the already-computed numbers and reasons as context;
- if it is unavailable, times out, or no key is configured, the deterministic
  narrative is used and nothing else changes;
- the API key is server-side only and never reaches the browser.

Section 41 of the specification requires the application to work fully without
an API key. It does — the default path never calls anything.

---

## 9. Testing

`backend/tests/test_recommendations.py` asserts the properties, not the
outputs, because an assertion like `rows[0] == "Rec Backend Intern"` is brittle
against a shared database and tells you nothing about correctness:

- a candidate matching more requirements outranks one matching fewer;
- results are returned in descending score order;
- every recommendation carries at least one reason;
- contributions sum to the reported score;
- eligibility failures are reported as reasons, not as a silent exclusion.

The pure-function design means these run in milliseconds with no fixtures, and
the same input always produces the same output — so a failure is a real
regression rather than a flake.
