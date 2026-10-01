# Scalability

## Where this actually stands

The application is built to run correctly, not to run at a million users. It
has been exercised with a seeded dataset in the hundreds of students and
thousands of rows. Everything below about larger scale is reasoning from the
architecture, not a measured result — and it is worth saying so plainly,
because a scalability document full of unmeasured numbers is worse than none.

What *is* true today:

- Stateless API processes, so horizontal scaling needs no session affinity.
- All database access is async; the process is not blocked on I/O.
- Connection pooling with configurable size and overflow.
- Background work is already off the request path, in Celery.
- The frontend is a standalone Next.js build behind a CDN-friendly Nginx.
- Analytics aggregates are cached; individual results deliberately are not.

---

## Known bottlenecks, in the order they would bite

### 1. Per-row match scoring in list endpoints

The marketplace computes a match score for every posting it returns, for the
signed-in student. That is `O(postings × requirements)` per request. It is fine
at a page size of 20 and a few hundred postings. It is the first thing that
would hurt at ten thousand postings and a thousand concurrent students.

**What would change.** Precompute and store scores. `recommendations` already
exists as a table with `student_id`, `target_id`, `score` and `reasons`; the
Celery task that refreshes recommendations already writes it. The marketplace
would read from it and fall back to live computation only for combinations not
yet materialised. The work moves from request time to the existing background
job, which is already triggered by the events that invalidate a score — an
assessment, a profile change, a new posting.

### 2. Skill-gap recomputation

Each gap analysis walks a student's skills against a role's requirements.
Cheap individually; expensive when an institution's dashboard asks for the
distribution across 5,000 students.

**What would change.** `skill_gap_analyses` and `skill_gap_items` are already
persisted, so the aggregate reads from stored analyses rather than recomputing.
Refresh moves to a scheduled job and to the events that invalidate an analysis.

### 3. Notification fan-out

Publishing a posting notifies every matching student. At scale that is one
query and a large number of inserts and emails.

**What would change.** Batch the inserts, chunk the email sends across worker
tasks, and collapse per-event emails into a digest — the digest task already
exists.

### 4. Full-text search

Search uses a portable `lower(column) LIKE '%needle%'` across a few columns —
deliberately dialect-neutral so it behaves the same on SQLite and PostgreSQL.
It is correct and adequate at the current data volume, but a leading wildcard
cannot use a B-tree index, so it will not hold up.

**What would change.** PostgreSQL full-text search with a GIN index on a
generated `tsvector` column is the next step and needs no new infrastructure.
Beyond that, OpenSearch — but only when the query patterns genuinely justify a
second system to operate.

### 5. Analytics roll-ups

Institution and platform analytics aggregate across the whole dataset. Cached,
but a cold cache after an invalidation is a slow request.

**What would change.** Materialised views refreshed on a schedule, or summary
tables maintained incrementally. The read path already goes through a cache
layer, so swapping the source is contained.

---

## Scaling stages

### Stage 1 — one machine (where it is now)

```
  Nginx ──┬── Next.js
          └── FastAPI ── PostgreSQL
                      ── Redis ── Celery worker
```

Fine for a single institution: hundreds of concurrent users, thousands of
students. `docker compose up` is the whole deployment.

### Stage 2 — horizontal API

```
              ┌── FastAPI ─┐
  Nginx / LB ─┼── FastAPI ─┼── PostgreSQL (primary)
              └── FastAPI ─┘── Redis
                            ── Celery workers ×N
```

The API processes are already stateless, so this needs no code change — the
production compose overlay sets `replicas: 2` today. The in-process rate
limiter becomes approximate across replicas, which is why Nginx also limits;
making the application limiter exact would mean moving its counters into Redis,
which is a small, contained change.

### Stage 3 — read replicas

```
  API ──── writes ────▶ PostgreSQL primary
      └─── reads ─────▶ replica ×N
```

The read/write split is the work here. Session factories would need a routing
layer, and every read path would need classifying for replication-lag
tolerance: a student's own application list cannot tolerate lag; the public
opportunity browser can.

### Stage 4 — partitioning and archival

The tables that grow without bound are `audit_logs`, `notifications`,
`email_logs` and `application_status_history`. All four are time-ordered and
rarely queried outside a recent window — natural candidates for monthly range
partitioning, with older partitions detached to cold storage.

---

## Frontend scaling

The Next.js build already emits a standalone bundle and is served by a
non-root Node process behind Nginx, with immutable caching for `/_next/static`.

The next steps, in order of value:

1. **Static generation for public pages.** The landing page, public company
   profiles and public portfolios change rarely and are currently rendered per
   request. ISR would remove almost all of that load.
2. **CDN in front of Nginx.** Static assets first; then cached public pages.
3. **Route-level code splitting.** The App Router splits by route already; the
   heavy chart bundle could be lazily loaded on the dashboards that need it.

---

## Database practices already in place

- Every foreign key is indexed.
- Composite indexes cover the sort and filter paths the marketplace and the
  applicant queue actually use, rather than every column speculatively.
- Eager loading is explicit (`selectinload`, `joinedload`) on the paths that
  need it. `lazy="raise"` on the collections where a silent lazy load would be
  a bug means an N+1 fails loudly in development instead of quietly in
  production.
- Pagination is mandatory on list endpoints, with a server-side cap on
  `page_size`.
- Transactions are scoped to a service function, not held open across I/O.

---

## What would need to be added

Honestly: these do not exist yet.

| Area | Current state | What is needed |
| --- | --- | --- |
| Metrics | Structured logs with request ids and durations | Prometheus metrics endpoint, dashboards, alerting |
| Tracing | Request id propagated end to end | OpenTelemetry spans across API, worker and database |
| Load testing | None | A k6 or Locust suite establishing an actual baseline |
| Query analysis | None | `pg_stat_statements` and slow-query logging in production |
| Blue/green | Compose restarts in place | A deployment strategy with health-gated cutover |
| Backups | Documented as the operator's responsibility | Automated, monitored, with a tested restore |
| Multi-tenancy | Row-level scoping by institution and company | Row-level security, or separate schemas, if isolation must be structural |

---

## What would not change

Worth stating, because it constrains everything above:

- **The engine stays deterministic and pure.** Precomputing scores moves *when*
  they are computed, never *how*. The same inputs must always give the same
  score, and it must still arrive with its derivation.
- **Explainability survives caching.** A precomputed score is stored together
  with its reasons. A cached recommendation that lost its explanation would be
  worse than a slow one.
- **The database stays the system of record.** Caches and derived tables are
  disposable; the constraints that protect the data stay where they are.
- **Scores stay snapshotted on applications.** No amount of scaling justifies
  recomputing a score a recruiter is already looking at.
