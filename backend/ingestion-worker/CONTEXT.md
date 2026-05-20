# Ingestion Worker — TDD Context

## What

Cron-triggered Node.js service that polls external sources, normalizes articles, deduplicates against PostgreSQL, enriches via Location Extraction service, and persists enriched events.

## Architecture

```
flow: SourceAdapter → Normalizer → Dedup (INSERT ON CONFLICT) → Location Extraction → DB UPDATE
```

### File Layout

```
backend/ingestion-worker/
├── src/
│   ├── index.js            # Entry: init logger, load sources, start scheduler, health endpoint
│   ├── scheduler.js        # node-cron: register per-source cron jobs
│   ├── runner.js           # Per-source cycle: fetch → normalize → dedup → enrich → write
│   ├── normalizer.js       # Pure function: raw article → {source_id, title, description, url, published_at, source}
│   ├── enrich.js           # Location Extraction client: POST /api/extract-location, retry logic
│   ├── db.js               # pg pool: INSERT ON CONFLICT, UPDATE location
│   ├── config.js           # Load enabled sources from PostgreSQL `sources` table
│   ├── logger.js           # pino structured logger wrapper
│   └── sources/
│       ├── adapter.js      # Abstract adapter interface docs (JSDoc type def)
│       └── mock-feed.js    # Fetch mock-feed RSS, parse, normalize
├── tests/
│   ├── helpers.js          # Shared: DB pool creation, migration runner
│   ├── unit/               # Fast, mocked I/O
│   │   ├── normalizer.test.js
│   │   ├── enrich.test.js
│   │   ├── runner.test.js
│   │   ├── scheduler.test.js
│   │   └── index.test.js
│   └── integration/        # Real I/O, Docker services
│       ├── helpers.js      # Integration: Docker compose lifecycle, service URLs
│       ├── mock-feed.test.js
│       ├── enrich.test.js
│       ├── db.test.js
│       ├── config.test.js
│       └── full-cycle.test.js
├── package.json
├── AGENTS.md
└── CONTEXT.md               ← this file
```

### Module Contracts

#### `src/normalizer.js`

```js
/**
 * Normalize a raw article from any source adapter to standard shape.
 * @param {object} raw - Raw article from adapter
 * @param {string} source - Source name (e.g. "mock-feed")
 * @returns {{source_id: string, title: string, description: string, url: string, published_at: string, source: string}}
 *
 * source_id source priority:
 *   1. raw.guid (RSS guid)
 *   2. SHA-256(raw.title + raw.pubDate) if neither exists
 */
export function normalizeArticle(raw, source)
```

#### `src/sources/mock-feed.js`

```js
/**
 * Fetch articles from mock-feed RSS endpoint.
 * @param {object} config - { url: string, source: string }
 * @param {object} deps - { fetch: typeof global.fetch } (injectable for tests)
 * @returns {Promise<Array<NormalizedArticle>>}
 */
export async function fetchArticles(config, deps = { fetch: global.fetch })
```

#### `src/enrich.js`

```js
/**
 * Send article text to Location Extraction service.
 * Returns GeoJSON FeatureCollection, or null after exhausting retries.
 * @param {string} text - Article title + description
 * @param {object} config - { url: string } (LE service base URL)
 * @returns {Promise<object|null>}
 */
export async function extractLocation(text, config)
```

#### `src/db.js`

```js
/**
 * Batch insert articles, dedup via ON CONFLICT DO NOTHING.
 * @param {import('pg').Pool} pool
 * @param {Array<NormalizedArticle>} articles
 * @returns {Promise<{inserted: number, skipped: number}>}
 */
export async function insertEvents(pool, articles)

/**
 * Update event with location GeoJSON after enrichment.
 * @param {import('pg').Pool} pool
 * @param {string} source
 * @param {string} sourceId
 * @param {object} geoJson - GeoJSON FeatureCollection
 */
export async function updateLocation(pool, source, sourceId, geoJson)
```

#### `src/config.js`

