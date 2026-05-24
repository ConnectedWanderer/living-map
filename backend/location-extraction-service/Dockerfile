ARG DEPS_IMAGE=living-map/le-deps
FROM ${DEPS_IMAGE} AS deps

FROM python:3.14-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    SPACY_EN_MODEL=en_core_web_sm \
    SPACY_FR_MODEL=fr_core_news_sm \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=deps /app/.venv/ ./.venv/

COPY src/ ./src/

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
