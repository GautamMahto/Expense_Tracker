FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY expense_bot ./expense_bot
RUN pip install --upgrade pip && pip install .

# Migrations and remaining project files.
COPY alembic.ini ./
COPY alembic ./alembic

# Run as a non-root user.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "expense_bot.main"]
