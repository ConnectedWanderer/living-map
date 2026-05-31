# Location Extraction Service

A high-throughput, low-latency NLP service that extracts geographic locations from unstructured text (news articles).

## Features

- Extract location mentions from article text
- Disambiguate place names to geographic coordinates
- Language detection (English, French)
- Offline operation (no external API costs)
- Sub-second latency per document

## Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker (for containerized deployment)

## Quick Start

### Local Development with uv

```bash
# Clone and enter directory
cd backend/location-extraction-service

# Install dependencies (creates .venv automatically)
uv sync

# Download spaCy small models
uv run python -m spacy download en_core_web_sm fr_core_news_sm

# (No separate geocoder data download needed — geonamescache ships data with the package)

# Run the server
uv run uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload

# Run tests
uv run python -m pytest
```

### Docker Deployment

```bash
# Build and run
docker compose up -d
```

## API Usage

### Extract Location

```bash
curl -X POST http://localhost:8000/api/extract-location \
  -H "Content-Type: application/json" \
  -d '{"text": "Breaking news from Paris, France about flooding in the Seine river.", "language": "auto"}'
```

### Response (GeoJSON FeatureCollection)

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [2.3522, 48.8566] },
      "properties": {
        "name": "Paris",
        "country": "FR",
        "country_name": "France",
        "confidence": 0.85
      }
    }
  ],
  "geocoding": {
    "query": {
      "text": "Breaking news from Paris, France about flooding in the Seine river."
    },
    "detected_language": "en",
    "model_name": "en_core_web_sm",
    "entities_found": 2,
    "entities_geocoded": 1,
    "processing_time_ms": 150.0,
    "all_entities": [
      {
        "type": "Feature",
        "geometry": {
          "type": "Point",
          "coordinates": [2.3488, 48.85341]
        },
        "properties": {
          "name": "Paris",
          "type": "GPE",
          "start": 20,
          "end": 25,
          "geocoded": true,
          "geocoding": {
            "country": "FR",
            "country_name": "France",
            "score": 2.5
          }
        }
      },
      {
        "type": "Feature",
        "geometry": null,
        "properties": {
          "name": "France",
          "type": "GPE",
          "start": 27,
          "end": 33,
          "geocoded": false
        }
      }
    ]
  }
}
```

### Health Check

```bash
curl http://localhost:8000/health
```

```json
{ "status": "ok" }
```

## Architecture

```
Input Text → Language Detection → spaCy NER → geonamescache Geocoder → Event Location Inference → GeoJSON FeatureCollection
```

## Configuration

| Variable         | Default           | Description         |
| ---------------- | ----------------- | ------------------- |
| `HOST`           | `0.0.0.0`         | Server host         |
| `PORT`           | `8000`            | Server port         |
| `LOG_LEVEL`      | `INFO`            | Logging level       |
| `SPACY_EN_MODEL` | `en_core_web_sm`  | English spaCy model |
| `SPACY_FR_MODEL` | `fr_core_news_sm` | French spaCy model  |

## Code Quality

```bash
uv run ruff check .     # Lint
uv run ruff format .    # Format
```

## Evaluation

Six hand-written corpora (138 samples) live in `tests/corpus/` and work out of the box. Large-scale corpora (NER only) are generated lazily on first run — see [Evaluation Guide](../../docs/evaluation.md) for details.

### Prerequisites

```bash
# Install dev dependencies (includes datasets + tqdm for corpus generation)
uv sync --dev
```

### Run

```bash
# Full evaluation (NER + Geocoding) on all corpora
#   → auto-generates large corpora (en_wikiann.json, fr_wikiner_gold.json) if missing
uv run python -m src.evaluation

# NER only
uv run python -m src.evaluation --ner

# Geocoding only (decoupled from NER)
uv run python -m src.evaluation --geocoding

# Single corpus
uv run python -m src.evaluation tests/corpus/en_simple.json
```

### Large-Scale Corpus Generation

Large Wikipedia-derived corpora are **not** committed to git. They are generated on demand:

| Corpus                 | Language | Samples | Command                     |
| ---------------------- | -------- | ------- | --------------------------- |
| `en_wikiann.json`      | EN       | ~7K     | `uv run python -m src.evaluation.converters.en_wikiann` |
| `fr_wikiner_gold.json` | FR       | ~3.8K   | `uv run python -m src.evaluation.converters.wikiner_fr` |

The evaluation runner also auto-generates these if `datasets` is installed and the files are missing. Hand-written corpora always work without any setup.

## Related Documentation

- [Architecture Documentation](../../docs/architecture/location-extraction.md)
- [Evaluation Guide](../../docs/evaluation.md)
- [ADR-001: Location Extraction Approach](../../docs/decisions/ADR-001-location-extraction-approach.md)
- [ADR-002: NER Evaluation Protocol](../../docs/decisions/ADR-002-ner-evaluation-protocol.md)
- [ADR-006: Pipeline Architectural Improvements](../../docs/decisions/ADR-006-pipeline-architectural-improvements.md)
- [ADR-007: Replace text2geo with geonamescache](../../docs/decisions/ADR-007-replace-text2geo-with-geonamescache.md)
- [ADR-008: Geocoding Evaluation Corpus](../../docs/decisions/ADR-008-geocoding-evaluation-corpus.md)

## License

MIT
