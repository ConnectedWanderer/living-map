# AI Agent Instructions

This document provides guidance for AI agents developing or maintaining this service.

## Architecture

The service follows a 4-stage NLP pipeline:

```
Input Text → Language Detection → spaCy NER → geonamescache Geocoder → Event Location Inference → GeoJSON FeatureCollection
```

### Components

| File                            | Purpose                                                                                                                                                                                      |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/models.py`                 | Typed dataclasses: EntityMention, GeocodedLocation, ScoredLocation, GeocodeResult, EntityResult, EventLocation, LocationResult                                                               |
| `src/pipeline.py`               | `NerPipeline` class + `NerResult` dataclass + internal detection/NER/model logic                                                                                                             |
| `src/geocoding.py`              | `GeoPipeline` class + `GeoResult` dataclass + internal text2geo wrapper (injectable geocode_fn)                                                                                              |
| `src/disambiguator.py`          | `DisambiguatePipeline` class + `DisambiguateResult` dataclass + event location inference (Stage 4)                                                                                           |
| `src/orchestrator.py`           | `LocationPipeline` class composing all 4 stages into a single `.run(text) -> LocationResult` seam                                                                                            |
| `src/app.py`                    | FastAPI server with `POST /api/extract-location`, `GET /health`, injectable pipeline via `Depends`                                                                                           |
| `src/schemas.py`                | Pydantic request/response schemas (GeoJSON FeatureCollection, GeoFeature, GeocodingMetadata, etc.)                                                                                           |
| `src/evaluation/__init__.py`    | Pure evaluation computation: `evaluate()`, `evaluate_geocoding()`, `evaluate_event_location()`                                                                                               |
| `src/evaluation/runner.py`      | Orchestration: `run_pipeline_on_corpus()`, `evaluate_corpus()`, `evaluate_all_corpora()`, `run_full_pipeline_on_corpus()`, `evaluate_geocoding_corpus()`, `evaluate_geocoding_all_corpora()` |
| `src/evaluation/__main__.py`    | CLI entry point: `uv run python -m src.evaluation` (supports `--geocoding` flag)                                                                                                             |
| `scripts/fix_corpus_offsets.py` | Corpus offset validation and repair                                                                                                                                                          |
| `scripts/ci.sh`                 | CI entry point: `--fast` for unit-only, otherwise downloads models + full suite                                                                                                              |

## Development Setup

This project uses [uv](https://github.com/astral-sh/uv) for fast, deterministic Python package management.

### Initial Setup

```bash
cd backend/location-extraction-service

# Install all dependencies including dev tools (creates .venv automatically)
uv sync

# If dev dependencies not installed, run:
uv sync --dev

# Download spaCy small models
uv run python -m spacy download en_core_web_sm
uv run python -m spacy download fr_core_news_sm

# (No geocoder data download needed — geonamescache ships data with the package)
```

### Development Workflow

#### TDD Approach

1. Write tests first in `tests/`
2. Run tests: `uv run pytest tests/ -v`
3. Implement to make tests pass
4. Refactor as needed

#### Adding New Languages

1. Download spaCy model: `uv run python -m spacy download {lang}_core_news_sm`
2. Update `_MODEL_MAP` in `src/pipeline.py`
3. Add tests for new language
4. Update Dockerfile to download new model

#### Adding New Components

1. Create module in appropriate `src/` subdirectory
2. Add corresponding test file in `tests/`
3. Update `src/pipeline/` to integrate new component
4. Update integration tests

## Evaluation

```bash
# Full evaluation (NER + Geocoding)
uv run python -m src.evaluation                                 # Aggregate synthesis of all corpora
uv run python -m src.evaluation tests/corpus/en_simple.json     # Single corpus

# NER evaluation (Stages 1-2)
uv run python -m src.evaluation --ner                            # Aggregate synthesis
uv run python -m src.evaluation --ner tests/corpus/en_simple.json

