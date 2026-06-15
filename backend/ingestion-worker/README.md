# Ingestion Worker

A one-shot CLI job that polls external sources, normalizes articles, deduplicates against PostgreSQL, and persists events. Designed to be triggered on a schedule (e.g., via container orchestrator cron) or run manually.

## Features

- Poll mock-feed sources and normalize articles
- Deduplicate articles via `INSERT ON CONFLICT` (source + source_id unique constraint)
- Structured JSON logging with pino
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

# Run the ingestion cycle once
DATABASE_URL=postgres://livingmap:livingmap@localhost:5432/livingmap \
npm start
```

### Docker Deployment

```bash
# Build and run (from project root)
docker compose up -d
```

## Architecture

```
SourceAdapter → Normalizer → Dedup (INSERT ON CONFLICT)
```

The service runs all enabled sources once per invocation and exits. Each cycle:

1. **Fetch** — Source adapter pulls raw articles (mock-feed)
2. **Normalize** — Map to `{source_id, title, description, url, published_at, source}`
3. **Dedup** — Batch insert with `ON CONFLICT DO NOTHING`

## Configuration

| Variable       | Default                                                   | Description                  |
| -------------- | --------------------------------------------------------- | ---------------------------- |
| `DATABASE_URL` | `postgres://livingmap:livingmap@localhost:5432/livingmap` | PostgreSQL connection string |
| `LOG_LEVEL`    | `info`                                                    | Pino log level               |

Sources are configured via the `sources` PostgreSQL table — see [`backend/migrations/001_schema.js`](../../migrations/001_schema.js) for the schema.

## Code Quality

```bash
npm run typecheck    # TypeScript check (no emit)
npm run lint         # Lint with Biome
npm run format       # Format with Biome
npm run check        # Biome check + JSDoc verification
npm run check:docs   # JSDoc verification only
npm run lint:ci      # CI lint + JSDoc (fails on violations, no writes)
npm test             # Unit tests
npm run test:all     # All tests (unit + integration via orchestrator)
npm run test:int     # Integration tests (auto-manages Docker via orchestrator)
```

Linting and formatting are integrated repo-wide via pre-commit hooks — see [Root AGENTS.md](../../AGENTS.md).

## Related Documentation

- [Architecture Documentation](../../docs/architecture/ingestion-worker.md)
- [ADR-013: npm Package Manager](../../docs/decisions/ADR-013-npm-package-manager.md)
- [ADR-014: node-pg-migrate for DB Migrations](../../docs/decisions/ADR-014-node-pg-migrate-for-db-migrations.md)
- [ADR-015: TypeScript for Node Services](../../docs/decisions/ADR-015-typescript-for-node-services.md)
