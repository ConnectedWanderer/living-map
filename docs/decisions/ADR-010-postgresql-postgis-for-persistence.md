# ADR-010: PostgreSQL + PostGIS for Event Persistence

## Status

Proposed

## Date

2026-05-19

## Context

The original architecture uses an in-memory cache (`node-cache`) for event storage. This has fundamental limitations:

1. **No durability** — cache is lost on process restart, forcing a full re-fetch and re-extraction of all events.
2. **No query capability** — in-memory cache supports key-value lookups only. Cannot filter by bounding box, date range, or event type.
3. **No concurrency** — multiple ingestion workers cannot safely share an in-memory cache.
4. **Memory-bound** — every event consumes RAM. No practical way to store historical data.

The system needs a persistent store that supports:

- Geospatial queries (find events within a map viewport)
- Concurrent reads and writes (separate ingestion worker + serving API)
- Schemas that evolve over time (migrations)
- Long-term event history for analytics and debugging

### Options Considered

| Option                   | Pros                                                               | Cons                                                     |
| ------------------------ | ------------------------------------------------------------------ | -------------------------------------------------------- |
| **PostgreSQL + PostGIS** | Geospatial indexes, concurrent writes, migrations, proven at scale | Requires separate database server, connection management |
| **SQLite + SpatiaLite**  | Zero-ops, single file, fast reads                                  | Poor concurrent write performance, no network access     |
| **MongoDB**              | Flexible schema, 2dsphere indexes                                  | Higher complexity, no joins, weaker consistency          |
| **Redis (persistent)**   | Fast, familiar                                                     | Limited query capability, geospatial queries are basic   |

## Decision

**Chosen: PostgreSQL with PostGIS extension**

### Schema Outline

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source          TEXT NOT NULL,          -- e.g., 'mock-feed', 'news-api'
    source_id       TEXT NOT NULL,          -- external source's stable ID (e.g., RSS guid)
    title           TEXT NOT NULL,
    description     TEXT,
    url             TEXT,
    published_at    TIMESTAMPTZ NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    location        GEOGRAPHY(Point, 4326), -- PostGIS geospatial point
    location_name   TEXT,                   -- resolved place name
    country         TEXT,                   -- ISO country code
    event_type      TEXT,                   -- e.g., 'earthquake', 'protest'
    properties      JSONB DEFAULT '{}',     -- extensible metadata
    content_hash    TEXT,                   -- SHA-256 of title+published_at for fallback dedup

    -- Dedup constraints
    CONSTRAINT uq_events_source_source_id UNIQUE (source, source_id)
);

-- Geospatial index for bounding box queries
CREATE INDEX idx_events_location ON events USING GIST (location);

-- Content hash index for fallback dedup
CREATE INDEX idx_events_content_hash ON events (content_hash);

-- Published_at index for time-range queries
CREATE INDEX idx_events_published_at ON events (published_at DESC);
```

### Why Not Others

| Option      | Why Not                                                                                                                                                                                              |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **SQLite**  | Concurrent writes from ingestion worker and serving API would be a bottleneck. No network access means the ingestion worker and serving API can't share the same file unless co-located.             |
| **MongoDB** | Valid alternative, but PostgreSQL + PostGIS provides richer geospatial functions (ST_DWithin, ST_Area, spatial joins) with a mature ecosystem. No need for a second data model when relational fits. |
| **Redis**   | Geospatial queries are limited to `GEORADIUS` — no polygon intersection, no complex filtering. In-memory cost for historical data is high.                                                           |

## Consequences

### Positive

- Geospatial queries (bounding box, radius, point-in-polygon) via PostGIS GiST indexes
- Concurrent reads and writes from separate services
- Schema migrations with Alembic for controlled evolution
- Durability — data survives restarts, supports historical queries
- Rich type system (JSONB, arrays, timestamps with timezone)
- Extension ecosystem (pgvector, TimescaleDB) available for future needs

### Negative

- Requires managing a PostgreSQL server (connection pooling, backups, migrations)
- Higher memory footprint than SQLite for small datasets
- Connection pool configuration needed for two concurrent services

### Neutral

- PostgreSQL is already the most likely dependency for deployment environments
- Can use managed PostgreSQL (Neon, Supabase, RDS) to reduce ops burden
- Adding read replicas later is straightforward if serving traffic grows
