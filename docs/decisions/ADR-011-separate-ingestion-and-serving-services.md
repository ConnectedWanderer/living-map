# ADR-011: Separate Ingestion and Serving Services

## Status

Proposed

## Date

2026-05-19

## Context

The original architecture plans a Node.js + Express backend that handles both ingestion (fetching from external APIs, calling location extraction) and serving (responding to frontend requests). These responsibilities have different characteristics:

| Dimension             | Ingestion                          | Serving                     |
| --------------------- | ---------------------------------- | --------------------------- |
| Failure impact        | Data becomes stale                 | User sees no data or errors |
| Latency requirement   | Minutes acceptable                 | < 200ms target              |
| Scaling driver        | Number of external API sources     | Number of concurrent users  |
| Schedule              | Cron-triggered (batch)             | Request-driven (on-demand)  |
| External dependencies | External APIs, Location Extraction | PostgreSQL only             |

Coupling them means:

- An external API outage can cause the serving API to hang or fail
- Scaling the serving API for traffic also scales ingestion (wasteful)
- A bug in ingestion logic can crash the entire backend
- Different languages may be optimal for each (Python for NLP integration, Node.js for lightweight API)

## Decision

Split the backend into two independently deployable services:

### Service 1: Serving API (Node.js + Express)

- Read-only HTTP API
- Queries PostgreSQL for events
- Returns GeoJSON FeatureCollection
- Stateless, horizontally scalable
- Dependencies: PostgreSQL only
- Responsibility: respond to user requests, fast and reliably

### Service 2: Ingestion Worker (Node.js)

- Cron-triggered batch processor
- Fetches from external API sources
- Calls Location Extraction service
- Writes enriched events to PostgreSQL
- Dependencies: PostgreSQL, Location Extraction, external APIs
- Responsibility: keep the database populated with fresh, deduplicated events

### Shared Nothing Except PostgreSQL

The two services share no code, no process, and no network port. They communicate only through the database: the ingestion worker writes, the serving API reads.

### Deployment

```yaml
# docker-compose.yml services
services:
  postgres: # PostgreSQL + PostGIS
  location-extraction: # existing FastAPI service
  mock-feed: # existing test feed
  ingestion-worker: # Node.js worker (new)
  api: # Node.js Express API (new)
```

## Consequences

### Positive

- Ingestion failures do not affect serving — users always see the last successful data
- Independent scaling: serve more users by adding API replicas, ingest more sources by tuning worker schedule
- Same language (Node.js) for both services — reduces cognitive overhead, shares patterns (Express, async I/O, npm ecosystem)
- Independent deploy cycles: update ingestion logic without touching serving API
- Clear module boundaries — each service has a single, testable responsibility
- Can develop and test each service in isolation with a shared database

### Negative

- Two services to build instead of one — more initial development effort
- Two sets of deployment configuration, monitoring, and logging
- Shared database creates implicit coupling — schema changes must coordinate across services
- Need to manage database connection pools for both services

### Neutral

- Adding more ingestion workers (for different source types) is natural — each is a separate process with its own config
- The serving API could later cache hot queries (Redis) without affecting ingestion
- If the split proves too costly, merging is straightforward: the ingestion worker becomes a module in the serving API
