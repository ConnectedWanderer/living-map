# ADR-018: Testcontainers for Integration Testing

## Status

Accepted

## Supersedes

ADR-016

## Context

ADR-016 introduced a centralized Docker Compose file (`docker-compose.test.yml`) and a Node.js orchestrator (`tests/integration-runner.ts`) for integration testing. The approach worked but revealed several pain points:

1. **Port conflicts** — Hardcoded ports (5432, 3001, 8000) prevent running tests concurrently or when local dev services are active.
2. **Shared PostgreSQL state** — A single database instance shared across all test files required `TRUNCATE` coordination. A crash mid-suite leaked state.
3. **Monolithic orchestration** — The runner had to manage the full lifecycle: `docker compose up`, migrations, test execution, teardown. Could not run individual test files directly.
4. **Redundant health checks** — `docker compose --wait` + `ensureServices()` HTTP pings did the same validation.
5. **Docker Compose coupling** — The full Docker Compose stack (Postgres, mock-feed, location-extraction) was required even for tests that only needed a database.

## Decision

Replace Docker Compose orchestration with Testcontainers v12 for managing ephemeral test infrastructure.

### Container Management Strategy

**Per-test-file containers (PostgreSQL):**

- Each integration test file starts its own `postgis/postgis:18-3.6-alpine` container via `@testcontainers/postgresql`
- Dynamic port mapping eliminates conflicts
- Fresh database per file eliminates cross-file state leaks
- Migrations run per file at setup time

**Shared containers (mock-feed, location-extraction):**

- `integration-runner.ts` builds and starts both services once via `GenericContainer.fromDockerfile()`
- Dynamic ports passed to test subprocesses via `MOCK_FEED_URL` and `LE_URL` environment variables
- Containers torn down in `finally` block after all tests complete

### File Changes

| Action  | File                                             | Rationale                                                                           |
| ------- | ------------------------------------------------ | ----------------------------------------------------------------------------------- |
| Rewrite | `tests/integration-runner.ts`                    | Build + start shared containers via Testcontainers; pass dynamic URLs via env       |
| Create  | `tests/integration/setup.ts`                     | `withPostgres()` helper using `@testcontainers/postgresql`                          |
| Modify  | `tests/helpers.ts`                               | Parameterized `createTestPool(connectionString)`, `runMigrations(connectionString)` |
| Modify  | `tests/integration/helpers.ts`                   | Remove `ensureServices()` (Testcontainers handles readiness); keep env-based URLs   |
| Modify  | `tests/integration/*.test.ts`                    | Use `withPostgres()` for per-file DB isolation                                      |
| Rename  | `docker-compose.test.yml` → `docker-compose.yml` | Retained for manual dev testing, not used by CI                                     |

### Docker Compose Role

`backend/docker-compose.yml` is retained for local development workflows where developers want to start all backend services manually. It is no longer used by the CI test runner.

## Consequences

### Positive

- **No port conflicts** — Every container uses dynamic port mapping via Testcontainers
- **Per-file isolation** — Each test file gets a fresh PostgreSQL container; `TRUNCATE` is only needed for within-test-file isolation
- **Direct test execution** — Individual test files can be run with `node --test` if shared services are already running (or started manually)
- **Simpler runner** — ~45 LOC vs 91 LOC; no Docker Compose spawning, no migration orchestration (each file handles its own)
- **Testcontainers v12 default wait strategy** — Uses Docker healthcheck when available, falling back to `Wait.forListeningPorts()`; no manual health check polling needed
- **Image layer caching** — LE and mock-feed images build once per machine; subsequent builds are fast

### Negative

- **First build is slow** — LE Dockerfile downloads spaCy models (~20-30s). Docker layer caching makes subsequent builds fast.
- **Dependency on testcontainers** — Adds `testcontainers` + `@testcontainers/postgresql` as dev dependencies
- **Direct test execution requires pre-running shared services** — Running a single test file without the runner requires LE and mock-feed to be running separately

### Neutral

- **Node.js >= 22.22 required** — Testcontainers v12 drops Node 20 support (EOL). The project already targets Node 22 (`node:22-alpine` base image).
- **Docker still required** — Testcontainers manages Docker under the hood. No Docker-in-Docker or rootless mode changes.