# Geocoding evaluation (Stages 3-4, decoupled from NER)
uv run python -m src.evaluation --geocoding                      # Aggregate synthesis
uv run python -m src.evaluation --geocoding tests/corpus/en_simple.json

# NER synthesis prints aggregate entity-level metrics (precision/recall/F1),
# per-type breakdown, and per-corpus summary table.
# Geocoding synthesis is decoupled from NER (feeds corpus entities to GeoPipeline
# directly). Reports geocoding rate, country accuracy, coordinate-distance metrics
# (mean distance, within 1/10/100 km), and event location accuracy.
```

## Corpus Maintenance

```bash
# Check all corpora for offset errors
uv run python scripts/fix_corpus_offsets.py --check

# Fix all offsets
uv run python scripts/fix_corpus_offsets.py
```

## Code Quality (ruff)

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting.

### Commands

```bash
# Check and format in one pass
uv run ruff check --fix . && uv run ruff format .
```

### Configuration

Ruff is configured in `pyproject.toml`:

- **Line length**: 100 characters
- **Target Python**: 3.14
- **Enabled rules**: E, W, F, I (isort), UP (pyupgrade), B (bugbear), C4 (comprehensions), RUF

### Python syntax

When editing Python code, follow these rules:

- **Exception handling**: Use modern Python syntax for multiple exceptions (Python 3.14+), e.g., `except Exception1, Exception2:` (parentheses optional)
- **Docstrings**: Google-style docstrings on all public classes and methods. Module-level docstrings describe the file's purpose in one line. Private functions (`_`-prefixed) do not require docstrings (enforced by ruff rule `D`).

### Quality Check Workflow

```bash
# Fast path (unit tests only, no model downloads needed):
uv run python -m pytest -m "not model_dependent" --cov=src --cov-report=term-missing

# Full suite (requires spaCy models + text2geo data):
uv run python -m pytest --cov=src --cov-report=term-missing

# CI entry point (downloads models, runs full suite):
bash scripts/ci.sh

# CI fast path (unit tests only):
bash scripts/ci.sh --fast

# 2. Lint code
uv run ruff check .

# 3. Format code
uv run ruff format .
```

## Docker Build

```bash
# Build image
docker build -t location-extraction-service .

# Run container
docker run -p 8000:8000 location-extraction-service

