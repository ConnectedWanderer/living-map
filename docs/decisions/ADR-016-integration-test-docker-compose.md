# ADR-016: Centralized Docker Compose for Integration Testing

## Status

Accepted

## Date

2026-05-20

## Context

The project has multiple backend services with cross-cutting integration dependencies:

| Service                      | Integration test requires                                          |
| ---------------------------- | ------------------------------------------------------------------ |
| ingestion-worker (TS)        | PostgreSQL, mock-feed (port 3001), location-extraction (port 8000) |
| location-extraction (Python) | spaCy models (local only, no external services)                    |

Currently, developers must start these services manually. The only Docker Compose file (`backend/location-extraction-service/docker-compose.yml`) only covers location-extraction. No Compose file exists for the full test environment.

The ingestion-worker integration tests (`tests/integration/helpers.ts`) hardcode `localhost` URLs with these defaults:

- `DATABASE_URL`: `postgres://livingmap:livingmap@localhost:5432/livingmap_test`
- `MOCK_FEED_URL`: `http://localhost:3001`
- `LE_URL`: `http://localhost:8000`

Absent a reproducible test environment leads to:

- Flaky CI — "works on my machine" gaps
- High onboarding friction — each dev figures out the service dance independently
- No automated integration test run in CI

## Decision

Create a dedicated integration test Docker Compose (`backend/docker-compose.test.yml`) plus a Dockerfile for mock-feed (the only un-containerized service).

### Services

**postgres-test** — `postgis/postgis:16-3.4`

- Test database (`livingmap_test`), dedicated user (`livingmap`)
- PostGIS for spatial queries used by the planned serving API
- Port 5432 mapped to host — no test code changes needed
- Health check: `pg_isready`

**mock-feed** — custom Node.js container

- New `Dockerfile` (`backend/mock-feed/Dockerfile`) on `node:22-alpine`
- Port 3001 mapped to host
- Health check: probe `/health`

**location-extraction** — reuse existing `Dockerfile`

- Built from `backend/location-extraction-service/Dockerfile` (includes spaCy models)
- Port 8000 mapped to host
- Health check: probe `/health`
- Grace period: 60s start (spaCy model load is CPU-heavy)

### Test Execution Pattern

```
docker compose -f docker-compose.test.yml up -d --wait  # start all, wait for health
npx node-pg-migrate up                                   # run migrations
node --test tests/integration/*.test.ts                  # run integration tests
docker compose -f docker-compose.test.yml down -v        # teardown + clean volumes
```

### No Changes to Test Code

All services expose their standard ports to the host. Test code default URLs match — no `helpers.ts` edits required.

## Consequences

### Positive

- Single command to start full test environment — reduces onboarding friction
- Reproducible CI — same container images, same database state
- Existing `npm run test:int` unchanged — devs get the same interface
- A Node.js orchestrator (`tests/integration-runner.ts`) wraps the full lifecycle: start containers, run migrations, execute tests, teardown
- PostGIS available for future serving API integration tests
- mock-feed now deployable in any environment (Dockerfile exists)

### Negative

- Longer build pipeline — LE Dockerfile downloads spaCy models (~20s image build)
- Port conflicts if dev already runs these services locally
- Test container state persists between runs (DB volume) unless `down -v`

### Neutral

- Existing LE `docker-compose.yml` stays for standalone LE development
- The convenience wrapper is a Node.js orchestrator (`tests/integration-runner.ts`) rather than a shell script, keeping the toolchain consistent
- CI can be added later; the Compose file is the foundation
