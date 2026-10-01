# Entity-relationship model

79 tables. This document groups them by domain, shows the relationships that
matter, and explains the two structural decisions that shape the rest.

Notation: `──<` is one-to-many (crow's foot at the many end), `>──<` is
many-to-many through a join table, `──` is one-to-one.

---

## 1. Identity, roles and sessions

```
                    ┌──────────────────┐
                    │      users       │
                    ├──────────────────┤
                    │ id (uuid) PK     │
                    │ email UNIQUE     │
                    │ password_hash    │  Argon2id
                    │ full_name        │
                    │ status           │  PENDING_VERIFICATION|ACTIVE|SUSPENDED
                    │ is_email_verified│
                    │ institution_id FK│
                    │ company_id FK    │
                    │ deleted_at       │  soft delete
                    └───┬────┬─────┬───┘
                        │    │     │
         ┌──────────────┘    │     └───────────────┐
         │                   │                     │
         ▼                   ▼                     ▼
┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐
│   user_roles    │  │ user_sessions  │  │ one_time_tokens  │
│  (join table)   │  ├────────────────┤  ├──────────────────┤
└────────┬────────┘  │ id PK          │  │ token_hash       │ sha256, never raw
         │           │ user_id FK     │  │ purpose          │ VERIFY|RESET
         ▼           │ refresh_hash   │  │ expires_at       │
┌─────────────────┐  │ family_id      │  │ used_at          │
│      roles      │  │ parent_id      │  └──────────────────┘
├─────────────────┤  │ revoked_at     │
│ name UNIQUE     │  │ ip_address     │  Rotation chain: presenting a token
│ label           │  │ user_agent     │  that was already rotated revokes the
│ is_assignable_  │  │ expires_at     │  whole family — see authentication.md
│   on_signup     │  └────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────────┐
│ role_permissions│──────▶│   permissions    │
│  (join table)   │       ├──────────────────┤
└─────────────────┘       │ code UNIQUE      │  e.g. "application:review"
                          │ resource, action │
                          └──────────────────┘
```

52 permissions across 6 roles. The catalogue lives in `app/core/rbac.py` as the
single source of truth and is synced into these tables on every boot, so the
database always matches the code.

---

## 2. Organisations

```
┌────────────────────┐            ┌────────────────────┐
│   institutions     │            │     companies      │
├────────────────────┤            ├────────────────────┤
│ id PK              │            │ id PK              │
│ name, slug UNIQUE  │            │ name, slug UNIQUE  │
│ type, city, state  │            │ industry_sector    │
│ accreditation      │            │ size, headquarters │
│ is_verified        │            │ is_verified        │
└─────────┬──────────┘            └─────────┬──────────┘
          │                                 │
          ▼ ──<                             ▼ ──<
┌────────────────────┐            ┌────────────────────┐
│   departments      │            │ recruiter_profiles │
├────────────────────┤            ├────────────────────┤
│ institution_id FK  │            │ company_id FK      │
│ name, code         │            │ user_id FK         │
└─────────┬──────────┘            │ designation        │
          │                       └────────────────────┘
          ▼ ──<
┌────────────────────┐
│ student_profiles   │            ┌──────────────────────┐
└────────────────────┘            │ industry_partnerships│
                                  ├──────────────────────┤
     institutions ──<  ─────────▶ │ institution_id FK    │
     companies    ──<  ─────────▶ │ company_id FK        │
                                  │ type, status, mou_*  │
                                  └──────────────────────┘
```

---

## 3. Profiles

```
                       users
                         │ 1──1
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌───────────────┐ ┌──────────────┐ ┌─────────────────┐
│student_profiles│ │academician_  │ │recruiter_       │
├───────────────┤ │  profiles    │ │  profiles       │
│ user_id FK    │ └──────────────┘ └─────────────────┘
│ institution_id│
│ department_id │        A user has exactly one profile, of the type that
│ program, year │        matches their role. The profile carries everything
│ graduation_yr │        role-specific; `users` stays lean.
│ cgpa          │
│ target_role_id│
│ readiness_score│
│ profile_completion
│ portfolio_slug│
└───┬───┬───┬───┘
    │   │   │
    │   │   └──────────────< achievements
    │   └──────────────────< student_projects
    └──────────────────────< education_records, experience_records
```

---

## 4. Skill taxonomy

This is the spine of the platform: everything that ranks, scores or recommends
resolves through it.

```
┌──────────────────┐
│ skill_categories │
├──────────────────┤
│ slug UNIQUE      │  programming, data, cloud, design, soft-skills, …
└────────┬─────────┘
         │ ──<
         ▼
┌──────────────────────┐              ┌────────────────────┐
│       skills         │              │     job_roles      │
├──────────────────────┤              ├────────────────────┤
│ id PK                │              │ id PK              │
│ slug UNIQUE          │              │ slug UNIQUE        │
│ name, aliases[]      │              │ title, family      │
│ category_id FK       │              │ seniority          │
│ market_demand 0-100  │              │ salary_min/max     │
│ is_active            │              │ demand_score       │
└───┬──────────────┬───┘              └─────────┬──────────┘
    │              │                            │
    │              │  ┌─────────────────────────┘
    │              ▼  ▼
    │       ┌──────────────────┐
    │       │   role_skills    │   the required-skill profile of a role
    │       ├──────────────────┤
    │       │ role_id FK       │
    │       │ skill_id FK      │
    │       │ required_level   │   BEGINNER … EXPERT
    │       │ importance       │   REQUIRED | PREFERRED
    │       │ weight           │   relative contribution
    │       └──────────────────┘
    │
    ▼ ──<
┌──────────────────────┐
│   student_skills     │   what a student actually has
├──────────────────────┤
│ student_id FK        │
│ skill_id FK          │   UNIQUE (student_id, skill_id)
│ level                │
│ score 0-100          │   CHECK constraint
│ source               │   SELF_REPORTED | ASSESSMENT | PROJECT | CERTIFICATION
│ confidence           │
│ is_verified          │
└──────┬───────────────┘
       │
       ▼ ──<
┌──────────────────────┐
│  skill_endorsements  │   a faculty member or recruiter vouching for a skill
└──────────────────────┘

┌──────────────────────┐          ┌──────────────────────┐
│ skill_gap_analyses   │ ──<      │   skill_gap_items    │
├──────────────────────┤ ────────▶├──────────────────────┤
│ student_id FK        │          │ skill_id FK          │
│ target_role_id FK    │          │ current_level        │
│ readiness_score      │          │ required_level       │
│ generated_at         │          │ severity, priority   │
└──────────────────────┘          └──────────────────────┘
```

`source` is doing real work. A self-reported "Advanced" and an assessed
"Advanced" are stored identically except for this column, and the UI never
shows one without it.

---

## 5. Assessments

```
┌────────────────────┐
│    assessments     │
├────────────────────┤
│ skill_id FK        │
│ duration_minutes   │
│ passing_score      │
│ max_attempts       │
└─────────┬──────────┘
          │ ──<
          ▼
┌────────────────────┐       ┌────────────────────┐
│assessment_questions│ ──<   │ assessment_options │
├────────────────────┤ ─────▶├────────────────────┤
│ prompt, type       │       │ label              │
│ difficulty         │       │ is_correct         │  never serialised to a
│ skill_id FK        │       └────────────────────┘  candidate mid-attempt
│ points             │
└────────────────────┘

┌────────────────────┐
│assessment_attempts │
├────────────────────┤
│ student_id FK      │
│ assessment_id FK   │
│ status             │  IN_PROGRESS | SUBMITTED | EVALUATED | EXPIRED
│ score, percentage  │
│ is_passed          │
│ confidence         │
│ duration_seconds   │
└────┬──────────┬────┘
     │          │
     ▼ ──<      ▼ ──<
┌──────────────┐ ┌────────────────────┐
│assessment_   │ │attempt_skill_scores│  per-skill breakdown, which is what
│  answers     │ ├────────────────────┤  feeds student_skills and the gap
└──────────────┘ │ skill_id FK        │  analysis
                 │ percentage, level  │
                 │ confidence         │
                 └────────────────────┘
```

---

## 6. Opportunities — joined-table inheritance

One posting concept, four kinds. The base table holds everything shared; each
subtype table adds its own columns and shares the base primary key.

```
                    ┌──────────────────────────┐
                    │      opportunities       │   base table
                    ├──────────────────────────┤
                    │ id PK                    │
                    │ kind                     │   discriminator
                    │ title, description       │
                    │ company_id FK            │
                    │ posted_by_id FK          │
                    │ location, work_mode      │
                    │ status                   │   DRAFT|PUBLISHED|CLOSED|…
                    │ application_deadline     │
                    │ eligible_degrees[]       │
                    │ eligible_graduation_years│
                    │ min_cgpa                 │
                    │ views_count              │
                    └────┬────┬────┬────┬──────┘
                         │    │    │    │
       ┌─────────────────┘    │    │    └──────────────────┐
       ▼                      ▼    ▼                       ▼
┌──────────────┐   ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐
│ internships  │   │    jobs      │  │live_projects │  │faculty_opportunities│
├──────────────┤   ├──────────────┤  ├──────────────┤  ├─────────────────────┤
│ duration_mos │   │ employment_  │  │ team_size    │  │ collaboration_type  │
│ stipend_min/ │   │   type       │  │ complexity   │  │ funding_amount      │
│   max        │   │ salary_min/  │  │ deliverables │  │ duration_months     │
│ is_ppo_      │   │   max        │  │ mentor_id FK │  │                     │
│   possible   │   │ experience_  │  │              │  │                     │
│ start_date   │   │   years_min  │  │              │  │                     │
└──────────────┘   └──────────────┘  └──────────────┘  └─────────────────────┘

opportunities ──< opportunity_skills >── skills
                  ├ required_level
                  ├ importance  (REQUIRED | PREFERRED)
                  └ weight

opportunities ──< saved_opportunities >── student_profiles
```

Why this shape: a student's "my applications" list, the recruiter's applicant
queue and the public search all need to treat the four kinds uniformly, while
an internship genuinely has a stipend and a job genuinely has a salary band.
Single-table inheritance would fill the table with nulls; separate tables would
need four of every query, four foreign keys on `applications` and four search
paths. Joined-table gives one query surface and honest columns.

---

## 7. Applications

```
┌──────────────────────────────┐
│        applications          │
├──────────────────────────────┤
│ id PK                        │
│ opportunity_id FK            │  points at the base table, so one FK
│ student_id FK      (nullable)│  covers all four kinds
│ academician_id FK  (nullable)│
│ status                       │  APPLIED → … → SELECTED | REJECTED | WITHDRAWN
│ match_score                  │  snapshot at submission
│ match_breakdown  (JSONB)     │  the factor contributions, frozen
│ matching_skills[]            │
│ missing_skills[]             │
│ cover_letter                 │
│ recruiter_rating             │
│ submitted_at                 │
└─────────┬─────────────┬──────┘
          │             │
          ▼ ──<         ▼ ──<
┌──────────────────────┐ ┌──────────────────┐
│application_status_   │ │    interviews    │
│      history         │ ├──────────────────┤
├──────────────────────┤ │ scheduled_at     │
│ from_status          │ │ mode, location   │
│ to_status            │ │ interviewer_id FK│
│ changed_by_id FK     │ │ outcome          │
│ note                 │ └──────────────────┘
│ created_at           │
└──────────────────────┘

CHECK one_applicant_identity:
    (student_id IS NOT NULL) <> (academician_id IS NOT NULL)

UNIQUE (opportunity_id, student_id)        — no duplicate applications
UNIQUE (opportunity_id, academician_id)
```

Two things are deliberate here. The match score and its breakdown are
**snapshotted** onto the application: a recruiter reviewing next month should
see the score as it was when the student applied, not one that silently changed
because the student took another assessment. And the check constraint makes
"exactly one applicant identity" a database invariant rather than a convention
that a future code path could break.

The permitted transitions live in `APPLICATION_TRANSITIONS`
(`app/models/enums.py`) and are enforced in the service layer; the frontend's
copy is asserted to be a subset of it by a contract test.

---

## 8. Learning

```
learning_paths ──< (generated from skill_gap_items)

┌──────────────────┐        ┌──────────────────┐
│ learning_programs│ ──<    │  course_modules  │
├──────────────────┤ ──────▶├──────────────────┤
│ institution_id FK│        │ order, duration  │
│ company_id FK    │        └────────┬─────────┘
│ title, level     │                 │
│ duration_hours   │                 ▼ ──<
└────┬─────────┬───┘        ┌──────────────────┐
     │         │            │ module_progress  │
     │         ▼ ──<        └──────────────────┘
     │  ┌──────────────┐
     │  │program_skills│ >── skills
     │  └──────────────┘
     ▼ ──<
┌──────────────┐
│ enrollments  │ >── student_profiles
└──────────────┘

certifications ──< student_certifications >── student_profiles
                   ├ credential_id
                   ├ issued_at, expires_at
                   └ verification_url
```

---

## 9. Portfolio and documents

```
┌────────────────────┐        ┌──────────────────────┐
│    portfolios      │        │      documents       │
├────────────────────┤        ├──────────────────────┤
│ student_id FK 1──1 │        │ owner_id FK          │
│ slug UNIQUE        │        │ kind                 │ RESUME|CERTIFICATE|…
│ visibility         │        │ storage_key          │ randomised
│   PUBLIC           │        │ original_filename    │
│   INSTITUTION_ONLY │        │ content_type, size   │
│   PRIVATE  (default)│       │ checksum             │
│ headline, summary  │        │ is_public   (false)  │
│ view_count         │        │ virus_scan_status    │
└────────────────────┘        └──────────┬───────────┘
                                         │ ──<
┌────────────────────┐        ┌──────────▼───────────┐
│      resumes       │ ──<    │document_access_grants│
├────────────────────┤        ├──────────────────────┤
│ document_id FK     │        │ grantee_id FK        │  who may read it
│ is_primary         │        │ expires_at           │  and until when
└─────────┬──────────┘        └──────────────────────┘
          │ ──<
          ▼
┌────────────────────┐
│  resume_analyses   │   parsed skills, experience and suggestions
└────────────────────┘

badges ──< student_badges >── student_profiles
```

Documents are private by default. There is no code path that serves one from a
public URL: every download is an authorisation check followed by a signed URL
that expires (`SIGNED_URL_EXPIRE_SECONDS`, default 15 minutes).

---

## 10. Collaboration

```
mentors ──< mentorship_requests ──< mentorship_sessions
events  ──< event_registrations
research_projects ──< research_applications
project_teams ──< project_team_members
              ──< project_tasks
              ──< project_milestones
              ──< project_submissions
conversations ──< conversation_participants
              ──< messages
```

---

## 11. Platform

```
┌──────────────────┐   ┌──────────────────┐   ┌────────────────────────┐
│  notifications   │   │   audit_logs     │   │    recommendations     │
├──────────────────┤   ├──────────────────┤   ├────────────────────────┤
│ user_id FK       │   │ actor_id FK      │   │ student_id FK          │
│ kind, title      │   │ action           │   │ kind, target_id        │
│ payload (JSONB)  │   │ resource_type/id │   │ score                  │
│ read_at          │   │ ip_address       │   │ reasons (JSONB)        │ never empty
│ channel          │   │ user_agent       │   │ is_dismissed           │
└──────────────────┘   │ metadata (JSONB) │   └───────────┬────────────┘
                       │ created_at       │               │ ──<
┌──────────────────┐   └──────────────────┘   ┌───────────▼────────────┐
│notification_     │                          │recommendation_feedback │
│  preferences     │   append-only; no        ├────────────────────────┤
├──────────────────┤   update or delete       │ was_useful             │
│ per-kind, per-   │   path exists            │ reason                 │
│ channel toggles  │                          └────────────────────────┘
└──────────────────┘

email_logs      delivery attempts and outcomes
saved_searches  a student's stored filters, optionally with alerts
```

`recommendations.reasons` is never empty. The recommender drops any candidate
it cannot explain rather than presenting an unexplained score — see
`recommendation-engine.md`.

---

## Conventions

| Convention | Applied to |
| --- | --- |
| UUID primary keys | Every table. Identifiers are safe to expose and do not leak row counts. |
| `created_at` / `updated_at` | Every table, timezone-aware. |
| Soft delete (`deleted_at`) | Users, companies, institutions, opportunities — anything referenced by history that must not vanish. |
| `is_demo` | Every seeded row, so demo data is identifiable and removable. |
| JSONB | Only for genuinely schemaless payloads: match breakdowns, notification payloads, audit metadata. Never as a substitute for a column. |
| Indexes | Every foreign key; plus composite indexes on the sort/filter paths the marketplace and applicant queue actually use. |
| Check constraints | Score ranges, the applicant-identity rule, date ordering. Invariants belong in the database. |