```js
/**
 * Load enabled source configurations from DB.
 * @param {import('pg').Pool} pool
 * @returns {Promise<Array<{id: number, name: string, type: string, config: object, schedule: string}>>}
 */
export async function loadSources(pool)
```

#### `src/runner.js`

```js
/**
 * Run one full ingestion cycle for a single source.
 * @param {object} sourceConfig - { name, type, config, schedule }
 * @param {object} deps - { fetch, pool, extractLocation, logger }
 * @returns {Promise<void>}
 */
export async function runSource(sourceConfig, deps)
```

#### `src/scheduler.js`

```js
/**
 * Register cron jobs for all sources.
 * @param {Array<object>} sources - Source configs from loadSources()
 * @param {Function} runFn - async (sourceConfig) => void
 * @returns {() => void} - Stop function to cancel all cron jobs
 */
export function startScheduler(sources, runFn)
```

#### `src/index.js`

```js
/**
 * Entry point. Init logger, load sources, start scheduler, start health server.
 * @param {object} env - { PORT, DATABASE_URL, LOCATION_EXTRACTION_URL, LOG_LEVEL }
 */
export async function main(env)
```

### `src/logger.js`

Wrapper around `pino`:

```js
export function createLogger(level = 'info')  // → pino.Logger
```

## Decisions

| Decision        | Choice                      | Rationale                        |
| --------------- | --------------------------- | -------------------------------- |
| Package manager | npm (ADR-013)               | Consistent with mock-feed        |
| Module system   | ESM (`"type": "module"`)    | Same as mock-feed                |
| Test runner     | `node:test` + `node:assert` | Zero dep, Node built-in          |
| DB library      | `pg` (node-postgres)        | Pool management, battle-tested   |
| Scheduling      | `node-cron`                 | In-process, no external dep      |
| Logging         | `pino`                      | Structured JSON, Docker-friendly |
| XML             | `fast-xml-parser`           | RSS parsing                      |
| HTTP            | `undici` (built-in `fetch`) | No extra dep                     |
| Migration       | node-pg-migrate (ADR-014)   | DB schema versioning             |

## Database Schema

### `sources` table

