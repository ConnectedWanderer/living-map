# ADR-012: Event Deduplication Strategy

## Status

Proposed

## Date

2026-05-19

## Context

The batch ingestion pipeline runs on a cron schedule and fetches articles from external APIs each cycle. Without deduplication, every ingestion cycle would re-process and re-insert the same articles, producing duplicate events in the database.

External API sources have variable reliability in providing stable identifiers:

| Source type    | ID stability         | Example                                       |
| -------------- | -------------------- | --------------------------------------------- |
| RSS feeds      | Stable `guid`        | `<guid isPermaLink="true">https://...</guid>` |
| JSON APIs      | Stable `id` field    | `{"id": "abc123", ...}`                       |
| Some REST APIs | No stable ID         | Returns only title + date                     |
| mock-feed      | Stable `guid` (UUID) | Generated with deterministic fields           |

Duplicate events degrade the user experience (multiple identical markers on the map) and waste extraction API calls.

## Decision

Use a two-tier deduplication strategy:

### Primary: Source + Source ID Unique Constraint

Each external source defines a `source` name (e.g., `mock-feed`, `news-api`) and extracts a `source_id` from each article (e.g., RSS `guid`, API `id`).

```sql
CREATE TABLE events (
    ...
    source      TEXT NOT NULL,
    source_id   TEXT NOT NULL,
    ...
    CONSTRAINT uq_events_source_source_id UNIQUE (source, source_id)
);
```

The `ON CONFLICT DO NOTHING` or `ON CONFLICT DO UPDATE` pattern handles upserts:

```sql
INSERT INTO events (source, source_id, title, ...)
VALUES ($1, $2, $3, ...)
ON CONFLICT ON CONSTRAINT uq_events_source_source_id
DO UPDATE SET updated_at = now()
    -- Update extracted data in case coordinates changed
    SET location = EXCLUDED.location,
        location_name = EXCLUDED.location_name;
```

### Fallback: Content Hash

For sources that do not provide stable IDs, compute `SHA-256(title + published_at)` as the `source_id`. This catches duplicate content even when the source provides no identifier.

### Ingestion Worker Flow

```
For each article in API response:
  1. Extract source_id from article (or compute content hash)
  2. Check dedup: INSERT ... ON CONFLICT DO NOTHING
  3. If inserted (new article):
     a. Call Location Extraction service
     b. UPDATE row with coordinates
  4. If not inserted (duplicate):
     a. Skip (optionally UPDATE updated_at for freshness tracking)
```

## Consequences

### Positive

- PostgreSQL unique constraint guarantees no duplicate rows regardless of race conditions
- Content hash fallback covers sources without stable IDs
- `ON CONFLICT` is atomic — no separate check-then-insert race window
- Worked example: mock-feed articles have UUID `guid`, deduped perfectly; a hypothetical API returning only `{"title": "Flood in Paris", "date": "2026-05-19"}` uses content hash

### Negative

- Content hash collisions are theoretically possible but negligible for SHA-256
- Sources with stable IDs may still change content (updated article) — the `ON CONFLICT DO UPDATE` handles this but does not re-extract location unless explicitly triggered

### Neutral

- Dedup logic lives entirely in the ingestion worker and the DB constraint — no external state
- Adding a new source type requires only configuring `source` name and `source_id` extraction logic
