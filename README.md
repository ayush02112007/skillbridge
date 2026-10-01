# SkillBridge

**Academia–Industry Collaboration & Employability Platform**

SkillBridge closes the distance between what students are taught and what
employers actually hire for. It measures a student's skills rather than taking
their word for them, shows exactly how those skills compare with a real role,
turns the difference into a learning path, and connects five participants —
students, academicians, companies, institutions and platform administrators —
around the same evidence.

This is a working full-stack application: a FastAPI backend with 79 tables and
218 API operations, a Next.js 15 frontend with 70 routes, a deterministic
recommendation engine that explains every score it produces, and the Docker,
CI and test infrastructure to run it.

---

## Table of contents

1. [What it does](#what-it-does)
2. [Technology stack](#technology-stack)
3. [Prerequisites](#prerequisites)
4. [Quick start](#quick-start)
5. [Demo accounts](#demo-accounts)
6. [Architecture](#architecture)
7. [Project layout](#project-layout)
8. [Running without Docker](#running-without-docker)
9. [Configuration](#configuration)
10. [Database and migrations](#database-and-migrations)
11. [Seeding](#seeding)
12. [API](#api)
13. [Light and dark themes](#light-and-dark-themes)
14. [The matching and recommendation engine](#the-matching-and-recommendation-engine)
15. [Assessment and skill-gap engines](#assessment-and-skill-gap-engines)
16. [Security](#security)
17. [Privacy and data ethics](#privacy-and-data-ethics)
18. [Testing](#testing)
19. [Production builds](#production-builds)
20. [Deployment](#deployment)
21. [Troubleshooting](#troubleshooting)
22. [Further documentation](#further-documentation)

---

## What it does

### For students

Take a skill assessment and receive a *measured* proficiency level, not a
self-declared one. Choose a target role and see a per-skill gap analysis with a
readiness percentage. Follow a prerequisite-ordered learning path that never
schedules React before JavaScript. Browse internships, jobs and live projects
ranked by evidenced fit, apply, and track every application through an explicit
state machine. Build a portfolio from verified work — completed internships and
assessed skills write back to it — and publish it publicly, privately, or to
your institution only.

### For companies

Post internships, jobs, live projects and faculty collaborations. See applicants
ranked by skill compatibility with the reasoning shown: which required skills
they meet, which they are missing, and how the score was composed. Move
applications through review, shortlist, interview, offer and selection, with
every transition recorded. Run mentorship programmes, sponsor research, and
partner directly with institutions.

### For academicians

Publish research, offer mentorship, run workshops, and collaborate with
industry. See aggregate skill trends across your students so curriculum
decisions are informed by what the market is actually asking for.

### For institutions

A placement-cell view of the student body: readiness distribution, placement
statistics, department-level analytics, industry partnerships, and exportable
reports (CSV and PDF).

### For platform administrators

User and organisation management, skill taxonomy curation, assessment bank
administration, moderation, audit log, and system health.

---

## Technology stack

### Backend

| Area | Choice | Version |
| --- | --- | --- |
| Language | Python | 3.12 |
| Framework | FastAPI | 0.115 |
| Validation | Pydantic + pydantic-settings | 2.10 / 2.7 |
| ORM | SQLAlchemy (async) | 2.0 |
| Migrations | Alembic (async `env.py`) | 1.14 |
| Database | PostgreSQL / SQLite | 16 / 3.x |
| Drivers | asyncpg, psycopg2, aiosqlite | — |
| Cache & broker | Redis | 7 |
| Background jobs | Celery + beat | 5.4 |
| Object storage | boto3 → S3 / MinIO | — |
| Passwords | Argon2id (argon2-cffi) | 23.1 |
| Tokens | PyJWT | 2.10 |
| Numerics | NumPy, pandas, scikit-learn | — |
| Reports | reportlab, pypdf, python-docx | — |
| Logging | structlog | 24.4 |
| Tests | pytest, pytest-asyncio, pytest-cov | 8.3 |
| Lint / types | ruff, mypy | 0.8 / 1.14 |

### Frontend

| Area | Choice | Version |
| --- | --- | --- |
| Framework | Next.js (App Router) | 15.1 |
| UI library | React | 19 |
| Language | TypeScript | 5.7 |
| Styling | Tailwind CSS + CSS variable tokens | 3.4 |
| Server state | TanStack Query | 5.64 |
| Forms | React Hook Form + Zod | 7.54 / 3.24 |
| Charts | Recharts | 2.15 |
| Motion | Framer Motion | 11 |
| Icons | lucide-react | 0.474 |
| Toasts | Sonner | 1.7 |
| Unit tests | Vitest + Testing Library | 2.1 |
| E2E tests | Playwright | 1.49 |
| Lint | ESLint + eslint-config-next | 9 / 15.1 |

### Infrastructure

Docker and Compose v2, nginx 1.27 (TLS, rate limiting), MinIO, Mailpit,
GitHub Actions (CI and a scheduled security workflow with CodeQL).

---

## Prerequisites

**With Docker — the only prerequisite is Docker itself.**

| Tool | Version | Notes |
| --- | --- | --- |
| Docker | 24+ with Compose v2 | Everything else runs inside containers |

**Without Docker:**

| Tool | Version | Notes |
| --- | --- | --- |
| Python | **3.12** | `requirements.txt` pins versions that have wheels for 3.12. Python 3.13+ may fail to build `greenlet` and `pydantic-core`. |
| Node.js | 22 LTS | 20 also works |
| PostgreSQL | 16 | Optional — SQLite is fully supported for development |
| Redis | 7 | Optional — there is an in-process cache and inline task fallback |

Nothing else is required. No API key is needed: the AI layer defaults to a
deterministic engine that makes no external calls.

---

## Quick start

The fastest path is Docker. You need Docker with Compose v2.

```bash
git clone <repository-url> skillbridge
cd skillbridge
cp .env.example .env
docker compose up --build
```

That builds and starts everything: PostgreSQL, Redis, MinIO, Mailpit, the API,
a Celery worker and beat scheduler, and the Next.js frontend. On first boot the
API waits for PostgreSQL, applies migrations and seeds the demo dataset.

| Service | URL | Notes |
| --- | --- | --- |
| Frontend | <http://localhost:3000> | The application |
| API | <http://localhost:8000> | REST API |
| Swagger UI | <http://localhost:8000/docs> | Interactive API documentation |
| ReDoc | <http://localhost:8000/redoc> | Reference-style API documentation |
| OpenAPI schema | <http://localhost:8000/openapi.json> | Machine-readable |
| Mailpit | <http://localhost:8025> | Every email the app "sends" |
| MinIO console | <http://localhost:9001> | Uploaded documents |

First run takes a few minutes (images, dependencies, seed data). Subsequent
starts are quick. To stop and keep your data, `docker compose down`; to reset
everything including volumes, `docker compose down -v`.

---

## Demo accounts

The seeder creates six labelled accounts. They all share one password, printed
by the seeder and configurable through `SEED_DEMO_PASSWORD`:

```
DemoPass!2024
```

| Email | Role | Sees |
| --- | --- | --- |
| `student@demo.com` | Student | Assessments, skill gap, learning path, applications, portfolio |
| `faculty@demo.com` | Academician | Research, mentorship, workshops, industry collaboration |
| `industry@demo.com` | Industry recruiter | Applicants, postings for one company |
| `industry-admin@demo.com` | Industry admin | The full company workspace, team, analytics |
| `institution@demo.com` | Institution admin | Student directory, placements, reports, partnerships |
| `admin@demo.com` | Platform admin | Users, organisations, taxonomy, moderation, audit |

> **These are development fixtures.** The seeder refuses to run when
> `ENVIRONMENT=production`, every seeded row is flagged `is_demo = true`, and
> these credentials must never exist in a production deployment.

`student@demo.com` is deliberately populated: assessments taken, a skill gap
with real priorities, applications in several states, projects, certifications
and a published portfolio — so every screen has something meaningful on it
rather than an empty state.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                  Browser                                 │
│   Next.js 15 · React 19 · TypeScript · Tailwind · TanStack Query         │
│   App Router · server components for shells, client for interaction      │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ HTTPS · JSON · Bearer JWT
┌───────────────────────────────▼──────────────────────────────────────────┐
│                        Nginx (production only)                           │
│   TLS termination · rate limiting · security headers · static caching    │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│                            FastAPI application                           │
│                                                                          │
│  Middleware   request context · security headers · rate limit · CSRF     │
│  API layer    25 routers · 168 paths · Pydantic v2 request/response      │
│  Services     auth · skills · assessment · opportunity · application ·   │
│               document · portfolio · analytics · notification · storage  │
│  AI engines   scoring · skill gap · matching · learning path ·           │
│               recommender · (optional) LLM narrative provider            │
│  Models       79 SQLAlchemy 2.0 tables, async, joined-table polymorphic  │
└──────┬───────────────────────┬──────────────────┬────────────────────────┘
       │                       │                  │
┌──────▼───────┐    ┌──────────▼────────┐   ┌─────▼──────────────┐
│  PostgreSQL  │    │   Redis           │   │  S3 / MinIO        │
│  system of   │    │   cache + Celery  │   │  documents,        │
│  record      │    │   broker          │   │  signed URLs only  │
└──────────────┘    └──────────┬────────┘   └────────────────────┘
                               │
                    ┌──────────▼────────┐
                    │  Celery worker    │  email, recommendation refresh,
                    │  + beat scheduler │  digests, demand recalculation
                    └───────────────────┘
```

Two decisions shape most of the code:

**Dialect portability.** Everything runs on PostgreSQL in Docker and on SQLite
locally, with no code changes. A `JSONB` type decorator renders as PostgreSQL's
`JSONB` or as portable `JSON`, and `sa.Uuid` handles identifiers. The result is
that the full test suite runs anywhere without infrastructure, and CI checks
both.

**Deterministic first.** Scoring, matching, gap analysis and learning paths are
pure functions of the data. An LLM is optional and may only rephrase the
narrative around numbers it did not produce. With no API key configured the
platform is fully functional.

---

## Project layout

```
SkillBridge/
├── backend/                      FastAPI application
│   ├── app/
│   │   ├── main.py               application factory, lifespan, error handlers
│   │   ├── core/                 config, database, security, logging,
│   │   │                         middleware, rbac, cache, exceptions
│   │   ├── models/               79 SQLAlchemy models + enums and state machine
│   │   ├── schemas/              Pydantic v2 request/response contracts
│   │   ├── api/v1/endpoints/     25 routers, 168 paths
│   │   ├── services/             business logic, transaction boundaries
│   │   ├── ai/                   scoring, skill_gap, matching, learning_path,
│   │   │                         recommender, text, provider, service
│   │   ├── repositories/         shared query builders
│   │   ├── tasks/                Celery app and jobs
│   │   └── utils/                pagination, formatting, validators
│   ├── migrations/               Alembic — async env.py, versioned revisions
│   ├── seeds/                    catalogue, assessment bank, demo dataset
│   ├── tests/                    pytest — 111 tests
│   ├── scripts/e2e-backend.sh    isolated API for the Playwright suite
│   ├── Dockerfile                multi-stage, non-root uid 1001
│   ├── docker-entrypoint.sh      wait for DB → migrate → optional seed → serve
│   ├── requirements.txt          runtime dependencies (pinned)
│   ├── requirements-dev.txt      test and lint dependencies
│   ├── pyproject.toml            ruff and mypy configuration
│   ├── pytest.ini                pytest configuration
│   ├── alembic.ini               migration configuration
│   └── .env.example              backend-only environment template
│
├── frontend/                     Next.js 15 application
│   ├── app/                      App Router — 70 routes
│   │   ├── (marketing)/          public landing page
│   │   ├── (auth)/               login, register, password reset, verification
│   │   ├── student/              15 routes
│   │   ├── industry/             11 routes
│   │   ├── academician/          7 routes
│   │   ├── institution/          9 routes
│   │   ├── admin/                10 routes
│   │   ├── opportunities/ companies/ portfolio/
│   │   ├── globals.css           design tokens — light and dark
│   │   ├── icon.svg              app icon
│   │   └── layout.tsx            providers, metadata, no-flash theme script
│   ├── components/
│   │   ├── ui/                   design-system primitives, incl. theme-toggle
│   │   ├── charts/               Recharts wrappers, theme-aware
│   │   └── layout/               shell, navigation, command palette, toaster
│   ├── features/                 screen-level modules, one per role
│   ├── hooks/use-chart-theme.ts  live chart colours for the active theme
│   ├── lib/
│   │   ├── api.ts                typed client, envelope, single-flight refresh
│   │   ├── auth.tsx              session context and route guard
│   │   ├── theme.tsx             theme provider and pre-paint script
│   │   ├── query.tsx             TanStack Query client
│   │   ├── constants.ts          labels, status tones, transitions
│   │   └── utils.ts              formatting helpers
│   ├── types/api.ts              mirrors the API contract
│   ├── tests/unit/               Vitest — 120 tests
│   ├── tests/e2e/                Playwright — 49 tests
│   ├── public/                   static assets
│   ├── package.json              scripts and dependencies
│   ├── package-lock.json         exact dependency tree
│   ├── tsconfig.json             TypeScript configuration
│   ├── tailwind.config.ts        design tokens → Tailwind scales
│   ├── next.config.mjs           standalone output for Docker
│   ├── vitest.config.ts          unit test configuration
│   ├── playwright.config.ts      e2e configuration, starts both servers
│   ├── Dockerfile                multi-stage, standalone, non-root uid 1001
│   └── .env.example              frontend-only environment template
│
├── database/                     everything to create the DB from scratch
│   ├── schema/
│   │   ├── schema.sql            flattened PostgreSQL DDL, 79 tables
│   │   └── generate_schema.py    regenerates schema.sql from the models
│   ├── init/01-extensions.sql    runs once on an empty PostgreSQL volume
│   └── README.md                 setup, migrations, seeding, constraints
│
├── docker/
│   ├── nginx/                    reverse proxy: TLS, rate limiting, headers
│   │   ├── nginx.conf
│   │   ├── proxy_params_sb
│   │   └── certs/                mount fullchain.pem and privkey.pem here
│   └── README.md                 image and service reference
│
├── docs/
│   ├── architecture.md           layering, request lifecycle, portability
│   ├── er-diagram.md             all 79 tables, grouped by domain
│   ├── api-flows.md              sequence diagrams for the main journeys
│   ├── authentication.md         token lifecycle, rotation, reuse detection
│   ├── recommendation-engine.md  scoring maths, worked example, ethics
│   ├── security-architecture.md  threat model, controls, what is out of scope
│   ├── scalability.md            bottlenecks, scaling stages, honest limits
│   └── theming.md                design tokens, contrast table, how to extend
│
├── .github/workflows/
│   ├── ci.yml                    backend, frontend, e2e, Docker
│   └── security.yml              pip-audit, npm audit, secret scan, CodeQL
│
├── docker-compose.yml            full development stack
├── docker-compose.prod.yml       production overlay
├── .env.example                  every variable, documented
├── .gitignore
└── README.md
```

> **Migrations and seeds live under `backend/`, not `database/`.** Alembic
> resolves `script_location` relative to the backend package, `env.py` imports
> `app.core.database` for the custom `JSONB` type, and the API image's build
> context is `backend/` — a migration outside it would not be in the image
> that runs `alembic upgrade head`. `database/README.md` says the same and
> points at both.

---

## Running without Docker

Useful for day-to-day development. No PostgreSQL, Redis or MinIO required —
the defaults fall back to SQLite, an in-process cache, inline task execution,
console email and local file storage.

### Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # then set DATABASE_URL=sqlite+aiosqlite:///./var/skillbridge.db
alembic upgrade head
python -m seeds.seed
uvicorn app.main:app --reload
```

The API is on <http://localhost:8000>, docs on `/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The app is on <http://localhost:3000>.

---

## Configuration

Every setting is an environment variable with a safe development default, so an
empty `.env` still boots. `.env.example` documents all 74 of them with inline
comments. The ones that matter most:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` |
| `DATABASE_URL` | SQLite file | `postgresql+asyncpg://…` in Docker |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache and Celery broker |
| `JWT_SECRET` / `JWT_REFRESH_SECRET` | dev sentinels | **Must be changed for production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access-token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `14` | Refresh-token lifetime |
| `CORS_ORIGINS` | localhost | Comma-separated; never `*` in production |
| `AI_PROVIDER` | `deterministic` | `deterministic` / `openai` / `anthropic` / `local` |
| `AI_API_KEY` | empty | Server-side only, never reaches the browser |
| `STORAGE_PROVIDER` | `local` | `local` / `s3` |
| `EMAIL_PROVIDER` | `console` | `console` / `smtp` / `sendgrid` / `ses` / `resend` |
| `MATCH_WEIGHT_*` | see below | Matching weights; must sum to exactly 1.0 |
| `SEED_DEMO_PASSWORD` | `DemoPass!2024` | Development fixture password |

### Production refuses to start misconfigured

`Settings.validate_runtime()` runs at startup and aborts the boot if, with
`ENVIRONMENT=production`:

- `JWT_SECRET` or `JWT_REFRESH_SECRET` is still the development sentinel,
- `DEBUG` is true,
- `CORS_ORIGINS` contains `*`,
- `TRUSTED_HOSTS` is `*`,
- the matching weights do not sum to 1.0.

This is deliberate: a platform that quietly runs with a known signing key is
worse than one that refuses to start.

### Secrets

Secrets come only from the environment. There are no credentials in source,
none in the frontend bundle, and the structured logger redacts any key whose
name looks like a password, token or secret before anything is written. A CI
job fails the build if an `.env` file is committed or if a `NEXT_PUBLIC_`
variable is named like a secret.

---

## Database and migrations

79 tables covering users and RBAC, institutions and departments, companies and
teams, the skill taxonomy, assessments and attempts, the opportunity hierarchy,
applications and their timeline, mentorship, events, research, projects,
certifications, portfolios, documents, notifications, messaging and audit.

The opportunity hierarchy uses joined-table polymorphic inheritance:
`opportunities` holds everything common, and `internships`, `jobs`,
`live_projects` and `faculty_opportunities` add what is specific to each. One
query searches all four; one foreign key from `applications` points at all four.

```bash
alembic upgrade head                      # apply
alembic downgrade -1                      # roll back one
alembic revision --autogenerate -m "..."  # new migration
alembic current                           # where am I
```

The `env.py` is async and reads `DATABASE_URL` from settings. Generated
migrations import `app.core.database` so the custom `JSONB` type resolves.

Notable invariants enforced in the database, not only in code:

- `applications` has a check constraint requiring exactly one applicant
  identity (a student *or* an academician, never both, never neither).
- Skill scores are constrained to 0–100. This caught a real seeder bug.
- Unique constraints prevent duplicate applications, duplicate skill rows per
  student, and duplicate portfolio slugs.

---

## Seeding

```bash
python -m seeds.seed                   # catalogue + demo dataset
python -m seeds.seed --catalog-only    # taxonomy and assessments only
python -m seeds.seed --reset           # drop, recreate, reseed
python -m seeds.seed --students 200    # a larger cohort
```

The seeder is deterministic — same seed, same data — and refuses to run when
`ENVIRONMENT=production`.

It loads a curated catalogue of 128 skills across categories with 31 job roles
and 315 role–skill links, an assessment bank of 50 scored questions plus 8
Likert items, and then a demo dataset: institutions with departments and
programmes, companies with teams and postings, students with assessment
histories and applications, mentors, events, research and partnerships.

Question options are shuffled at seed time with a deterministic hash-seeded
permutation. The bank is authored correct-answer-first, so without this,
answering "always A" would score 86%.

---

## API

The API is versioned under `/api/v1` and documented at `/docs`.

- **168 paths, 218 operations, 25 tag groups**
- Every response is enveloped: `{ "success": true, "data": …, "meta": … }`
- Every error is enveloped: `{ "success": false, "error": { "code", "message", "details" } }`
- Errors carry stable machine-readable codes (`ALREADY_APPLIED`,
  `INVALID_TRANSITION`, `TOKEN_REUSED`, …), not just HTTP statuses
- List endpoints are paginated with `page` / `page_size` and return
  `meta: { page, page_size, total, pages }`

A representative request:

```bash
# sign in
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"student@demo.com","password":"DemoPass!2024"}'

# use the access token
curl -s http://localhost:8000/api/v1/recommendations/opportunities \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Every recommendation in that response carries a `reasons` array. A
recommendation that cannot state why it is there is dropped rather than shown.

---

## Light and dark themes

Both themes are designed; neither is an inversion of the other. The toggle is
in the header of every surface — the marketing site, the sign-in pages, and
every portal — plus a three-way **Light · Dark · System** control in
**Settings → Account**.

```
Marketing nav ──▶ ☀/🌙   Auth header ──▶ ☀/🌙   App header ──▶ ☀/🌙
                                          Settings → Account ──▶ [Light|Dark|System]
```

- **System is the default.** It follows `prefers-color-scheme` and keeps
  following it, so a device that switches at sunset takes the app with it.
  Choosing Light or Dark explicitly stops that until System is picked again.
- **The choice persists** in `localStorage` under `sb.theme`, across reloads,
  navigation and new tabs. It is per-device, not per-account.
- **No flash of the wrong theme.** A synchronous script in `<head>` resolves
  and applies the theme before first paint; the React provider adopts that
  decision rather than re-deciding it.
- **Every colour is a token.** `app/globals.css` defines them for both themes;
  no component hardcodes a colour and there are no `dark:` variants scattered
  through the markup.

Coverage is complete: backgrounds, cards, text, secondary text, borders,
buttons, inputs, navigation, tables, dialogs, alerts and toasts, charts and
gauges, badges and status chips, skeletons, scrollbars, focus rings, shadows
and the mobile browser chrome.

Every text token was measured against the surface it sits on — all reach WCAG
AA and most reach AAA. The full contrast table, the token reference and the
rules for adding a component are in [`docs/theming.md`](docs/theming.md).

---

## The matching and recommendation engine

### How a match score is computed

A weighted sum of seven factors, each scored 0–100 independently, then combined:

| Factor | Weight | What it measures |
| --- | --- | --- |
| Skills | 50% | Evidenced proficiency against required and preferred skills, weighted by each skill's importance to the role |
| Education | 15% | Degree, discipline, graduation year and CGPA against stated criteria |
| Interest | 10% | Declared career interests and target role |
| Experience | 10% | Prior internships, projects and their relevance |
| Location | 5% | Location and work-mode compatibility |
| Certification | 5% | Relevant certifications held |
| Project | 5% | Project work relevant to the role's skills |

Weights are configurable through `MATCH_WEIGHT_*` and validated at startup to
sum to exactly 1.0.

### Explainability is a contract, not a feature

Every score returns its contributions — the per-factor breakdown, the matched
skills, the missing skills, and human-readable reasons. The student sees why an
opportunity was recommended. The recruiter sees the same breakdown next to the
application, above an explicit statement that the score is decision support and
the hiring decision is theirs.

### What the engine may not do

Two rules are enforced in code and stated in the module that implements them:

1. **No protected characteristics.** Gender, date of birth, religion, caste and
   similar attributes are never read by the matching module. They are not
   inputs, not proxies, not tie-breakers.
2. **Support, not decision.** Nothing in the platform auto-rejects, auto-hires
   or auto-filters a candidate out of a recruiter's view on the basis of a
   score. Recruiters can sort and threshold, but the decision is a human one.

### Optional LLM narrative

With `AI_PROVIDER` set to `openai`, `anthropic` or `local` and a key present,
an LLM may rewrite the *narrative* around a recommendation — the prose, not the
numbers. The score, the ranking and the reasons are computed deterministically
either way. If no key exists, the deterministic narrative is used and nothing
is degraded.

---

## Assessment and skill-gap engines

### Scoring

Questions carry a difficulty weight (easy 1.0, medium 1.5, hard 2.25).
Multi-select questions award partial credit with a penalty for wrong
selections, so guessing everything scores worse than answering carefully.
Unanswered questions count against the maximum — skipping is not free. A
confidence figure accompanies every result and reflects how many questions
supported it.

### Measurement overrides self-report

A student may declare a proficiency. An assessment measures one. The measured
value wins, and the UI always shows the evidence source beside the level: a
self-reported "Advanced" and a tested "Advanced" are not the same claim and are
never displayed as if they were.

### Skill gap

For a target role, each required skill is compared against the student's
evidenced level. The gap carries a severity, the role's importance weighting,
and a priority that accounts for how much of the market currently asks for that
skill. The result is an ordered list of what to work on next, with a readiness
percentage for the role as a whole.

### Learning paths

Generated from the gaps, ordered by a prerequisite graph. JavaScript is never
scheduled after React; SQL comes before database design. Each step carries an
estimated effort and, where the institution offers one, an attached programme.

---

## Security

| Concern | Implementation |
| --- | --- |
| Password storage | Argon2id, with a strength policy enforced server-side and mirrored in the UI |
| Sessions | Short-lived access JWT + rotating refresh token |
| Token theft | Refresh reuse detection: presenting a rotated token revokes the entire session family |
| Authorisation | RBAC with 52 permissions across 6 roles, defined in one catalogue and synced to the database on boot |
| Object access | Ownership checks on every resource; the API is the authority, the UI only hides what would be refused |
| Rate limiting | Per-IP buckets in middleware, tighter for authentication (10/min), plus Nginx zones in production |
| CSRF | Double-submit token for cookie-authenticated requests; bearer requests are exempt by construction |
| Input validation | Pydantic v2 at the boundary, database constraints underneath |
| SQL injection | Parameterised SQLAlchemy throughout; no string-built SQL |
| XSS | React escaping by default, no `dangerouslySetInnerHTML` on user content, CSP headers |
| Uploads | Magic-byte content sniffing, MIME allow-list, size limits, path-containment checks, randomised storage names |
| Document access | Private by default; served only through short-lived signed URLs |
| Headers | CSP, HSTS (production), `X-Content-Type-Options`, `X-Frame-Options`, Referrer-Policy, Permissions-Policy |
| Audit | Security-relevant actions written to an append-only audit log with actor, IP and user agent |
| Logging | Structured JSON with automatic redaction of secret-shaped keys |
| Secrets | Environment only; never in source, never in the frontend bundle, never in logs |

See [`docs/security-architecture.md`](docs/security-architecture.md)
for the full model, including the threat table and what is deliberately out of
scope.

---

## Privacy and data ethics

- **Portfolios** have three visibility levels: `PUBLIC`, `INSTITUTION_ONLY` and
  `PRIVATE`. The default is private.
- **Documents** are never publicly accessible. Every download is an
  authorisation check followed by a signed URL that expires.
- **Contact details** are revealed to a recruiter only once a student has
  applied to that recruiter's posting.
- **Protected characteristics** are never used for ranking. Where the platform
  stores demographic data at all, it is for the institution's own reporting and
  is excluded from every scoring path.
- **Students can see their own data** — the gap analysis, the score breakdown,
  the reasons — because a recommendation a student cannot interrogate is not
  explainable in any useful sense.
- **Audit logs** record who accessed what, so institutional access to student
  records is traceable.

---

## Testing

```bash
# Backend — 111 tests
cd backend && pytest -q
pytest --cov=app --cov-report=term-missing

# Frontend unit — 120 tests
cd frontend && npm test
npm run test:coverage          # thresholds enforced: 90% lines

# Type checking and linting
cd frontend && npm run typecheck && npm run lint
cd backend  && ruff check . && mypy app seeds

# End to end — 49 tests
cd frontend
npm run test:e2e:install       # once: downloads Chromium (~150 MB)
npm run test:e2e
```

### Playwright setup

`playwright.config.ts` starts **both servers itself**, so `npm run test:e2e`
works from a clean checkout — no manual setup, no leftover state. The API runs
against its own throwaway SQLite database (`backend/scripts/e2e-backend.sh`),
recreated and reseeded on every run, so the suite never touches your
development data.

| Command | What it does |
| --- | --- |
| `npm run test:e2e:install` | Downloads the Chromium build Playwright manages |
| `npm run test:e2e` | Runs both projects — desktop and phone |
| `npm run test:e2e -- --project=chromium` | Desktop only |
| `npm run test:e2e:ui` | Interactive runner |
| `npx playwright show-report` | The HTML report from the last run |

**If the Chromium download is blocked** — a restricted network, a corporate
proxy — drive a locally installed browser instead:

```bash
E2E_BROWSER_CHANNEL=chrome npm run test:e2e     # or msedge
```

Same engine, no download. Video capture is skipped in that mode because it
needs the ffmpeg binary from the same download; traces and screenshots still
work, and they are the useful artefacts anyway.

Other environment variables the suite honours:

| Variable | Default | Purpose |
| --- | --- | --- |
| `E2E_BROWSER_CHANNEL` | unset | Use a locally installed `chrome` / `msedge` |
| `E2E_BASE_URL` | `http://127.0.0.1:3000` | Test against an already-running frontend |
| `E2E_API_URL` | `http://127.0.0.1:8000` | Test against an already-running API |
| `E2E_KEEP_DB` | `false` | Keep the e2e database between runs when debugging |
| `PYTHON` | auto-detected | Interpreter for the e2e API (falls back to `backend/.venv`, then `python3`) |

### What the suites cover

**Backend (111)** — authentication (registration, login, refresh rotation,
reuse detection, password policy, rate limiting), settings parsing and the
production-configuration guards, the skill taxonomy, assessment scoring
including answer-position bias, the marketplace and application state machine,
and the recommendation engine's explainability contract.

**Frontend unit (120)** — the API client (envelope unwrapping, error mapping,
single-flight token refresh), the auth context and route guard, the theme
system (persistence, system-preference following, corrupted storage), the
formatting helpers, and the design-system primitives — with particular
attention to accessibility: dialog focus trapping, tab keyboard navigation,
tooltip dismissal, labelled form controls.

**Contract tests** read the backend's Python enums directly and assert the
TypeScript unions match, that every application status has a label and a tone,
and that the recruiter UI never offers a status transition the API would
reject. Language boundaries are where contracts drift silently; this makes the
drift fail a build.

**End to end (49)** — a real browser against a real API, covering the journey
the specification describes: register → sign in → complete profile → take an
assessment → view the skill gap → find an internship → apply → recruiter
reviews → recruiter shortlists → the student sees the new status. Plus route
protection, password recovery, every sidebar link in all five portals, phone
layout, keyboard accessibility, and the theme system — persistence across
reloads and navigation, the system-preference default, that the theme is
applied before React hydrates, and that eight representative pages paint
correctly in both themes with the heading contrast above 4.5:1.

---

## Production builds

```bash
# Frontend — standalone server bundle, the same one the Docker image runs
cd frontend
npm ci
NEXT_PUBLIC_API_URL=https://api.example.com \
NEXT_PUBLIC_SITE_URL=https://app.example.com \
  npm run build
npm run start                    # serves the build on :3000
```

`next.config.mjs` sets `output: "standalone"`, so `.next/standalone/server.js`
is a self-contained server. `NEXT_PUBLIC_*` values are compiled into the
bundle at build time — changing one requires a rebuild, not a restart.

```bash
# Backend — no build step; run the ASGI app under a process manager
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  --workers 4 --proxy-headers --forwarded-allow-ips '*'
```

```bash
# Both, as images
docker compose build
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
```

---

## Deployment

### Docker Compose

```bash
# generate real secrets first
python -c "import secrets; print(secrets.token_urlsafe(64))"

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The production overlay sets `ENVIRONMENT=production`, disables seeding and
debug, requires every secret to be supplied (the compose file fails fast if one
is missing), stops publishing database and cache ports to the host, and puts
Nginx in front as the only exposed service.

Put your certificate and key in `docker/nginx/certs/` as
`fullchain.pem` and `privkey.pem`.

### Pre-flight checklist

- [ ] `JWT_SECRET` and `JWT_REFRESH_SECRET` are unique, random and different
- [ ] `POSTGRES_PASSWORD` and `S3_SECRET_KEY` are not the development values
- [ ] `CORS_ORIGINS` lists your real origins; `TRUSTED_HOSTS` lists real hostnames
- [ ] `SECURE_COOKIES=true` and TLS is terminating at Nginx
- [ ] `REQUIRE_EMAIL_VERIFICATION=true`
- [ ] `SEED_ON_START=false`
- [ ] A real `EMAIL_PROVIDER` is configured
- [ ] Database backups are scheduled
- [ ] No demo account exists

The API will refuse to start if the first item is wrong. The others are on you.

### Health

`GET /health` is a liveness check. `GET /ready` verifies the database and cache
and is what a load balancer should poll.

Scaling is discussed in
[`docs/scalability.md`](docs/scalability.md).

---

## Troubleshooting

**`docker compose up` fails on the database.** The API waits up to two minutes
for PostgreSQL. If it gives up, check `docker compose logs postgres` — usually
a stale volume from a previous password. `docker compose down -v` clears it.

**Migrations fail with "target database is not up to date".** You have a
partially applied migration. `alembic current` shows where you are;
`alembic downgrade base && alembic upgrade head` on a development database is
the blunt fix.

**SQLite "disk I/O error".** You deleted `skillbridge.db` but left
`skillbridge.db-wal` and `skillbridge.db-shm`. Delete all three.

**The frontend shows "We could not load this" everywhere.** The API is not
reachable at `NEXT_PUBLIC_API_URL`. That variable is baked in at build time, so
changing it needs a rebuild, not a restart.

**Rate limited during development.** Raise `RATE_LIMIT_AUTH_PER_MINUTE`, or set
`RATE_LIMIT_ENABLED=false`.

**Playwright cannot find a browser.** `npm run test:e2e:install`.

**Seeding fails with a constraint violation.** That is the database catching a
real inconsistency. Read the constraint name — it says exactly what invariant
was broken.

**`pip install -r requirements.txt` fails building `greenlet` or
`pydantic-core`.** You are on Python 3.13 or newer; the pinned versions have
wheels for 3.12. Use Python 3.12, or let Docker handle it.

**The API will not start and mentions `CORS_ORIGINS`.** An older build
JSON-decoded list settings straight out of the `.env` file, so the
comma-separated form this README documents raised at startup. Fixed —
`enable_decoding=False` in `Settings.model_config` leaves parsing to the
validator, which accepts both `a,b` and `["a","b"]`. If you see this, your
backend is out of date.

**Production refuses to start.** That is deliberate. The message names the
setting: a development JWT secret, `DEBUG` on, `SECURE_COOKIES` off, the two
JWT secrets equal, or a wildcard in `CORS_ORIGINS` / `TRUSTED_HOSTS`. See
`backend/app/core/config.py:validate_runtime`.

**Playwright cannot download Chromium.** Use a locally installed browser
instead: `E2E_BROWSER_CHANNEL=chrome npm run test:e2e`.

**The theme flashes on load.** The pre-paint script in `<head>` should prevent
it. If you moved `<ThemeScript />` out of `<head>` or removed
`suppressHydrationWarning` from `<html>`, put them back — see
[`docs/theming.md`](docs/theming.md).

---

## Further documentation

| Document | Contents |
| --- | --- |
| [`docs/architecture.md`](docs/architecture.md) | System architecture, request lifecycle, layering rules |
| [`docs/er-diagram.md`](docs/er-diagram.md) | Entity relationships across all 79 tables |
| [`docs/api-flows.md`](docs/api-flows.md) | Sequence diagrams for the main journeys |
| [`docs/authentication.md`](docs/authentication.md) | Token lifecycle, rotation, reuse detection, RBAC |
| [`docs/recommendation-engine.md`](docs/recommendation-engine.md) | Scoring maths, worked example, ethical constraints |
| [`docs/security-architecture.md`](docs/security-architecture.md) | Threat model, controls, what is out of scope |
| [`docs/scalability.md`](docs/scalability.md) | Bottlenecks, scaling stages, what would change |
| [`docs/theming.md`](docs/theming.md) | Design tokens, contrast table, how to style a new component |
| [`database/README.md`](database/README.md) | Creating the database from scratch, migrations, seeding, constraints |
| [`docker/README.md`](docker/README.md) | Images, services, commands, production overlay |

---

## Licence

Provided as-is for educational and demonstration purposes.
