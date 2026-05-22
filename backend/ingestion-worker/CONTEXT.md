# Ingestion Worker — Context

## What

Cron-triggered Node.js service that polls external API sources (RSS feeds, mock-feed), normalizes articles, deduplicates against PostgreSQL via `ON CONFLICT DO NOTHING`, enriches new articles via the Location Extraction service (POST `/api/extract-location`), and persists enriched events to PostgreSQL. Pure I/O orchestration — no heavy computation.

## Architecture

### File Tree

```
backend/ingestion-worker/
├── src/
│   ├── index.ts            # Entry: init logger, load sources, start scheduler, health endpoint
│   ├── scheduler.ts        # node-cron: register per-source cron jobs (17 lines)
│   ├── runner.ts           # Per-source cycle: fetch → insert → enrich → update (40 lines)
│   ├── normalizer.ts       # Raw article → normalized (32 lines)
│   ├── enrich.ts           # LE client: POST + retry (38 lines)
│   ├── db.ts               # pg pool: INSERT ON CONFLICT, UPDATE location (46 lines)
│   ├── config.ts           # Load enabled sources from sources table (16 lines)
│   ├── logger.ts           # pino factory (5 lines)
│   └── sources/
│       ├── adapter.ts      # SourceConfig + FetchDeps types (8 lines)
│       ├── mock-feed.ts    # RSS fetch + XML parse + normalize (58 lines)
│       └── registry.ts     # Adapter registry: registerAdapter + getAdapter (16 lines)
├── tests/
│   ├── helpers.ts          # DB pool, migration, cleanup
│   ├── integration-runner.ts # Docker compose orchestrator
│   ├── unit/
│   │   ├── enrich.test.ts      # 2 tests
│   │   ├── index.test.ts       # 2 tests
│   │   ├── normalizer.test.ts  # 2 tests
│   │   ├── runner.test.ts      # 2 tests
│   │   ├── scheduler.test.ts   # 1 test
│   │   └── registry.test.ts   # 3 tests
│   └── integration/
│       ├── helpers.ts          # Service health checks
│       ├── config.test.ts      # 2 tests
│       ├── db.test.ts          # 3 tests
│       ├── enrich.test.ts      # 1 test
│       ├── full-cycle.test.ts  # 1 test
│       └── mock-feed.test.ts   # 1 test
├── CONTEXT.md
├── AGENTS.md
├── README.md
├── package.json
└── tsconfig.json
```

### Data Flow (per-source cycle)

```
Scheduler (node-cron) → Runner → SourceAdapter.fetchArticles()
    → INSERT ... ON CONFLICT DO NOTHING (dedup)
    → For each new article: POST /api/extract-location
    → UPDATE events SET location = ...
    → Log summary
```

### Module Contracts

| Module                 | Exports                                                                   | Signature                                  |
| ---------------------- | ------------------------------------------------------------------------- | ------------------------------------------ |
| `index.ts`             | `main(env: Env) => Promise<http.Server>`                                  | Entry point                                |
| `scheduler.ts`         | `startScheduler(sources, runFn) => () => void`                            | Registers cron per source, returns stop fn |
| `runner.ts`            | `runSource(sourceConfig, deps) => Promise<void>`                          | Orchestrates one source cycle              |
| `normalizer.ts`        | `normalizeArticle(raw, source) => NormalizedArticle`                      | Pure: raw RSS→normalized                   |
| `enrich.ts`            | `extractLocation(text, {url}) => Promise<GeoJsonFeatureCollection\|null>` | LE client with retry                       |
| `db.ts`                | `insertEvents(pool, articles) => Promise<{inserted,skipped}>`             | Row-by-row INSERT                          |
| `db.ts`                | `updateLocation(pool, source, sourceId, geoJson) => Promise<void>`        | UPDATE event location                      |
| `config.ts`            | `loadSources(pool) => Promise<SourceRow[]>`                               | Query enabled sources                      |
| `logger.ts`            | `createLogger(level?) => pino.Logger`                                     | Factory                                    |
| `sources/mock-feed.ts` | `fetchArticles(config, deps?) => Promise<NormalizedArticle[]>`            | RSS fetch+parse                            |

### Type Definitions

```ts
SourceRow { id: number; name: string; type: string; config: Record<string,unknown>; schedule: string; }
NormalizedArticle { source_id: string; title: string; description: string|undefined; url: string; published_at: string; source: string; }
GeoJsonFeatureCollection { type: "FeatureCollection"; features: Array<{type:"Feature"; geometry:{type:string;coordinates:unknown}; properties:Record<string,unknown>}>; }
RunnerDeps { fetch; pool; fetchArticles; insertEvents; updateLocation; extractLocation; locationExtractionUrl; logger; }
```

## Decisions

