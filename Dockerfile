# syntax=docker/dockerfile:1
# Production image for the website, run by researchit-deploy (stacks/web).
# Build: docker build -t researchit-website .

ARG PYTHON_VERSION=3.12

# --- build: install locked dependencies with uv, collect static files ----------
FROM python:${PYTHON_VERSION}-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /bin/uv
# Venv outside /app; use the image's Python, never download one; copy (not
# hardlink) from the cache mount; precompile bytecode for faster startup.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
# Dependencies first (cached layer until pyproject.toml/uv.lock change).
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev
COPY . /app
# Production settings need these at import time; the values are build-only.
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_SECRET_KEY=build-only \
    DATABASE_URL=sqlite:////tmp/build.sqlite3 \
    python manage.py collectstatic --noinput

# --- runtime: slim image, non-root user, no build tooling -----------------------
FROM python:${PYTHON_VERSION}-slim-trixie
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_LOG_FORMAT=json
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
 && mkdir -p /app/media \
 && chown app:app /app/media
COPY --from=build /opt/venv /opt/venv
COPY --from=build /app /app
WORKDIR /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"]
# 2 workers is plenty for a mostly static site on 2 vCPU. /tmp is a tmpfs
# (the container's root filesystem is read-only).
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--worker-tmp-dir", "/tmp", \
     "--access-logfile", "-", \
     "--forwarded-allow-ips", "*"]
