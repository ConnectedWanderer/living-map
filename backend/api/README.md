# Serving API

Read-only Express server serving Mapbox Vector Tile (MVT) tiles from PostGIS for the Living Map frontend.

## Features

- Serve MVT tiles at `GET /tiles/{z}/{x}/{y}.pbf`
- PostGIS `ST_AsMVT` rendering with spatial index filtering (`&& ST_TileEnvelope`)
- CORS configured for frontend dev server
- Health check endpoint for container orchestration
- Type-safe with TypeScript (run directly via `--experimental-strip-types`)

## Prerequisites

- **Node.js** v22+ (for `--experimental-strip-types`)
- **npm**
- **PostgreSQL** 14+ with PostGIS extension and `livingmap` database
- **Docker** (for integration tests and containerized deployment)

## Quick Start

### Local Development

```bash
# Clone and enter directory
cd backend/api

# Install dependencies
npm install

# Ensure PostgreSQL + PostGIS is running with the `livingmap` database
# Run migrations (from project root)
npx node-pg-migrate up --migration-file-language js --migration-dir backend/migrations

# Start the service
DATABASE_URL=postgres://livingmap:livingmap@localhost:5432/livingmap \
npm start
```

### Docker Deployment

```bash
# Build and run (from project root)
docker compose -f backend/docker-compose.yml up -d --build
```

The API is exposed on port 3002.

## Architecture

```
Express → routes/tiles.ts → services/tiles.ts (ST_AsMVT SQL) → db/client.ts (pg Pool) → PostGIS
```

- `src/db/client.ts` — Singleton `pg.Pool` from `DATABASE_URL` env var
- `src/routes/tiles.ts` — Route handler with tile coordinate validation (z 0–22, x/y within z bounds)
- `src/services/tiles.ts` — `getTile(pool, z, x, y)` executes `ST_AsMVT` query, returns `Buffer | null`

Tiles with no features return `204 No Content`.

## API

### Get Tile

```bash
curl http://localhost:3002/tiles/12/2048/1024.pbf
```

Returns `application/vnd.mapbox-vector-tile` binary on success, `204 No Content` when empty.

### Health Check

```bash
curl http://localhost:3002/health
```

```json
{ "status": "ok" }
```

## Configuration

| Variable       | Default                                    | Description                     |
| -------------- | ------------------------------------------ | ------------------------------- |
| `DATABASE_URL` | `postgres://livingmap:livingmap@localhost:5432/livingmap` | PostgreSQL connection string |
| `PORT`         | `3002`                                     | Server port                     |
| `CORS_ORIGIN`  | `http://localhost:5173`                    | Allowed CORS origin             |

## Code Quality

```bash
npm run typecheck    # TypeScript check (no emit)
npm run lint         # Lint with Biome
npm run format       # Format with Biome
npm run check        # Biome check
npm run lint:ci      # CI lint (fails on violations, no writes)
npm test             # Unit tests
npm run test:int     # Integration tests (Testcontainers + PostGIS)
npm run test:all     # All tests
```

## Related Documentation

- [Architecture Documentation](../../docs/architecture/serving-api.md)
- [Root README](../../README.md)
