FROM python:3.14-slim
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    SPACY_EN_MODEL=en_core_web_sm \
    SPACY_FR_MODEL=fr_core_news_sm

COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev && \
    uv pip install pip && \
    uv run --no-sync python -m spacy download ${SPACY_EN_MODEL} && \
    uv run --no-sync python -m spacy download ${SPACY_FR_MODEL} && \
    uv cache clean && \
    uv pip uninstall uv pip -y && \
    rm -f /app/.venv/lib/python3.14/site-packages/geonamescache/data/cities1000.json \
          /app/.venv/lib/python3.14/site-packages/geonamescache/data/cities15000.json \
          /app/.venv/lib/python3.14/site-packages/geonamescache/data/cities5000.json && \
    find /app/.venv -name '*.so' -exec strip --strip-unneeded {} + 2>/dev/null; \
    find /app/.venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
    find /app/.venv -name '*.pyc' -delete

COPY src/ ./src/

USER appuser
# DATABASE_URL must be set at runtime
CMD [".venv/bin/python", "-c", "from src.app import main; main()"]