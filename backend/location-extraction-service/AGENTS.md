# AI Agent Instructions

This document provides guidance for AI agents developing or maintaining this service.

## Architecture

The service follows a 4-stage NLP pipeline:

```
Input Text → Language Detection → spaCy NER → text2geo Geocoder → Event Location Inference → JSON
```

### Components

| File                            | Purpose                                     |
| ------------------------------- | ------------------------------------------- |
| `src/pipeline/detector.py`      | Language detection using langdetect         |
| `src/pipeline/nlp_manager.py`   | spaCy model loading and caching             |
| `src/pipeline/extractor.py`     | Named Entity Recognition (GPE/LOC entities) |
| `src/pipeline/disambiguator.py` | Event location inference and scoring        |
| `src/geocoding/geocoder.py`     | text2geo wrapper for offline geocoding      |
| `src/models/schemas.py`         | Pydantic request/response models            |
| `src/__main__.py`               | FastAPI application entry point             |

## Development Setup

This project uses [uv](https://github.com/astral-sh/uv) for fast, deterministic Python package management.

### Initial Setup

```bash
cd backend/location-extraction-service

# Install all dependencies including dev tools (creates .venv automatically)
uv sync

# If dev dependencies not installed, run:
uv sync --dev

# Download spaCy models
uv run python -m spacy download en_core_web_trf
uv run python -m spacy download fr_core_news_trf

# Download GeoNames data for text2geo
uv run python -c "from text2geo import Geocoder; Geocoder(dataset='world')"
```

### Development Workflow

#### TDD Approach

1. Write tests first in `tests/`
2. Run tests: `uv run pytest tests/ -v`
3. Implement to make tests pass
4. Refactor as needed

#### Adding New Languages

1. Download spaCy model: `uv run python -m spacy download {lang}_core_news_trf`
2. Update `src/pipeline/nlp_manager.py` model map
3. Add tests for new language
4. Update Dockerfile to download new model

#### Adding New Components

1. Create module in appropriate `src/` subdirectory
2. Add corresponding test file in `tests/`
3. Update `src/pipeline/` to integrate new component
4. Update integration tests

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

## Testing

```bash
# Run all tests with coverage summary
uv run python -m pytest tests/ -v
```

### Quality Check Workflow

```bash
# 1. Run tests
uv run python -m pytest tests/ -v

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

| Package    | Version   | Purpose                    |
| ---------- | --------- | -------------------------- |
| spacy      | >=3.8.0   | NLP framework              |
| langdetect | >=1.0.9   | Language detection         |
| text2geo   | git       | Offline geocoding (GitHub) |
| fastapi    | >=0.135.0 | API server                 |
| uvicorn    | >=0.30.0  | ASGI server                |
| pydantic   | >=2.9.0   | Data validation            |
| ruff       | >=0.9.0   | Linting/formatting         |
| pytest     | >=9.0.0   | Testing                    |

## Performance Targets

- Latency (p95): <1 second per document
- Throughput: 1000+ documents/day
- Memory: ~2GB (spaCy models + geocoder)

## Troubleshooting

**Dependencies not found**: Run `uv sync` to install all dependencies

**spaCy model not found**: Run `uv run python -m spacy download en_core_web_trf fr_core_news_trf`

**text2geo data missing**: Run `uv run python -c "from text2geo import Geocoder; Geocoder(dataset='world')"`

**Slow startup**: Models are cached after first load. Subsequent startups are faster.

## uv Commands Reference

| Command                   | Description                                         |
| ------------------------- | --------------------------------------------------- |
| `uv sync`                 | Install all dependencies (including dev by default) |
| `uv sync --dev`           | Explicitly include dev dependencies                 |
| `uv sync --no-dev`        | Exclude dev dependencies                            |
| `uv run python -m pytest` | Run pytest tests                                    |
| `uv run ruff check`       | Lint code                                           |
| `uv run ruff format`      | Format code                                         |
| `uv lock`                 | Update lock file                                    |
| `uv sync --frozen`        | Install without updating lock (CI/CD)               |

## File Structure

```
location-extraction-service/
├── src/
│   ├── __main__.py           # FastAPI entry point
│   ├── pipeline/
│   │   ├── detector.py       # Language detection
│   │   ├── nlp_manager.py    # spaCy model manager
│   │   ├── extractor.py      # NER extraction
│   │   └── disambiguator.py  # Event location inference
│   ├── geocoding/
│   │   └── geocoder.py       # text2geo wrapper
│   └── models/
│       └── schemas.py        # Pydantic models
├── tests/
│   ├── conftest.py           # Test fixtures
│   ├── test_detector.py
│   ├── test_nlp_manager.py
│   ├── test_extractor.py
│   ├── test_disambiguator.py
│   ├── test_geocoder.py
│   └── test_pipeline_integration.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml             # Dependencies and ruff config
├── README.md                 # End-user documentation
├── AGENTS.md                 # This file
└── .env.example
```

## Related Documentation

- [Architecture](../design/architecture/location-extraction.md)
- [ADR-001](../design/decisions/ADR-001-location-extraction-approach.md)
- [spaCy Documentation](https://spacy.io/)
- [text2geo](https://github.com/charonviz/text2geo)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [uv Documentation](https://github.com/astral-sh/uv)
- [ruff Documentation](https://docs.astral.sh/ruff/)
