# ADR-014: node-pg-migrate for Database Migrations

## Status

Accepted

## Date

2026-05-19

## Context

The project needs a database migration tool for PostgreSQL schema evolution. All services that communicate directly with the database are Node.js: `api`, `ingestion-worker`, `mock-feed`. The original `overview.md` planned Alembic (Python), which introduces a separate runtime solely for migrations.

Options considered:

- **Alembic** — Python, mature, full-featured. Requires Python runtime in CI/CD and Docker images despite no Python services needing it.
- **node-pg-migrate** — Node.js, PostgreSQL-only, 1.4K+ stars, v8.0.4 stable, maintained by @Shinigami92 (FakerJS core, Vite core member). Auto-infers down migrations, advisory locking for concurrent safety.
- **Umzug** — Node.js, framework-agnostic, 600K weekly downloads, but needs manual wiring of DB client, storage, logging. More boilerplate.
- **Postgrator** — Node.js, plain SQL files, simpler but less active (last update Nov 2024), no programmatic API.
- **@pgkit/migrator** — Node.js, SQL-first + schema diff, promising but pre-1.0, ~1.5K weekly downloads, unstable API.
- **Prisma Migrate / Drizzle Kit** — Full ORM lock-in. Overkill for a project using raw SQL via `pg`.

### Key Criteria

| Criterion         | Requirement                                      |
| ----------------- | ------------------------------------------------ |
| Runtime           | Node.js (no Python)                              |
| PostgreSQL-native | Full support for GIST indexes, JSONB, extensions |
| Production safety | Advisory locking for concurrent migration runs   |
| Rollback          | `down` migrations supported                      |
| Maintenance       | Active community, recent releases                |
| Simplicity        | Minimal config, no ORM coupling                  |

## Decision

Use **node-pg-migrate** for all database schema migrations.

### Migration Location

All migration files live in `backend/migrations/`, versioned alongside application code.

### Runner

Migrations run as a **separate step** before deployment, not on application startup:

- CI/CD: `npx node-pg-migrate up`
- Docker Compose: separate `migration` service with `depends_on: postgres` and `condition: service_healthy`
- Local dev: `npm run migrate:up`

This keeps the application stateless — it refuses to start if the schema does not match (via a startup check), but never modifies the schema itself.

### Configuration

- `DATABASE_URL` environment variable for connection string
- `backend/migrations/` as migration directory
- Timestamp-based migration file naming

## Consequences

### Positive

- **Zero new runtime dependencies** — works with existing Node.js stack. No Python in Docker images or CI.
- **PostgreSQL-native** — full support for PostGIS extensions, GIST indexes, JSONB, `CREATE INDEX CONCURRENTLY` (auto-detects and runs outside transaction).
- **Auto-inferred rollbacks** — many `up` operations (e.g., `createTable`, `addColumn`) automatically generate `down` — less boilerplate.
- **Advisory locking** — safe for concurrent migration runs (CI/CD parallel deploys, multiple replicas).
- **Active maintenance** — v8.0.4 stable (Dec 2025), v9 alpha in development, 90 contributors.
- **Consistent with ADR-013** — npm package, installs alongside `pg`.

### Negative

- **PostgreSQL-only** — cannot switch to another database without changing migration tool. Acceptable — the project is committed to PostgreSQL (ADR-010).
- **Smaller community than Alembic** — but active and well-maintained within the Node.js PostgreSQL ecosystem.

### Neutral

- Migration files are plain JavaScript (or SQL via `pgm.sql()`). Developers write SQL schema changes directly — no abstraction layer.
- If the project later adopts an ORM (e.g., Drizzle), node-pg-migrate can coexist or be replaced. Migrations are just tracked in a table.
