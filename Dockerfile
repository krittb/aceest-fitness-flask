# syntax=docker/dockerfile:1

# ---------- base ----------
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# ---------- builder: install runtime deps only ----------
FROM base AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- test: dev deps + tests (used by CI via `--target test`) ----------
FROM base AS test
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY app.py test_app.py ./
COPY templates ./templates
COPY static ./static
CMD ["pytest", "-v", "--cov=app", "--cov-report=term-missing"]

# ---------- runtime: final, minimal, non-root (default target) ----------
FROM base AS runtime
LABEL org.opencontainers.image.title="ACEest Fitness & Gym" \
      org.opencontainers.image.description="Flask-based fitness club management app"

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --no-create-home --shell /usr/sbin/nologin appuser

COPY --from=builder /install /usr/local
COPY app.py ./
COPY templates ./templates
COPY static ./static
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