# With docker-compose
docker-compose up --build
```

## Key Dependencies

| Package       | Version   | Purpose                   |
| ------------- | --------- | ------------------------- |
| spacy         | >=3.8.0   | NLP framework             |
| langdetect    | >=1.0.9   | Language detection        |
| geonamescache | >=3.0.1   | Offline geocoding (PyPI)  |
| pycountry     | >=26.2.16 | ISO country name lookup   |
| fastapi       | >=0.135.0 | API server                |
| uvicorn       | >=0.30.0  | ASGI server               |
| pydantic      | >=2.9.0   | Data validation           |
| httpx         | >=0.28.0  | Async HTTP client (tests) |
| ruff          | >=0.9.0   | Linting/formatting        |
| pytest        | >=9.0.0   | Testing                   |

## Performance Targets

- Latency (p95): <1 second per document
- Throughput: 1000+ documents/day
- Memory: ~2GB (spaCy models + geocoder)

## Troubleshooting

**Dependencies not found**: Run `uv sync` to install all dependencies

**spaCy model not found**: Run `uv run python -m spacy download en_core_web_sm fr_core_news_sm`

**Slow startup**: Models are cached after first load. Subsequent startups are faster.

**CI fails with missing model error**: Run `bash scripts/ci.sh` which downloads models before testing. Use `bash scripts/ci.sh --fast` for a quick unit-only pass. If integration tests are skipped with `pytest.exit`, models are missing — run the download commands above.

## uv Commands Reference

| Command                                            | Description                                         |
| -------------------------------------------------- | --------------------------------------------------- |
| `uv sync`                                          | Install all dependencies (including dev by default) |
| `uv sync --dev`                                    | Explicitly include dev dependencies                 |
| `uv sync --no-dev`                                 | Exclude dev dependencies                            |
| `uv run python -m pytest`                          | Run pytest tests (full suite, requires models)      |
| `uv run python -m pytest -m "not model_dependent"` | Run unit tests only (no model downloads needed)     |
| `uv run ruff check`                                | Lint code                                           |
| `uv run ruff format`                               | Format code                                         |
| `uv lock`                                          | Update lock file                                    |
| `uv sync --frozen`                                 | Install without updating lock (CI/CD)               |

## File Structure

```
location-extraction-service/
├── src/
│   ├── __init__.py
│   ├── app.py                # FastAPI server, /health, /api/extract-location, dependency injection
│   ├── schemas.py            # Pydantic schemas (GeoJSON FeatureCollection, GeoFeature, etc.)
│   ├── models.py             # Typed dataclasses (EntityMention, GeocodedLocation, LocationResult, etc.)
│   ├── pipeline.py           # NerPipeline + NerResult + internal detection/NER/model
│   ├── geocoding.py          # GeoPipeline + GeoResult + internal geonamescache wrapper (injectable)
│   ├── disambiguator.py      # DisambiguatePipeline + DisambiguateResult + event location inference
│   ├── orchestrator.py       # LocationPipeline composing all 4 stages
│   ├── evaluation/
│   │   ├── __init__.py       # Pure evaluation (evaluate, evaluate_geocoding, evaluate_event_location)
│   │   ├── runner.py         # Pipeline orchestration + corpus loading + geocoding evaluation
│   │   └── __main__.py       # CLI runner (supports --geocoding)
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_detector.py
│   │   ├── test_extractor.py
│   │   ├── test_disambiguator.py
│   │   └── test_evaluation.py
│   ├── integration/
│   │   ├── conftest.py
│   │   ├── test_api.py              # FastAPI integration tests (mock pipeline)
│   │   ├── test_nlp_manager.py
│   │   ├── test_pipeline_integration.py
│   │   └── test_evaluation_integration.py
│   └── corpus/               # Evaluation corpora (EN + FR, with geocoding annotations)
│       ├── en_simple.json
│       ├── en_paragraphs.json
│       ├── en_edge_cases.json
│       ├── fr_simple.json
│       ├── fr_paragraphs.json
│       └── fr_edge_cases.json
├── scripts/
│   ├── annotate_geocoding.py    # Geocoding ground-truth annotation via Nominatim
│   ├── fix_corpus_offsets.py    # Corpus offset fixer
│   └── ci.sh                    # CI entry point (--fast for unit-only)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml             # Dependencies and ruff config
├── README.md                 # End-user documentation
├── AGENTS.md                 # This file
└── .env.example
```

## Related Documentation

- [Evaluation Guide](../../docs/evaluation.md)
- [Architecture](../../docs/architecture/location-extraction.md)
- [ADR-001](../../docs/decisions/ADR-001-location-extraction-approach.md)
- [ADR-002](../../docs/decisions/ADR-002-ner-evaluation-protocol.md)
- [ADR-003](../../docs/decisions/ADR-003-ner-pipeline-seam.md)
- [ADR-004](../../docs/decisions/ADR-004-consolidate-pipeline-module.md)
- [ADR-005](../../docs/decisions/ADR-005-text2geo-nan-bug.md) (deprecated — `text2geo` replaced by `geonamescache` per [ADR-007](../../docs/decisions/ADR-007-replace-text2geo-with-geonamescache.md))
- [ADR-006](../../docs/decisions/ADR-006-pipeline-architectural-improvements.md)
- [ADR-008](../../docs/decisions/ADR-008-geocoding-evaluation-corpus.md)
- [spaCy Documentation](https://spacy.io/)
- [text2geo](https://github.com/charonviz/text2geo)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [uv Documentation](https://github.com/astral-sh/uv)
- [ruff Documentation](https://docs.astral.sh/ruff/)
