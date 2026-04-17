FROM python:3.14-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_COMPILE_BYTECODE=1 \
    SPACY_EN_MODEL=en_core_web_sm \
    SPACY_FR_MODEL=fr_core_news_sm

RUN pip install --no-cache-dir uv

COPY pyproject.toml .

RUN uv sync --frozen --no-dev

RUN --mount=type=cache,target=/root/.cache \
    uv run python -m spacy download ${SPACY_EN_MODEL} && \
    uv run python -m spacy download ${SPACY_FR_MODEL}

RUN --mount=type=cache,target=/root/.cache \
    uv run python -c "from text2geo import Geocoder; Geocoder(dataset='world')"

COPY src/ ./src/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src:app", "--host", "0.0.0.0", "--port", "8000"]
