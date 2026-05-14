# AI Agent Instructions

This document provides guidance for AI agents developing or maintaining this service.

## Architecture

The service follows a 4-stage NLP pipeline:

```
Input Text → Language Detection → spaCy NER → text2geo Geocoder → Event Location Inference → JSON
```

### Components

| File                            | Purpose                                                                                             |
| ------------------------------- | --------------------------------------------------------------------------------------------------- |
| `src/pipeline.py`               | `NerPipeline` class + `NerResult` dataclass + internal detection/NER/model logic                    |
| `src/geocoding.py`              | `GeoPipeline` class + `GeoResult` dataclass + internal text2geo wrapper                             |
| `src/disambiguator.py`          | `DisambiguatePipeline` class + `DisambiguateResult` dataclass + event location inference (Stage 4)  |
| `src/evaluation/__init__.py`    | Pure evaluation computation: `evaluate()` (precision, recall, harmonic mean (P/R/F1))               |
| `src/evaluation/runner.py`      | Orchestration: `evaluate_corpus()`, `evaluate_all_corpora()`, `discover_corpora()`, `load_corpus()` |
| `src/evaluation/__main__.py`    | CLI entry point: `uv run python -m src.evaluation`                                                  |
| `scripts/fix_corpus_offsets.py` | Corpus offset validation and repair                                                                 |
| `scripts/ci.sh`                 | CI entry point: `--fast` for unit-only, otherwise downloads models + full suite                     |

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

| Package    | Version   | Purpose                    |
| ---------- | --------- | -------------------------- |
| spacy      | >=3.8.0   | NLP framework              |
| langdetect | >=1.0.9   | Language detection         |
| text2geo   | git       | Offline geocoding (GitHub) |
| pycountry  | >=26.2.16 | ISO country name lookup    |
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

**CI fails with missing model error**: Run `bash scripts/ci.sh` which downloads models before testing. Use `bash scripts/ci.sh --fast` for a quick unit-only pass. If integration tests are skipped with `pytest.exit`, models are missing — run the download commands above.

**text2geo data download fails**: See [ADR-005](../../docs/decisions/ADR-005-text2geo-nan-bug.md) — known upstream `NaN` bug in text2geo. `scripts/ci.sh` tolerates this failure with a warning.

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
│   ├── pipeline.py            # NerPipeline + NerResult + internal detection/NER/model
│   ├── geocoding.py           # GeoPipeline + GeoResult + internal text2geo wrapper
│   ├── disambiguator.py       # DisambiguatePipeline + DisambiguateResult + event location inference
│   ├── evaluation/
│   │   ├── __init__.py       # Pure evaluation computation (evaluate)
│   │   ├── runner.py         # Pipeline orchestration + corpus loading
│   │   └── __main__.py       # CLI runner
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
│   │   ├── test_pipeline_integration.py
│   │   └── test_evaluation_integration.py
│   └── corpus/               # Evaluation corpora (EN + FR)
│       ├── en_simple.json
│       ├── en_paragraphs.json
│       ├── en_edge_cases.json
│       ├── fr_simple.json
│       ├── fr_paragraphs.json
│       └── fr_edge_cases.json
├── scripts/
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

- [Architecture](../../docs/architecture/location-extraction.md)
- [ADR-001](../../docs/decisions/ADR-001-location-extraction-approach.md)
- [ADR-002](../../docs/decisions/ADR-002-ner-evaluation-protocol.md)
- [ADR-003](../../docs/decisions/ADR-003-ner-pipeline-seam.md)
- [ADR-004](../../docs/decisions/ADR-004-consolidate-pipeline-module.md)
- [ADR-005](../../docs/decisions/ADR-005-text2geo-nan-bug.md)
- [spaCy Documentation](https://spacy.io/)
- [text2geo](https://github.com/charonviz/text2geo)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [uv Documentation](https://github.com/astral-sh/uv)
- [ruff Documentation](https://docs.astral.sh/ruff/)
