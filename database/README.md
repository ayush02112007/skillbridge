# Database

Everything needed to create the SkillBridge database from scratch. Nothing
here depends on an existing local database.

```
database/
├── schema/
│   ├── schema.sql            flattened PostgreSQL DDL — 79 tables (generated)
│   └── generate_schema.py    regenerates schema.sql from the models
├── init/
│   └── 01-extensions.sql     runs once on an empty PostgreSQL data directory
└── README.md
```

## Where the rest lives

Two things a reader might expect here are deliberately elsewhere, because
moving them would break the tools that own them:

| Artefact | Location | Why there |
| --- | --- | --- |
| Alembic migrations | `backend/migrations/` | `alembic.ini` resolves `script_location` relative to the backend package, and `migrations/env.py` imports `app.core.database` for the custom `JSONB` type. The API image's build context is `backend/`, so a migration outside it would not be in the image that runs `alembic upgrade head`. |
| Seed data and scripts | `backend/seeds/` | Run as `python -m seeds.seed`; the module imports `app.services` and `app.models` directly. It is a Python package inside the backend, not standalone SQL. |
| SQLAlchemy models | `backend/app/models/` | 79 mapped classes; the models *are* the schema definition that everything else derives from. |

## Creating a database from scratch

### With Docker (nothing to install)

```bash
cp .env.example .env
docker compose up --build
```

`docker-compose.yml` starts PostgreSQL 16, mounts `database/init/` so the
extensions are created on the empty volume, and the API entrypoint then waits
for the database, runs `alembic upgrade head`, and seeds (because
`SEED_ON_START=true` in development).

### Against your own PostgreSQL

```bash
createdb skillbridge
psql skillbridge -f database/init/01-extensions.sql

cd backend
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/skillbridge"
alembic upgrade head
python -m seeds.seed
```

### Without PostgreSQL at all

SQLite is fully supported — the same code, the same migrations, the same test
suite. Useful for development and required for nothing.

```bash
cd backend
export DATABASE_URL="sqlite+aiosqlite:///./var/skillbridge.db"
alembic upgrade head
python -m seeds.seed
```

### From the flattened schema, skipping Alembic

```bash
createdb skillbridge
psql skillbridge -f database/init/01-extensions.sql
psql skillbridge -f database/schema/schema.sql

# Then mark the migration chain as already applied, or Alembic will try to
# create everything a second time:
cd backend && alembic stamp head
```

## Migrations

```bash
cd backend
alembic upgrade head                      # apply everything
alembic downgrade -1                      # roll back one
alembic current                           # where am I
alembic history --verbose                 # what exists
alembic revision --autogenerate -m "..."  # new migration from model changes
```

After changing a model, regenerate the flattened schema so it does not drift:

```bash
cd backend && python ../database/schema/generate_schema.py
```

CI applies the whole chain to a real PostgreSQL instance on every commit,
rolls it back to base, applies it again, and then seeds — so the migrations
are proven forwards *and* backwards, not just forwards.

## Seeding

```bash
cd backend
python -m seeds.seed                   # catalogue + demo dataset
python -m seeds.seed --catalog-only    # taxonomy and assessments only
python -m seeds.seed --reset           # drop, recreate, reseed
python -m seeds.seed --students 200    # a larger cohort
```

The seeder is deterministic — the same seed produces the same data — and
refuses to run when `ENVIRONMENT=production`. Every row it writes is flagged
`is_demo = true`, so demo data is identifiable and removable.

It loads a curated catalogue of **128 skills** across 14 categories, **31 job
roles** with **315 role–skill links**, and an assessment bank of **50 scored
questions plus 8 Likert items**, then generates institutions, companies,
postings, students with assessment histories, applications, mentors, events,
research and partnerships.

## What the schema contains

79 tables. See [`../docs/er-diagram.md`](../docs/er-diagram.md) for the
relationships, grouped by domain, and the reasoning behind the two structural
decisions (joined-table inheritance for opportunities, and the snapshotted
match score on applications).

Invariants are enforced in the database, not only in application code:

| Constraint | Table | What it prevents |
| --- | --- | --- |
| `one_applicant_identity` | `applications` | An application with both a student and an academician, or neither |
| `score` range 0–100 | `student_skills` | An out-of-range proficiency score (this caught a real seeder bug) |
| `UNIQUE (opportunity_id, student_id)` | `applications` | A duplicate application from a race between two tabs |
| `UNIQUE (student_id, skill_id)` | `student_skills` | Two rows for the same skill |
| `UNIQUE (slug)` | `portfolios`, `companies`, `institutions`, `skills`, `job_roles` | Ambiguous public URLs |

Every foreign key is indexed, and composite indexes cover the sort and filter
paths the marketplace and the applicant queue actually use.

## PostGIS

Not used. Locations are stored as city and state strings and matched
textually — there is no geometry column, no spatial index and no distance
query in the codebase. `database/init/01-extensions.sql` says the same thing,
and points at what to change if geographic matching is ever added.
