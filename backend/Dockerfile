# =============================================================================
# AI-Assisted Office Layout Generation Platform - Backend Dockerfile
# Python 3.11 Multi-Stage Container Build
# =============================================================================

FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies (GEOS, GDAL for Shapely/PostGIS capabilities)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgeos-dev \
    libgdal-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY pyproject.toml README.md /app/

# Copy application source code
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

# Expose HTTP port
EXPOSE 8000

# Default launch command with Uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
