FROM python:3.11-slim AS build

RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/sh app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY src/ /app/src/
COPY data/ /app/data/
RUN chown -R app:app /app
USER app

ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app/src PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8080/health || exit 1

CMD ["sh", "-c", "uvicorn protobox.admin.main:app --host 0.0.0.0 --port ${PORT}"]