```sql
CREATE TABLE sources (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    type        TEXT NOT NULL,         -- 'mock-feed', 'rss', ...
    config      JSONB NOT NULL DEFAULT '{}',
    schedule    TEXT NOT NULL,         -- cron expression
    enabled     BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `events` table

```sql
CREATE TABLE events (
    id            SERIAL PRIMARY KEY,
    source        TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    url           TEXT,
    published_at  TIMESTAMPTZ,
    location      JSONB,               -- GeoJSON FeatureCollection
    location_name TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_events_source_source_id UNIQUE (source, source_id)
);
```

### Migration file

`backend/migrations/001_create-events-and-sources.js` using node-pg-migrate API.

---

## TDD Cycle Plan

Each cycle: **RED** (write failing test) → **GREEN** (minimal implementation) → **REFACTOR** (clean up, run all previous tests).

### Setup (Cycle 0)

| Step | Action                                                                                                                                |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------- |
| 0a   | `backend/ingestion-worker/package.json` — ESM, deps: `pg`, `node-cron`, `pino`, `fast-xml-parser`, devDeps: none (node:test built-in) |
| 0b   | `backend/migrations/001_create-events-and-sources.js` — node-pg-migrate with `pgm.createTable()` for `sources` and `events`           |
| 0c   | `tests/helpers.js` — `createTestPool()`, `runMigrations()`, `cleanTables()`                                                           |
| 0d   | `tests/integration/helpers.js` — `ensureServices()`, `MOCK_FEED_URL`, `LE_URL`, `DATABASE_URL`                                        |
| 0e   | `npm install` in `backend/ingestion-worker/`                                                                                          |

### Unit Cycles (fast, mocked I/O)

| #   | RED: write this test                                                                                                                                                                                                                                                                              | GREEN: write this src                                                                                                 | What it proves                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| 1   | `tests/unit/normalizer.test.js` — `normalizeArticle({guid:"abc", title:"X", description:"Y", link:"http://...", pubDate:"2026-01-01"}, "mock-feed")` returns `{source_id:"abc", title:"X", description:"Y", url:"http://...", published_at:"2026-01-01T00:00:00.000Z", source:"mock-feed"}`       | `src/normalizer.js` — extract `guid` → `source_id`, map fields                                                        | Pure function, stable ID                      |
| 2   | Same file, new test: no `guid` → `source_id` = SHA-256(title + published_at)                                                                                                                                                                                                                      | Same module: add `crypto.createHash('sha256')` fallback                                                               | Content hash fallback                         |
| 3   | `tests/unit/enrich.test.js` — mock `fetch` returns `{ok:true, json: async() => geoJson}` → `extractLocation("text", {url})` returns geoJson                                                                                                                                                       | `src/enrich.js` — POST to `${url}/api/extract-location`, parse response                                               | Basic HTTP client                             |
| 4   | Same file: mock `fetch` fails 3 times (network errors) → returns `null`                                                                                                                                                                                                                           | Same module: retry loop 3 attempts, exponential backoff 1s/4s/16s                                                     | Retry + graceful degradation                  |
| 5   | `tests/unit/runner.test.js` — inject mock adapter returns articles, mock `insertEvents` returns inserted, mock `extractLocation` returns geoJson, mock `updateLocation` succeeds, mock logger → `runSource(config, deps)` asserts effect counts (N enrich, M updates, summary log) not call order | `src/runner.js` — orchestrate: fetch → insert → filter new → enrich each → update each → log summary                  | Orchestration wiring, effect-count assertions |
| 6   | Same file: insert returns 0 inserted → `extractLocation` never called                                                                                                                                                                                                                             | Same module                                                                                                           | Skip enrichment on duplicates                 |
| 7   | `tests/unit/scheduler.test.js` — mock `cron.schedule()`, mock `runFn` → `startScheduler([source1, source2], runFn)` calls `cron.schedule()` twice                                                                                                                                                 | `src/scheduler.js` — loop sources, `cron.schedule(source.schedule, () => runFn(source))`                              | Cron registration                             |
| 8   | `tests/unit/index.test.js` — mock all deps, `main()` starts scheduler + health server responding `{status:"ok"}`                                                                                                                                                                                  | `src/index.js` — init logger, load config, start scheduler, create express app on $PORT, `GET /health` returns status | Entry point wiring                            |

### Integration Cycles (real I/O, Docker services)

| #   | RED: write this test                                                                                                                                                     | GREEN: implement                                                                                                           | Infrastructure                       |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| 9   | `tests/integration/mock-feed.test.js` — `fetchArticles({url:"http://localhost:3001/feed?count=3", source:"mock-feed"})` returns 3 normalized articles with correct shape | `src/sources/mock-feed.js` — fetch RSS XML, parse with `fast-xml-parser`, normalize each `<item>` via `normalizeArticle()` | Docker: mock-feed on :3001           |
| 10  | `tests/integration/enrich.test.js` — `extractLocation("Flood in Paris", {url:"http://localhost:8000"})` returns `{type:"FeatureCollection", features:[...]}`             | Already implemented in unit cycles. Integration confirms real service.                                                     | Docker: location-extraction on :8000 |
| 11  | `tests/integration/db.test.js` — migrate DB, `insertEvents(realPool, articles)` returns actual inserted count, verify row exists, `updateLocation()` updates row         | Integration confirms real SQL (no unit mock).                                                                              | Docker: PostgreSQL                   |
| 12  | `tests/integration/config.test.js` — seed `sources` table, `loadSources(realPool)` returns correct config                                                                | Integration confirms real config loading (no unit mock).                                                                   | Docker: PostgreSQL                   |
| 13  | `tests/integration/full-cycle.test.js` — seed `sources` row for mock-feed, call `runSource(config, realDeps)`, verify events table has enriched rows with location       | Wiring of all real modules                                                                                                 | Docker: PG + mock-feed + LE          |

## Integration Test Infrastructure

Each integration test uses `tests/integration/helpers.js` which provides:

```js
// Before all integration tests:
//   1. Check Docker services are healthy (mock-feed:3001, LE:8000, PG:5432)
//   2. Run migrations against test DB
//   3. Export service URLs

