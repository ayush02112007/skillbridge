# Architecture

## System overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                  Clients                                   │
│                    browsers (desktop and mobile), API consumers            │
└───────────────────────────────────┬────────────────────────────────────────┘
                                    │ HTTPS
┌───────────────────────────────────▼────────────────────────────────────────┐
│                          Nginx  (production only)                          │
│  TLS 1.2/1.3 termination · HTTP→HTTPS redirect · security headers          │
│  rate-limit zones (auth 1r/s, write 10r/s, read 30r/s) · gzip              │
│  immutable caching for /_next/static · request-id propagation              │
└───────────────┬───────────────────────────────────┬────────────────────────┘
                │                                   │
    ┌───────────▼────────────┐          ┌───────────▼──────────────┐
    │   Next.js  (web)       │          │   FastAPI  (api)         │
    │   node:22 standalone   │          │   python:3.12-slim       │
    │   port 3000, non-root  │          │   port 8000, non-root    │
    └───────────┬────────────┘          └───────────┬──────────────┘
                │  fetch /api/v1/*                  │
                └───────────────────────────────────┤
                                                    │
        ┌───────────────┬───────────────────────────┼───────────────┐
        │               │                           │               │
┌───────▼──────┐ ┌──────▼───────┐        ┌──────────▼──────┐ ┌──────▼───────┐
│  PostgreSQL  │ │    Redis     │        │   S3 / MinIO    │ │  SMTP / ESP  │
│  16          │ │    7         │        │                 │ │              │
│  system of   │ │  cache (db0) │        │  documents,     │ │  Mailpit in  │
│  record      │ │  broker (db1)│        │  resumes,       │ │  development │
│              │ │  results(db2)│        │  avatars        │ │              │
└──────────────┘ └──────┬───────┘        └─────────────────┘ └──────────────┘
                        │
            ┌───────────▼────────────┐
            │  Celery worker + beat  │
            │  email, digests,       │
            │  recommendation        │
            │  refresh, demand recalc│
            └────────────────────────┘
```

## Backend layering

Each layer may call the layer below it and never the one above.

```
  API layer            app/api/v1/endpoints/*
  ────────────────     HTTP concerns only: routing, status codes, auth
                       dependencies, request/response schemas. No SQL, no
                       business rules. 25 routers, 168 paths.
        │
        ▼
  Schema layer         app/schemas/*
  ────────────────     Pydantic v2 contracts. Validation, coercion, the
                       documented shape of every request and response.
        │
        ▼
  Service layer        app/services/*
  ────────────────     Business rules and the transaction boundary. A service
                       function does one complete unit of work. Raises domain
                       exceptions, which the API layer maps to HTTP.
        │
        ▼
  AI / engine layer    app/ai/*
  ────────────────     Pure functions over plain data structures. No database
                       access, no I/O, no framework. This is what makes the
                       scoring testable in isolation and reproducible.
        │
        ▼
  Model layer          app/models/*
  ────────────────     SQLAlchemy 2.0 async ORM. 79 tables. Relationships,
                       constraints and the application state machine.
        │
        ▼
  Core                 app/core/*
  ────────────────     Configuration, database engine, security primitives,
                       logging, middleware, RBAC catalogue, cache, exceptions.
```

The engine layer being pure is the load-bearing decision. `ai/matching.py`
takes a candidate profile and an opportunity as dataclasses and returns a score
with its contributions. It can be tested with a dictionary; it cannot
accidentally perform a query inside a loop; and it produces the same answer for
the same input every time.

## Request lifecycle

```
1.  Request arrives
        │
2.  RequestContextMiddleware
        ├─ assigns or propagates X-Request-ID
        └─ binds it to the structured logger for this request
        │
3.  SecurityHeadersMiddleware
        └─ CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy,
           Permissions-Policy, HSTS (production only)
        │
4.  RateLimitMiddleware
        ├─ per-IP token bucket
        ├─ tighter bucket for /auth/* (default 10/min)
        └─ 429 with Retry-After when exhausted
        │
5.  CSRFMiddleware
        ├─ bearer-authenticated requests: exempt by construction
        └─ cookie-authenticated mutations: double-submit token required
        │
6.  CORS
        └─ explicit origin list; never a wildcard in production
        │
7.  Route resolution → dependency injection
        ├─ get_db            async session, one per request
        ├─ get_current_user  decodes the access token, loads the user
        └─ require(perm)     RBAC check against the session's permissions
        │
8.  Pydantic validates the request body and query parameters
        │
9.  Endpoint calls a service function
        │
10. Service executes business logic inside one transaction
        ├─ may call the pure engine layer
        ├─ may enqueue a Celery task
        └─ writes an audit entry for security-relevant actions
        │
11. Response model serialises the result
        │
12. Envelope wraps it: { success, data, meta }
        │
13. Response returns with the request id attached
```

Errors take a parallel path: domain exceptions carry a machine-readable code
and are mapped by a single exception handler to
`{ success: false, error: { code, message, details } }`. Nothing leaks a
stack trace, and nothing returns a bare 500 for a condition the application
anticipated.

## Frontend architecture

```
app/                    App Router. Layouts are server components; anything
                        interactive is a client component.
  (marketing)/          public landing page
  (auth)/               login, register, forgot/reset password, verify email
  student/              15 routes
  industry/             11 routes
  academician/          7 routes
  institution/          9 routes
  admin/                10 routes
  opportunities/        public browsing and detail
  companies/[slug]/     public company profile
  portfolio/[slug]/     public portfolio

features/               One module per screen. Owns its queries, mutations and
                        local state. Screens are composed from primitives, not
                        from other screens.

components/ui/          The design system: button, card, badge, input, field,
                        progress, score ring, dialog, tabs, table, tooltip,
                        avatar, stat, skeletons, empty/error/query states.

components/layout/      Dashboard shell, navigation configuration, command
                        palette, notification menu, page header.

lib/api.ts              The only place that talks to the API. Attaches the
                        bearer token, refreshes once on a 401 and replays,
                        unwraps the envelope, converts errors to ApiError.

lib/auth.tsx            Session context. Exposes can() and hasRole() so the UI
                        hides what the API would refuse — presentation only;
                        the server remains the authority.

lib/query.tsx           TanStack Query client with shared defaults.

types/api.ts            Mirrors the API contract. Contract tests assert it
                        stays in step with the backend enums.
```

### Data fetching

TanStack Query owns server state. Every data view uses `QueryState`, which
renders exactly one of four things: a skeleton, an error with a retry, an empty
state, or the data. There is no path through the component that renders
nothing, which is what stops blank screens.

Mutations invalidate the query keys they affect, so a recruiter shortlisting an
applicant updates the list, the counts and the detail panel without a manual
refetch.

### Token refresh

A 401 triggers one refresh, and the original request is replayed with the new
token. Concurrent 401s collapse into a single refresh call — a second rotation
would invalidate the first and sign the user out mid-session. This is
single-flight, tested, and lives in one function.

## Background work

Celery handles what should not block a request:

| Task | Trigger |
| --- | --- |
| Send email | On registration, password reset, application status change, interview scheduling |
| Recompute recommendations | After an assessment, a profile change, or a new posting |
| Refresh skill demand | Scheduled; derived from live postings |
| Daily digest | Scheduled |
| Expire stale postings | Scheduled |

When no worker is running, `CELERY_TASK_ALWAYS_EAGER=true` executes tasks
inline. Development and the test suite need no broker.

## Caching

A two-tier cache: Redis when available, an in-process dictionary when not.
Cache failures are logged at debug level and fall through — a request never
fails because the cache is down. Cached reads are limited to expensive
aggregate queries (skill demand, platform statistics, analytics roll-ups), and
every write path invalidates by prefix.

## Storage

Documents go to S3-compatible storage (MinIO in development). Uploads are
validated by magic bytes rather than by the declared content type, checked
against an allow-list and a size limit, stored under randomised names, and
served only through signed URLs that expire. A path-containment check prevents
a crafted filename from escaping its prefix.

## Dialect portability

The application runs on PostgreSQL and SQLite from the same code.

```python
class JSONB(TypeDecorator):
    """PostgreSQL JSONB where available, portable JSON elsewhere."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.JSONB())
        return dialect.type_descriptor(JSON())
```

This is one importable symbol, which matters because Alembic renders type names
into generated migrations: `with_variant(...)` produced code that did not
import. Identifiers use `sa.Uuid`, which maps to native `uuid` on PostgreSQL
and to a stable representation on SQLite.

The payoff is that `pytest` runs with no infrastructure at all, while CI
additionally applies every migration to a real PostgreSQL instance and seeds it
— so the portable path and the production path are both proven on every commit.
