# AI Agent Instructions

This document provides guidance for AI agents developing or maintaining this service.

## Architecture

The service follows a 4-stage NLP pipeline:

```
Input Text → Language Detection → spaCy NER → text2geo Geocoder → Event Location Inference → JSON
```

### Components

| File                            | Purpose                                                |
| ------------------------------- | ------------------------------------------------------ |
| `src/pipeline/detector.py`      | Language detection using langdetect                    |
| `src/pipeline/nlp_manager.py`   | spaCy model loading and caching                        |
| `src/pipeline/extractor.py`     | Named Entity Recognition (GPE/LOC entities)            |
| `src/pipeline/disambiguator.py` | Event location inference and scoring                   |
| `src/geocoding/geocoder.py`     | text2geo wrapper for offline geocoding                 |
| `src/evaluation/__init__.py`    | Evaluation logic: `evaluate()` (P/R/F1), `evaluate_corpus()` (single corpus), `evaluate_all_corpora()` (aggregate synthesis), `discover_corpora()` (file discovery) |
| `src/evaluation/__main__.py`    | CLI entry point: `uv run python -m src.evaluation` (single corpus) or no-args for aggregate synthesis of all corpora |
| `src/evaluation/corpus.py`      | Evaluation corpus schema and loading                   |
| `scripts/fix_corpus_offsets.py` | Corpus offset validation and repair                    |
| `src/models/schemas.py`         | Pydantic request/response models                       |
| `src/__main__.py`               | FastAPI application entry point                        |

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

1. Download spaCy model: `uv run python -m spacy download {lang}_core_news_sm`
2. Update `src/pipeline/nlp_manager.py` model map
3. Add tests for new language
4. Update Dockerfile to download new model

#### Adding New Components

1. Create module in appropriate `src/` subdirectory
2. Add corresponding test file in `tests/`
3. Update `src/pipeline/` to integrate new component
4. Update integration tests

## Evaluation

```bash
# Single corpus
uv run python -m src.evaluation tests/corpus/en_simple.json

# Aggregate synthesis of all corpora
uv run python -m src.evaluation

# The synthesis prints aggregate entity-level metrics,
# per-type breakdown, and per-corpus summary table.
# Per-sample details are accessible via single-corpus mode.
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

### Quality Check Workflow

```bash
# 1. Run tests with coverage
uv run python -m pytest tests/ --cov=src --cov-report=term-missing

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

**spaCy model not found**: Run `uv run python -m spacy download en_core_web_sm fr_core_news_sm`

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
│   ├── evaluation/
│   │   ├── __init__.py       # Evaluation logic (precision/recall/F1)
│   │   ├── __main__.py       # CLI runner
│   │   └── corpus.py         # Corpus loading
│   └── models/
│       └── schemas.py        # Pydantic models
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_detector.py
│   │   ├── test_extractor.py
│   │   ├── test_disambiguator.py
│   │   └── test_evaluation.py
│   ├── integration/
│   │   ├── conftest.py
│   │   ├── test_nlp_manager.py
│   │   └── test_pipeline_integration.py
│   └── corpus/               # Evaluation corpora (EN + FR)
│       ├── en_simple.json
│       ├── en_paragraphs.json
│       ├── en_edge_cases.json
│       ├── fr_simple.json
│       ├── fr_paragraphs.json
│       └── fr_edge_cases.json
├── scripts/
│   └── fix_corpus_offsets.py    # Corpus offset fixer
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml             # Dependencies and ruff config
├── README.md                 # End-user documentation
├── AGENTS.md                 # This file
└── .env.example
```

## Related Documentation

- [Architecture](../../docs/architecture/location-extraction.md)
- [ADR-001](../../docs/decisions/ADR-001-location-extraction-approach.md)
- [ADR-002](../../docs/decisions/ADR-002-ner-evaluation-protocol.md)
- [spaCy Documentation](https://spacy.io/)
- [text2geo](https://github.com/charonviz/text2geo)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [uv Documentation](https://github.com/astral-sh/uv)
- [ruff Documentation](https://docs.astral.sh/ruff/)
