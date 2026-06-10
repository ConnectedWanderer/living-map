# Living Map

Real-time geographical events map.

## Components

| Component                   | Directory                              | Description                          |
| --------------------------- | -------------------------------------- | ------------------------------------ |
| Frontend                    | `frontend/`                            | Vue 3 + Vite + MapLibre GL JS        |
| Serving API                 | `backend/api/`                         | Node.js + TypeScript + Express       |
| Ingestion Worker            | `backend/ingestion-worker/`            | Cron-triggered batch ingestion       |
| Location Extraction Service | `backend/location-extraction-service/` | Python + FastAPI NLP microservice    |
| Mock Feed                   | `backend/mock-feed/`                   | RSS test data generator (standalone) |
| Migrations                  | `backend/migrations/`                  | DB schema migrations                 |

## Running All Services (Docker Compose)

To start all backend services locally for development or manual testing:

```bash
docker compose -f backend/docker-compose.yml up -d --build
```

This starts:

- **PostgreSQL + PostGIS** database
- **Migrations** (runs schema migrations on startup, then exits)
- **Serving API** (`backend/api`) — GET /events endpoint on port 3002
- **Ingestion Worker** (`backend/ingestion-worker`) — polls RSS sources on schedule, enriches via LES
- **Location Extraction Service (LES)** (`backend/location-extraction-service`) — NLP geo-parsing on port 8000
- **Frontend** (`frontend/`) — nginx serving Vue 3 production build on port 8080

Mock-feed runs separately for testing (see [mock-feed docs](backend/mock-feed/README.md)).

To stop:

```bash
docker compose -f backend/docker-compose.yml down
```

To view backend logs:

```bash
docker compose -f backend/docker-compose.yml logs -f
```

## Contributing

Development setup and code quality instructions are in [AGENTS.md](AGENTS.md).

### Project Glossary

See [docs/glossary.md](docs/glossary.md) for project-specific abbreviations and domain terms.
