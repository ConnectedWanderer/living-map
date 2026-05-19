# ADR-009: Batch Ingestion Pipeline

## Status

Proposed

## Date

2026-05-19

## Context

The original architecture uses synchronous polling: the frontend requests events every 60 seconds, the backend fetches raw articles from external APIs, calls the Location Extraction service, caches results in memory, and returns to the frontend — all within a single request cycle.

This design has several problems:

1. **Request latency depends on external API speed** — if an external feed is slow or down, the user's request hangs or fails entirely.
2. **No persistence** — the in-memory cache loses all data on restart. Every 60 seconds, the backend must re-fetch and re-process everything.
3. **No retry mechanism** — if location extraction fails for an article, the article is silently dropped. No replay or recovery path.
4. **Single point of failure** — the backend handles both ingestion and serving. An ingestion bug can take down the serving path.

The system needs a decoupled ingestion approach where data is fetched, extracted, and persisted independently of user-facing serving.

## Decision

Replace synchronous polling with a **cron-triggered batch ingestion pipeline**:

1. A dedicated **Ingestion Worker** (Node.js) runs on configurable per-source cron schedules.
2. On each trigger, the worker fetches articles from the configured external API, checks deduplication against the database, calls the Location Extraction service for new articles, and persists the enriched results to PostgreSQL.
3. The **Serving API** (Node.js + Express) is a separate service that reads from PostgreSQL only. It has no knowledge of external APIs, location extraction, or ingestion scheduling.
4. No message queue is used. Cron scheduling is sufficient for news-cycle data freshness requirements and avoids the operational complexity of managing a queue broker.

### Per-Source Schedule

Each external API source has an independent cron expression configured in the ingestion worker's config. For example:

| Source        | Schedule         | Rationale                  |
| ------------- | ---------------- | -------------------------- |
| mock-feed     | Every 5 minutes  | Test data, fast turnaround |
| Real news API | Every 15 minutes | Typical news cycle         |
| Alert feed    | Every 1 minute   | Time-sensitive events      |

## Consequences

### Positive

- Ingestion latency decoupled from serving latency — users always get fast responses from the database
- Failed location extraction calls are retried on the next ingestion cycle; no article is silently dropped
- Data survives restarts via PostgreSQL persistence
- Serving API remains available and fast even when external APIs are down (stale data > no data)
- Each cycle processes only new articles (dedup gate), keeping extraction load constant
- No queue infrastructure to operate (Redis, RabbitMQ, Kafka)

### Negative

- Data freshness is bounded by the cron interval — no true real-time updates
- Without a queue, repeated failures of the same external API can waste extraction calls (can be mitigated by source health checks)
- The ingestion worker must implement its own retry/backoff logic per source

### Neutral

- Cron schedule is simple but less flexible than a queue for dynamic prioritization
- Adding a queue later (BullMQ, RabbitMQ) is straightforward: replace the cron trigger with a queue producer, and the ingestion worker becomes a queue consumer
