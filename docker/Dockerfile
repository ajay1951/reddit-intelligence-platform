# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install uv for high-performance dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Ensure uv uses the system environment instead of creating a venv inside the container
ENV UV_SYSTEM_PYTHON=1

WORKDIR /usr/src/app

# Install essential system build dependencies using BuildKit cache mounts
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libssl-dev \
    ca-certificates

# Copy only requirements.txt first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies using uv with a persistent cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -r requirements.txt

# Install Playwright browsers and their system-level dependencies.
# We do this after installing Python packages so the 'playwright' CLI is available.
RUN playwright install --with-deps

# Copy the rest of the application code last, as it changes most frequently
COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.scripts.run_scraper:app", "--host", "0.0.0.0", "--port", "8000"]
