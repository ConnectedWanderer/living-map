# Ingestion Worker

A cron-triggered Node.js service that polls external sources, normalizes articles, deduplicates against PostgreSQL, enriches via the Location Extraction service, and persists enriched events.

## Features

- Poll multiple RSS/mock-feed sources on configurable cron schedules
- Deduplicate articles via `INSERT ON CONFLICT` (source + source_id unique constraint)
- Enrich articles with geographic location data via the Location Extraction service
- Structured JSON logging with pino
- Health check endpoint for container orchestration
- Type-safe with TypeScript (run directly via `--experimental-strip-types`)

## Prerequisites

- **Node.js** v22+ (for `--experimental-strip-types`)
- **npm**
- **Docker** (for integration tests and containerized deployment)
- **PostgreSQL** 14+ (with `livingmap` database)

## Quick Start

### Local Development

```bash
# Clone and enter directory
cd backend/ingestion-worker

# Install dependencies
npm install

# Ensure PostgreSQL is running with the `livingmap` database
# Run migrations (from project root)
npx node-pg-migrate up --migration-file-language js --migration-dir backend/migrations

# Start the service
DATABASE_URL=postgres://livingmap:livingmap@localhost:5432/livingmap \
LOCATION_EXTRACTION_URL=http://localhost:8000 \
npm start
```

### Docker Deployment

```bash
# Build and run (from project root)
docker-compose up -d
```

## Architecture

```
SourceAdapter → Normalizer → Dedup (INSERT ON CONFLICT) → Location Extraction → DB UPDATE
```

The service runs on a cron schedule defined per source in the `sources` PostgreSQL table. Each cycle:

1. **Fetch** — Source adapter pulls raw articles (RSS, mock-feed, etc.)
2. **Normalize** — Map to `{source_id, title, description, url, published_at, source}`
3. **Dedup** — Batch insert with `ON CONFLICT DO NOTHING`
4. **Enrich** — For newly inserted articles, POST to Location Extraction service
5. **Persist** — Update enriched rows with GeoJSON location data

## Configuration

| Variable                  | Default                                                   | Description                     |
| ------------------------- | --------------------------------------------------------- | ------------------------------- |
| `DATABASE_URL`            | `postgres://livingmap:livingmap@localhost:5432/livingmap` | PostgreSQL connection string    |
| `LOCATION_EXTRACTION_URL` | `http://localhost:8000`                                   | Location Extraction service URL |
| `PORT`                    | `3000`                                                    | Health endpoint port            |
| `LOG_LEVEL`               | `info`                                                    | Pino log level                  |

Sources are configured via the `sources` PostgreSQL table — see [`backend/migrations/001_create-events-and-sources.js`](../../migrations/001_create-events-and-sources.js) for the schema.

## API

### Health Check

```bash
curl http://localhost:3000/health
```

```json
{ "status": "ok" }
```

## Code Quality

```bash
npm run typecheck    # TypeScript check (no emit)
npm test             # Unit tests
npm run test:all     # All tests (unit + integration via orchestrator)
npm run test:int     # Integration tests (auto-manages Docker via orchestrator)
```

Formatting is handled repo-wide via pre-commit hooks — see [Root AGENTS.md](../../AGENTS.md).

## Related Documentation

- [Architecture Documentation](../../docs/architecture/ingestion-worker.md)
- [ADR-013: npm Package Manager](../../docs/decisions/ADR-013-npm-package-manager.md)
- [ADR-014: node-pg-migrate for DB Migrations](../../docs/decisions/ADR-014-node-pg-migrate-for-db-migrations.md)
- [ADR-015: TypeScript for Node Services](../../docs/decisions/ADR-015-typescript-for-node-services.md)
