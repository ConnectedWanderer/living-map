# Ingestion Worker — Database Schema

## Tables

### `sources` (new)

Source configuration read by worker on startup. Enables dynamic source registration.

```sql
CREATE TABLE IF NOT EXISTS sources (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    adapter     TEXT NOT NULL,          -- module name in src/sources/ (e.g. 'mock-feed', 'rss')
    endpoint    TEXT NOT NULL,          -- URL to fetch
    schedule    TEXT NOT NULL,          -- cron expression
    enabled     BOOLEAN NOT NULL DEFAULT true,
    config      JSONB DEFAULT '{}',     -- adapter-specific options (count, params, headers)
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

### `events` (new — finalize alongside ADR-012)

Persisted enriched events displayed on the map.

```sql
CREATE TABLE IF NOT EXISTS events (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    source_id       TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    url             TEXT,
    published_at    TIMESTAMPTZ,
    location        GEOMETRY(Point, 4326),  -- PostGIS geometry for bbox queries
    location_name   TEXT,
    country         TEXT,
    confidence      REAL,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_events_source_source_id UNIQUE (source, source_id)
);

CREATE INDEX IF NOT EXISTS idx_events_location ON events USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_events_published_at ON events (published_at DESC);
```

## Migration Tooling

**Chosen: `node-pg-migrate`** (see ADR-014).

### Why Not Alembic

Alembic (Python) was originally planned in `overview.md` but adds a Python runtime dependency solely for migrations. Since all services that communicate directly with the database are Node.js, a Node.js-native tool is simpler — no extra runtime in CI/CD, Docker images, or dev environments.

### Running Migrations

Migrations run as a **separate step before deploy**, not on worker startup:

- **CI/CD pipeline**: `npx node-pg-migrate up` against the target database
- **Docker Compose**: an `init` container or a separate `migration` service that runs before the worker starts
- **Local dev**: `npm run migrate:up` script

```json
{
  "scripts": {
    "migrate:up": "node-pg-migrate up",
    "migrate:down": "node-pg-migrate down",
    "migrate:create": "node-pg-migrate create"
  }
}
```

### Migration Files

Each migration is a `.js` or `.sql` file in `backend/migrations/`. node-pg-migrate tracks applied migrations in the `pgmigrations` table.

Example `backend/migrations/001_create-sources.js`:

```js
exports.up = (pgm) => {
  pgm.createTable("sources", {
    id: { type: "serial", primaryKey: true },
    name: { type: "text", notNull: true, unique: true },
    adapter: { type: "text", notNull: true },
    endpoint: { type: "text", notNull: true },
    schedule: { type: "text", notNull: true },
    enabled: { type: "boolean", notNull: true, default: true },
    config: { type: "jsonb", default: "{}" },
    created_at: { type: "timestamptz", default: pgm.func("now()") },
  });
};

exports.down = (pgm) => {
  pgm.dropTable("sources");
};
```

Or plain SQL via `pgm.sql()` for complex operations (e.g., PostGIS extension, spatial indexes).

## Seed Data

Initial `mock-feed` source row — can be part of the migration or a separate seed script:

```sql
INSERT INTO sources (name, adapter, endpoint, schedule, config)
VALUES (
    'mock-feed',
    'mock-feed',
    'http://mock-feed:3001/feed?count=20',
    '*/5 * * * *',
    '{}'
)
ON CONFLICT (name) DO NOTHING;
```
