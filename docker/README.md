# Docker

```
docker/
├── nginx/
│   ├── nginx.conf            reverse proxy: TLS, rate limiting, headers
│   ├── proxy_params_sb       shared proxy_set_header block
│   └── certs/                mount fullchain.pem and privkey.pem here
└── README.md
```

The Dockerfiles themselves live with the code they build — `backend/Dockerfile`
and `frontend/Dockerfile` — because a Dockerfile must sit inside its build
context. Moving them here would mean setting the build context to the
repository root and shipping the whole tree into both images.

| File | Purpose |
| --- | --- |
| `backend/Dockerfile` | API image. `python:3.12-slim`, multi-stage, runs as non-root uid 1001. |
| `backend/docker-entrypoint.sh` | Waits for the database, runs `alembic upgrade head`, optionally seeds, then execs the command. |
| `backend/.dockerignore` | Keeps `.venv`, `var/`, `__pycache__` and tests out of the image. |
| `frontend/Dockerfile` | Web image. `node:22-alpine`, multi-stage, Next.js standalone output, non-root uid 1001. |
| `frontend/.dockerignore` | Keeps `node_modules`, `.next` and test output out of the build context. |
| `database/init/` | SQL run once on an empty PostgreSQL volume. |
| `docker-compose.yml` | The full development stack. |
| `docker-compose.prod.yml` | Production overlay: TLS via nginx, required secrets, no seeding. |

## Development

```bash
cp .env.example .env
docker compose up --build
```

| Service | Image | Port | Notes |
| --- | --- | --- | --- |
| `postgres` | postgres:16-alpine | 5432 | Init scripts from `database/init/` |
| `redis` | redis:7-alpine | 6379 | Cache (db0), Celery broker (db1), results (db2) |
| `minio` | minio/minio | 9000, 9001 | S3-compatible document storage |
| `minio-init` | minio/mc | — | Creates the bucket, then exits |
| `mailpit` | axllent/mailpit | 8025, 1025 | Captures every email; nothing leaves the machine |
| `api` | built from `backend/` | 8000 | Migrates and seeds on first boot |
| `worker` | built from `backend/` | — | Celery worker |
| `beat` | built from `backend/` | — | Celery scheduler |
| `web` | built from `frontend/` | 3000 | Next.js standalone server |

Useful commands:

```bash
docker compose ps                        # what is running
docker compose logs -f api               # follow the API
docker compose exec api alembic current  # migration state
docker compose exec api python -m seeds.seed --reset
docker compose exec postgres psql -U skillbridge skillbridge
docker compose down                      # stop, keep data
docker compose down -v                   # stop and delete the volumes
```

## Production

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"   # per secret

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The overlay sets `ENVIRONMENT=production`, turns off seeding and debug, stops
publishing the database and cache ports to the host, requires every secret to
be present (compose fails fast if one is missing), and puts nginx in front as
the only exposed service.

Put your certificate and key in `docker/nginx/certs/` as `fullchain.pem` and
`privkey.pem`.

The API refuses to start in production if `JWT_SECRET` or `JWT_REFRESH_SECRET`
is still a development sentinel, if the two are equal, if `DEBUG` is on, if
`SECURE_COOKIES` is off, or if `CORS_ORIGINS` or `TRUSTED_HOSTS` contains a
wildcard. See `backend/app/core/config.py:validate_runtime`.

## Notes on the images

**Both run as non-root.** uid 1001 in each, with the application directory
owned by that user.

**Both are multi-stage.** Build dependencies do not reach the runtime layer.
The web image ships Next.js `output: "standalone"`, which is a self-contained
server bundle rather than the whole `node_modules` tree.

**`NEXT_PUBLIC_*` values are baked in at build time.** They are compiled into
the JavaScript bundle, so changing `NEXT_PUBLIC_API_URL` requires a rebuild,
not a restart. Only public configuration belongs in those variables — never a
key or a secret.

**The API waits for the database itself** rather than relying on compose's
`depends_on` alone, because a healthy container is not the same as a database
ready to accept the first connection.