export const MOCK_FEED_URL = "http://localhost:3001";
export const LE_URL = "http://localhost:8000";
export const DATABASE_URL =
  process.env.DATABASE_URL ||
  "postgres://livingmap:livingmap@localhost:5432/livingmap_test";
```

Docker services expected running:

- `mock-feed` on port 3001
- `location-extraction` on port 8000
- `postgres` on port 5432 (with `livingmap_test` database)

## Running Tests

```bash
# Unit tests only (fast)
node --test tests/unit/*.test.js

# Integration tests (requires Docker services)
node --test tests/integration/*.test.js

# All tests
node --test tests/**/*.test.js
```

## Checklist Per Cycle

- [ ] RED: test fails with expected error/message
- [ ] GREEN: minimal code to pass — no speculative features
- [ ] All previous tests still pass
- [ ] Test uses public interface only (no internal imports)
- [ ] Test would survive internal refactor
- [ ] No mocks at system boundaries (HTTP, DB) — only in unit tests

---

## Progress

| Cycle | Module            | Test file                            | Src file                 | Status  | Notes                                           |
| ----- | ----------------- | ------------------------------------ | ------------------------ | ------- | ----------------------------------------------- |
| 0     | setup             | —                                    | —                        | pending | Scaffold, package.json, migration, test helpers |
| 1     | normalizer        | tests/unit/normalizer.test.js        | src/normalizer.js        | pending | Stable guid → source_id                         |
| 2     | normalizer        | tests/unit/normalizer.test.js        | src/normalizer.js        | pending | Content hash fallback (no guid)                 |
| 3     | enrich            | tests/unit/enrich.test.js            | src/enrich.js            | pending | Mock fetch returns GeoJSON                      |
| 4     | enrich            | tests/unit/enrich.test.js            | src/enrich.js            | pending | Retry 3x then return null                       |
| 5     | runner            | tests/unit/runner.test.js            | src/runner.js            | pending | Effect-count assertions                         |
| 6     | runner            | tests/unit/runner.test.js            | src/runner.js            | pending | Skip enrich on duplicate                        |
| 7     | scheduler         | tests/unit/scheduler.test.js         | src/scheduler.js         | pending | Cron registration per source                    |
| 8     | index             | tests/unit/index.test.js             | src/index.js             | pending | Health endpoint + init wiring                   |
| 9     | mock-feed adapter | tests/integration/mock-feed.test.js  | src/sources/mock-feed.js | pending | Real HTTP to mock-feed                          |
| 10    | enrich            | tests/integration/enrich.test.js     | src/enrich.js            | pending | Real POST to LE service                         |
| 11    | db                | tests/integration/db.test.js         | src/db.js                | pending | Real PG insert/update                           |
| 12    | config            | tests/integration/config.test.js     | src/config.js            | pending | Real PG config loading                          |
| 13    | full-cycle        | tests/integration/full-cycle.test.js | all modules              | pending | End-to-end with all real services               |

## Last Session

**Date:** —
**Cycles completed:** none
**Cycles attempted:** none
**Outcome:** Removed Cycles 5-8 (db + config unit tests) — mock at pg driver level too brittle. Runner test (now Cycle 5) changed to effect-count assertions instead of call-order.
**Blockers:** none
**Files created/modified:** CONTEXT.md (this file), docs/architecture/ingestion-worker.md
**Tests passing:** —
**Next action:** Start Cycle 0 — scaffold project structure, write `package.json`, migration file, and test helpers.

## Handoff

_Fresh agent starts here. Read Progress table and Last Session. Start at the first `pending` cycle. Update this file after each session._
