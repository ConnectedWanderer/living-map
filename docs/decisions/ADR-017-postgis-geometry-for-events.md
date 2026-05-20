# ADR-017: PostGIS Geometry for Event Locations

## Status

Accepted

## Date

2026-05-20

## Context

The `events.location` column is stored as `jsonb` (migration 001). The serving API needs spatial queries (bounding box, `ST_DWithin`) to support the interactive map view. GeoJSON is the frontend serialization format — not the storage format.

This creates a mismatch between how locations are stored (JSONB blob) and how they need to be queried (spatial operators). PostGIS geometry enables:

- GIST-indexed bounding box queries (`&&` operator)
- Distance queries (`ST_DWithin`)
- Spatial join and clustering operations

The infrastructure already uses `postgis/postgis` Docker images (ADR-016). The architecture doc (`ingestion-worker-db-schema.md`) already specifies `GEOMETRY(Point, 4326)`. Only the migration and ingestion code need to catch up.

## Decision

1. **Storage type**: Change `events.location` from `jsonb` to `GEOMETRY(Point, 4326)`.
2. **Ingestion pipeline** (`db.ts:updateLocation`): Extract `[lon, lat]` from the Location Extraction service's GeoJSON `FeatureCollection` response and write via `ST_SetSRID(ST_MakePoint(...), 4326)`.
3. **Serving API** (future): Convert geometry back to GeoJSON `FeatureCollection` at read time for the frontend.
4. **PostGIS extension**: Created via migration 002 (`pgm.createExtension`). Already available in the `postgis/postgis` Docker base image.
5. **No changes** to `enrich.ts`, `runner.ts`, or the Location Extraction service — they continue to produce/consume GeoJSON; the geometry conversion is isolated to `db.ts`.

## Consequences

### Positive

- Spatial queries become possible with GIST index performance
- Architecture doc (`ingestion-worker-db-schema.md`) now matches the actual schema
- PostGIS extension is already provisioned in test/prod Docker images — no infra change needed
- Conversion logic is contained in a single function (`updateLocation`) — minimal blast radius

### Negative

- Existing JSONB data must be migrated (migration 002 handles this)
- The `updateLocation` function cannot store a `FeatureCollection` — only the first feature's point geometry is stored; metadata (`location_name`, `country`, `confidence`) is dropped (these columns don't exist in the current migration)
- Serving API will need a geometry → GeoJSON conversion step on read

### Neutral

- PostGIS is already a project dependency (chosen in ADR-016 for the serving API)
- The `postgis/postgis` Docker image is the same — no additional container size or startup time
