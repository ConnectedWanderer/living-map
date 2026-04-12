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

# Download spaCy models
uv run python -m spacy download en_core_web_trf
uv run python -m spacy download fr_core_news_trf

# Download GeoNames data
uv run python -c "from text2geo import Geocoder; Geocoder(dataset='world')"

# Run the server
uv run uvicorn src:app --host 0.0.0.0 --port 8000 --reload

# Run tests
uv run python -m pytest
```

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# Or build image manually
docker build -t location-extraction-service .
docker run -p 8000:8000 location-extraction-service
```

## API Usage

### Extract Location

```bash
curl -X POST http://localhost:8000/api/extract-location \
  -H "Content-Type: application/json" \
  -d '{"text": "Breaking news from Paris, France about flooding in the Seine river.", "language": "auto"}'
```

### Response

```json
{
  "detected_language": "en",
  "event_location": {
    "text": "Paris",
    "lat": 48.8566,
    "lon": 2.3522,
    "country": "FR",
    "country_name": "France",
    "confidence": 0.85
  },
  "all_locations": [
    {
      "text": "Paris",
      "lat": 48.8566,
      "lon": 2.3522,
      "name": "Paris",
      "country": "FR",
      "type": "GPE"
    }
  ],
  "metadata": {
    "processing_time_ms": 150,
    "language_model": "en_core_web_trf",
    "entities_found": 1,
    "entities_geocoded": 1
  }
}
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Architecture

```
Input Text → Language Detection → spaCy NER → text2geo Geocoder → Event Location Inference → JSON
```

## Configuration

| Variable    | Default   | Description   |
| ----------- | --------- | ------------- |
| `HOST`      | `0.0.0.0` | Server host   |
| `PORT`      | `8000`    | Server port   |
| `LOG_LEVEL` | `INFO`    | Logging level |

## License

MIT
