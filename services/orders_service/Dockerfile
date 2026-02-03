# ---------- build stage ----------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definitions first for better caching
COPY pyproject.toml ./
COPY README.md ./README.md

# Install build tooling
RUN pip install --upgrade pip setuptools wheel

# Build wheel
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .


# ---------- runtime stage ----------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Runtime OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip install --upgrade pip && pip install --no-cache-dir /wheels/*

# Copy application source
COPY . .

# Expose service port
EXPOSE 8000

# Health check (matches ALB target group)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Run app (adjust module path if needed)
CMD ["sh", "-c", "uvicorn services.orders_service.app.main:app --host 0.0.0.0 --port ${PORT}"]
