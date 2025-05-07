############################################################
#  MediArch — container image             (uv edition)
############################################################
FROM python:3.13-alpine AS runtime

# ── Environment ────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# ── Install uv ──────────────────────
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

# ── Python dependencies (cached layer) ─────────────────────
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# ── Copy application source last ───────────────────────────
COPY src ./src

# ── Runtime config ─────────────────────────────────────────
ENV FLASK_APP="mediarch:create_app" \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=8000 \
    PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uv", "run", "flask", "run"]