# Living Map

Real-time geographical events map.

## Components

- [Location Extraction Service](backend/location-extraction-service/README.md) — Python NLP microservice
- [Mock Feed](backend/mock-feed/README.md) — RSS test data generator

## Running All Backend Services

To start all backend services locally for development or manual testing:

```bash
docker compose -f backend/docker-compose.yml up -d --build
```

This starts:

- **PostgreSQL + PostGIS** db
- **Mock Feed** (`backend/mock-feed`) — RSS test data generator
- **Location Extraction Service (LES)** (`backend/location-extraction-service`) — NLP geo-parsing microservice

To stop:

```bash
docker compose -f backend/docker-compose.yml down
```

To view logs:

```bash
docker compose -f backend/docker-compose.yml logs -f
```

## Contributing

Development setup and code quality instructions are in [AGENTS.md](AGENTS.md).

### Project Glossary

See [docs/glossary.md](docs/glossary.md) for project-specific abbreviations and domain terms.
