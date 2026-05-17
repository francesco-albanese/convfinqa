FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Two-step uv sync: deps first (cached while uv.lock is unchanged), project
# second after backend/src/ is copied. Splitting them keeps the dep layer warm
# across code-only edits.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/src/ ./backend/src/
COPY backend/alembic/ ./backend/alembic/
COPY data/ ./data/
COPY alembic.ini README.md ./
RUN uv sync --frozen --no-dev


FROM python:3.13-slim-bookworm

RUN useradd --system --create-home --uid 1000 convfinqa

WORKDIR /app

COPY --from=builder --chown=convfinqa:convfinqa /app /app
COPY --chown=convfinqa:convfinqa backend/scripts/docker-entrypoint.sh /app/scripts/docker-entrypoint.sh
RUN chmod +x /app/scripts/docker-entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER convfinqa
EXPOSE 8000

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
