# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install uv for high-performance reproducible dependency management
COPY --from=ghcr.io/astral-sh/uv:0.5.26 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

WORKDIR /usr/src/app

# Install essential system build dependencies and curl for healthcheck
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libssl-dev \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root unprivileged service user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy requirements file first for layer caching
COPY requirements.txt .

# Install Python dependencies using uv with persistent cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -r requirements.txt

# Create runtime directories including ChromaDB persistence directory
RUN mkdir -p /usr/src/app/chroma_db && \
    chown -R appuser:appgroup /usr/src/app

# Copy application source code
COPY . .
RUN chown -R appuser:appgroup /usr/src/app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
