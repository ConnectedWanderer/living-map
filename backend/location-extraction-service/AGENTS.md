# AI Agent Instructions

This document provides AI-specific guidance for developing or maintaining this service.
For human-oriented documentation, see [README.md](README.md).

For architecture details, see [Architecture Documentation](../../docs/architecture/location-extraction.md).
For evaluation guide, see [Evaluation Guide](../../docs/evaluation.md).

## Quick Commands

```bash
# Test (fast path — unit only, no model downloads)
uv run python -m pytest -m "not model_dependent" --cov=src --cov-report=term-missing

# Test (full suite — requires spaCy models)
uv run python -m pytest --cov=src --cov-report=term-missing

# CI entry point
bash scripts/ci.sh          # full suite
bash scripts/ci.sh --fast   # unit only

# Lint & format
uv run ruff check . && uv run ruff format .

# Evaluation
uv run python -m src.evaluation
uv run python -m src.evaluation --geocoding
uv run python -m src.evaluation path/to/corpus.json

# Corpus offset check/fix
uv run python scripts/fix_corpus_offsets.py --check
uv run python scripts/fix_corpus_offsets.py

# Docker
docker-compose up --build
```

## Development Workflow

### TDD Approach

1. Write tests first in `tests/`
2. Run tests: `uv run pytest tests/ -v`
3. Implement to make tests pass
4. Refactor as needed

### Adding New Languages

1. Download spaCy model: `uv run python -m spacy download {lang}_core_news_sm`
2. Update `_MODEL_MAP` in `src/pipeline.py`
3. Add tests for new language
4. Update Dockerfile to download new model

### Adding New Components

1. Create module in appropriate `src/` subdirectory
2. Add corresponding test file in `tests/`
3. Update `src/orchestrator.py` to integrate new component
4. Update integration tests

## Code Conventions

Ruff is configured in `pyproject.toml`:

- **Line length**: 100
- **Target Python**: 3.14
- **Enabled rules**: E, W, F, I (isort), UP (pyupgrade), B (bugbear), C4 (comprehensions), RUF

Python syntax:

- **Exception handling**: Use modern Python syntax for multiple exceptions (Python 3.14+), e.g., `except Exception1, Exception2:`
- **Docstrings**: Google-style on all public classes and methods. Module-level docstrings describe the file's purpose. Private functions (`_`-prefixed) do not require docstrings (ruff rule `D`).

## Structure

```
src/
├── app.py               # FastAPI server + DI
├── schemas.py           # Pydantic GeoJSON schemas
├── models.py            # Typed dataclasses
├── pipeline.py          # NerPipeline (stages 1-2)
├── geocoding.py         # GeoPipeline (stage 3)
├── disambiguator.py     # DisambiguatePipeline (stage 4)
├── orchestrator.py      # LocationPipeline (all stages)
└── evaluation/          # NER & geocoding evaluation
```

See `docs/architecture/location-extraction.md` for the full annotated tree.

## Troubleshooting

| Symptom                  | Fix                                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------------------ |
| Dependencies not found   | `uv sync`                                                                                                    |
| spaCy model not found    | `uv run python -m spacy download en_core_web_sm fr_core_news_sm`                                             |
| Slow startup             | Models cache after first load. Subsequent startups are faster.                                               |
| CI fails (missing model) | Run `bash scripts/ci.sh` which downloads models first. For quick unit-only pass: `bash scripts/ci.sh --fast` |

## uv Commands Reference

| Command                                            | Description                              |
| -------------------------------------------------- | ---------------------------------------- |
| `uv sync`                                          | Install all dependencies (creates .venv) |
| `uv sync --dev`                                    | Include dev dependencies                 |
| `uv sync --no-dev`                                 | Exclude dev dependencies                 |
| `uv run python -m pytest`                          | Run full test suite                      |
| `uv run python -m pytest -m "not model_dependent"` | Run unit tests only                      |
| `uv run ruff check`                                | Lint code                                |
| `uv run ruff format`                               | Format code                              |
| `uv lock`                                          | Update lock file                         |
| `uv sync --frozen`                                 | Install without updating lock (CI/CD)    |

## Related Documentation

- [README.md](README.md) — End-user documentation (setup, API, Docker)
- [Architecture Documentation](../../docs/architecture/location-extraction.md) — Deep design doc
- [Evaluation Guide](../../docs/evaluation.md) — NER & geocoding evaluation protocol
- [ADR-001](../../docs/decisions/ADR-001-location-extraction-approach.md) — Location extraction approach
- [ADR-002](../../docs/decisions/ADR-002-ner-evaluation-protocol.md) — NER evaluation protocol
- [ADR-006](../../docs/decisions/ADR-006-pipeline-architectural-improvements.md) — Pipeline architectural improvements
- [ADR-007](../../docs/decisions/ADR-007-replace-text2geo-with-geonamescache.md) — text2geo → geonamescache
- [ADR-008](../../docs/decisions/ADR-008-geocoding-evaluation-corpus.md) — Geocoding evaluation corpus
