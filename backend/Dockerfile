# syntax=docker/dockerfile:1
# ---------------------------------------------------------------- builder --
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Build-only toolchain; not carried into the runtime image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# ---------------------------------------------------------------- runtime --
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    # Run as an unprivileged user: a container is not a security boundary on
    # its own, so drop root inside it too.
    && groupadd --system --gid 1001 skillbridge \
    && useradd --system --uid 1001 --gid skillbridge --create-home skillbridge

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=skillbridge:skillbridge . .

RUN mkdir -p /app/var/uploads && chown -R skillbridge:skillbridge /app/var

USER skillbridge
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
