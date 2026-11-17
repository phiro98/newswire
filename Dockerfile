# ==============================================================================
# Multi-Stage Dockerfile for Newswire Compliance & Intelligence Monitor
# Optimized for Python 3.11, newspaper4k, lxml, and NLTK NLP models
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build & Compilation Stage
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies for C-extensions (lxml, Pillow, psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment to isolate dependencies cleanly
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download required NLTK datasets so container functions offline / without internet at runtime
RUN mkdir -p /opt/nltk_data && \
    python -m nltk.downloader -d /opt/nltk_data punkt punkt_tab stopwords vader_lexicon

# ------------------------------------------------------------------------------
# Stage 2: Final Production Runtime Stage (Lean & Secure)
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runner

LABEL maintainer="Newswire AI Platform Team" \
      version="2.0.0" \
      description="Production container for Newswire Compliance Monitor"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    NLTK_DATA="/opt/nltk_data" \
    PYTHONPATH="/app"

# Install only essential runtime C libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user for security compliance
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 -m -s /sbin/nologin appuser

WORKDIR /app

# Copy isolated virtual environment and pre-downloaded NLTK models from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/nltk_data /opt/nltk_data

# Copy application source code and frontend
COPY app /app/app
COPY index.html /app/index.html
COPY styles.css /app/styles.css
COPY app.js /app/app.js

# Prepare persistent storage directories and assign permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appgroup /app /opt/nltk_data

USER appuser

# Healthcheck probe for orchestrators (Docker Swarm, Kubernetes, Docker Compose)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Start production ASGI server with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