| Decision             | Choice                                                        | Rationale                                          |
| -------------------- | ------------------------------------------------------------- | -------------------------------------------------- |
| Batch ingestion      | Cron-triggered worker (ADR-009)                               | Simpler than queue, sufficient for news-cycle data |
| Service split        | Separate worker + API (ADR-011)                               | Independent scaling, failure isolation             |
| Dedup                | `(source,source_id)` UNIQUE + content hash fallback (ADR-012) | Atomic, no race window                             |
| In-process scheduler | node-cron                                                     | No external cron dependency                        |
| Source config        | `sources` DB table                                            | Dynamic registration without restart               |
| Language             | TypeScript (ADR-015)                                          | Module contracts at compile time                   |
| Migrations           | node-pg-migrate (ADR-014)                                     | Node.js-native, no Python runtime dep              |
| HTTP client          | Built-in `undici` fetch                                       | No external dep                                    |
| XML parsing          | fast-xml-parser                                               | RSS feed support                                   |

## Database Schema

```sql
CREATE TABLE sources (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    adapter     TEXT NOT NULL,
    endpoint    TEXT NOT NULL,
    schedule    TEXT NOT NULL,
    enabled     BOOLEAN NOT NULL DEFAULT true,
    config      JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE events (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    source_id       TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    url             TEXT,
    published_at    TIMESTAMPTZ,
    location        GEOMETRY(Point, 4326),
    location_name   TEXT,
    country         TEXT,
    confidence      REAL,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_events_source_source_id UNIQUE (source, source_id)
);
```

## Configuration

| Variable                  | Default                                                   | Description     |
| ------------------------- | --------------------------------------------------------- | --------------- |
| `DATABASE_URL`            | `postgres://livingmap:livingmap@localhost:5432/livingmap` | PostgreSQL      |
| `LOCATION_EXTRACTION_URL` | `http://localhost:8000`                                   | LE service      |
| `PORT`                    | `3003`                                                    | Health endpoint |
| `LOG_LEVEL`               | `info`                                                    | Pino level      |

## Infrastructure (docker-compose)

- `postgres` — PostgreSQL + PostGIS
- `location-extraction` — Python FastAPI for NLP
- `mock-feed` — Test RSS feed server
- `ingestion-worker` — This service
- `api` — Express serving API (separate)

## Running

```bash
# Unit tests
node --test --experimental-strip-types tests/unit/*.test.ts

# Integration tests (auto-manages Docker)
npm run test:int

# All tests
npm run test:all

# Type-check
tsc --noEmit

# Start
npm start
```

---

## Progress

| Cycle | Module                              | Test file        | Src file                      | Status  | Notes                                                            |
| ----- | ----------------------------------- | ---------------- | ----------------------------- | ------- | ---------------------------------------------------------------- |
| 1     | db.ts, runner.ts                    | —                | —                             | pending | Batch INSERT + fix dedup tracking                                |
| 2     | runner.ts, scheduler.ts             | —                | —                             | pending | Error-resilient runner with retry                                |
| 3     | logger.ts, adapter.ts, scheduler.ts | —                | —                             | pending | Consolidate shallow modules                                      |
| 4     | index.ts, sources/                  | registry.test.ts | index.ts, sources/registry.ts | done    | Dynamic source adapter registry — extracted from index.ts switch |
| 5     | index.ts                            | —                | —                             | pending | Graceful shutdown (SIGTERM drain)                                |

## Last Session

**Date:** 2026-05-22
**Cycles completed:** Candidate 4 — Dynamic source adapter registry
**Cycles attempted:** 4
**Outcome:** Extracted hardcoded adapter `switch` from `index.ts` into dedicated `src/sources/registry.ts` module. `index.ts` now calls `getAdapter(type)` instead of maintaining a switch. Added 3 unit tests for registry behavior.
**Blockers:** (null)
**Files created/modified:**

- `src/sources/registry.ts` (created) — Adapter registry with `registerAdapter` + `getAdapter`
- `tests/unit/registry.test.ts` (created) — 3 tests (known type, unknown type throws, dynamic registration)
- `src/index.ts` (modified) — Removed `createFetchArticles` switch, removed `mock-feed` import, uses `getAdapter`
- `CONTEXT.md` (modified) — Updated progress table, file tree, last session
  **Tests passing:** Yes — 12 unit tests pass, tsc --noEmit clean
  **Next action:** User selects next candidate from the architectural friction summary.

## Architectural Friction Summary

1. **Bug in dedup tracking** — `runner.ts` uses `articles.slice(0, inserted)` to identify new articles, but `insertEvents` doesn't return _which_ articles were inserted. Interleaved duplicates produce incorrect enrichment targets.
2. **Row-by-row INSERT** — `db.ts:insertEvents` does N individual INSERTs instead of batch. Architecture doc claims "Batch INSERT (100/batch)" but code doesn't implement it.
3. **Missing error handling** — Runner has no try/catch. Errors propagate as unhandled rejections in cron jobs. Architecture doc describes retry behavior that isn't implemented at the orchestration level.
4. **Shallow modules** — `logger.ts` (5 lines), `sources/adapter.ts` (8 lines), `scheduler.ts` (17 lines) add file navigation overhead with minimal logic.
5. **Hardcoded adapter registry** — `index.ts` has a switch statement for source types. Adding a source requires modifying the entry point.

## Handoff

_Fresh agent starts here. Read Progress table and Last Session. Start when user selects a candidate. Update this file after each session._
