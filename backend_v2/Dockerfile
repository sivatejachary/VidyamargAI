# VidyaMarg AI — Job Discovery Platform Dockerfile
# =================================================
# Multi-stage build for minimal production image size
# Base: Python 3.12-slim

# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production
FROM python:3.12-slim AS production

LABEL maintainer="VidyaMarg AI <eng@vidyamarg.ai>"
LABEL version="2.0.0"
LABEL description="Autonomous Job Discovery Platform"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r jduser && useradd -r -g jduser jduser

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create directories for sessions and storage
RUN mkdir -p /app/sessions /app/logs && \
    chown -R jduser:jduser /app

USER jduser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -sf http://localhost:8100/health || exit 1

EXPOSE 8100

# Default: Start FastAPI server
# Override CMD to start Celery worker:
# CMD ["celery", "-A", "app.job_discovery.workers.celery_app", "worker", "--loglevel=info", "-Q", "discovery"]
CMD ["uvicorn", "app.job_discovery.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8100", \
     "--workers", "4", \
     "--log-level", "info"]
