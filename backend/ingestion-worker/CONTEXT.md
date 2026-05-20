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
│   ├── index.ts            # Entry: init logger, load sources, start scheduler, health endpoint
│   ├── scheduler.ts        # node-cron: register per-source cron jobs
│   ├── runner.ts           # Per-source cycle: fetch → normalize → dedup → enrich → write
│   ├── normalizer.ts       # Pure function: raw article → {source_id, title, description, url, published_at, source}
│   ├── enrich.ts           # Location Extraction client: POST /api/extract-location, retry logic
│   ├── db.ts               # pg pool: INSERT ON CONFLICT, UPDATE location
│   ├── config.ts           # Load enabled sources from PostgreSQL `sources` table
│   ├── logger.ts           # pino structured logger wrapper
│   └── sources/
│       ├── adapter.ts      # Abstract adapter interface + type defs
│       └── mock-feed.ts    # Fetch mock-feed RSS, parse, normalize
├── tests/
│   ├── helpers.ts          # Shared: DB pool creation, migration runner
│   ├── unit/               # Fast, mocked I/O
│   │   ├── normalizer.test.ts
│   │   ├── enrich.test.ts
│   │   ├── runner.test.ts
│   │   ├── scheduler.test.ts
│   │   └── index.test.ts
│   └── integration/        # Real I/O, Docker services
│       ├── helpers.ts      # Integration: Docker compose lifecycle, service URLs
│       ├── mock-feed.test.ts
│       ├── enrich.test.ts
│       ├── db.test.ts
│       ├── config.test.ts
│       └── full-cycle.test.ts
├── tsconfig.json
├── package.json
├── AGENTS.md
└── CONTEXT.md               ← this file
```

### Module Contracts

All source files are TypeScript (`.ts`). Types defined per module below.

#### `src/normalizer.ts`

```ts
interface RawArticle {
  guid?: string;
  title: string;
  description?: string;
  link: string;
  pubDate: string;
}

interface NormalizedArticle {
  source_id: string;
  title: string;
  description: string | undefined;
  url: string;
  published_at: string;
  source: string;
}

// source_id priority:
//   1. raw.guid (RSS guid)
//   2. SHA-256(raw.title + raw.pubDate) if no guid
function normalizeArticle(raw: RawArticle, source: string): NormalizedArticle;
```

#### `src/sources/mock-feed.ts`

```ts
interface SourceConfig {
  url: string;
  source: string;
  // adapter-specific options
}

interface FetchDeps {
  fetch: typeof global.fetch;
}

async function fetchArticles(
  config: SourceConfig,
  deps?: FetchDeps,
): Promise<NormalizedArticle[]>;
```

#### `src/enrich.ts`

```ts
// Sends article text to Location Extraction service.
// Returns GeoJSON FeatureCollection, or null after exhausting retries.
async function extractLocation(
  text: string,
  config: { url: string },
): Promise<GeoJSON.FeatureCollection | null>;
```

#### `src/db.ts`

```ts
// Batch insert articles, dedup via ON CONFLICT DO NOTHING.
async function insertEvents(
  pool: pg.Pool,
  articles: NormalizedArticle[],
): Promise<{ inserted: number; skipped: number }>;

// Update event with location GeoJSON after enrichment.
async function updateLocation(
  pool: pg.Pool,
  source: string,
  sourceId: string,
  geoJson: GeoJSON.FeatureCollection,
): Promise<void>;
```

#### `src/config.ts`

```ts
interface SourceRow {
  id: number;
  name: string;
  type: string;
  config: Record<string, unknown>;
  schedule: string;
}

async function loadSources(pool: pg.Pool): Promise<SourceRow[]>;
```

#### `src/runner.ts`

```ts
interface RunnerDeps {
  fetch: typeof global.fetch;
  pool: pg.Pool;
  extractLocation: typeof extractLocation;
  logger: pino.Logger;
}

async function runSource(
  sourceConfig: SourceRow,
  deps: RunnerDeps,
): Promise<void>;
```

#### `src/scheduler.ts`

```ts
// Register cron jobs for all sources. Returns stop function.
function startScheduler(
  sources: SourceRow[],
  runFn: (source: SourceRow) => Promise<void>,
): () => void;
```

#### `src/index.ts`

```ts
interface Env {
  PORT?: string;
  DATABASE_URL?: string;
  LOCATION_EXTRACTION_URL?: string;
  LOG_LEVEL?: string;
}

async function main(env: Env): Promise<void>;
```

### `src/logger.ts`

```ts
function createLogger(level?: string): pino.Logger;
```

## Decisions

| Decision        | Choice                       | Rationale                                   |
| --------------- | ---------------------------- | ------------------------------------------- |
| Language        | TypeScript (ADR-015)         | Module contracts enforced at compile time   |
| Package manager | npm (ADR-013)                | Consistent with mock-feed                   |
| Module system   | ESM (`"type": "module"`)     | Same as mock-feed                           |
| Runtime flag    | `--experimental-strip-types` | Run `.ts` directly, no build step (ADR-015) |
| Test runner     | `node:test` + `node:assert`  | Zero dep, Node built-in                     |
| DB library      | `pg` (node-postgres)         | Pool management, battle-tested              |
| Scheduling      | `node-cron`                  | In-process, no external dep                 |
| Logging         | `pino`                       | Structured JSON, Docker-friendly            |
| XML             | `fast-xml-parser`            | RSS parsing                                 |
| HTTP            | `undici` (built-in `fetch`)  | No extra dep                                |
| Migration       | node-pg-migrate (ADR-014)    | DB schema versioning                        |

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

| Step | Action                                                                                                                      |
| ---- | --------------------------------------------------------------------------------------------------------------------------- |
| 0a   | `backend/ingestion-worker/package.json` — ESM, deps: `pg`, `node-cron`, `pino`, `fast-xml-parser`                           |
| 0b   | `backend/migrations/001_create-events-and-sources.js` — node-pg-migrate with `pgm.createTable()` for `sources` and `events` |
| 0c   | `tests/helpers.ts` — `createTestPool()`, `runMigrations()`, `cleanTables()`                                                 |
| 0d   | `tests/integration/helpers.ts` — `ensureServices()`, `MOCK_FEED_URL`, `LE_URL`, `DATABASE_URL`                              |
| 0e   | `tsconfig.json` — strict TS config, `allowImportingTsExtensions`, `noEmit`                                                  |
| 0f   | `npm install` with devDeps: `typescript`, `@types/node`, `@types/pg` in `backend/ingestion-worker/`                         |

### Unit Cycles (fast, mocked I/O)

| #   | RED: write this test                                                                                                                                                                                                                                                                              | GREEN: write this src                                                                                                 | What it proves                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| 1   | `tests/unit/normalizer.test.ts` — `normalizeArticle({guid:"abc", title:"X", description:"Y", link:"http://...", pubDate:"2026-01-01"}, "mock-feed")` returns `{source_id:"abc", title:"X", description:"Y", url:"http://...", published_at:"2026-01-01T00:00:00.000Z", source:"mock-feed"}`       | `src/normalizer.ts` — extract `guid` → `source_id`, map fields                                                        | Pure function, stable ID                      |
| 2   | Same file, new test: no `guid` → `source_id` = SHA-256(title + published_at)                                                                                                                                                                                                                      | Same module: add `crypto.createHash('sha256')` fallback                                                               | Content hash fallback                         |
| 3   | `tests/unit/enrich.test.ts` — mock `fetch` returns `{ok:true, json: async() => geoJson}` → `extractLocation("text", {url})` returns geoJson                                                                                                                                                       | `src/enrich.ts` — POST to `${url}/api/extract-location`, parse response                                               | Basic HTTP client                             |
| 4   | Same file: mock `fetch` fails 3 times (network errors) → returns `null`                                                                                                                                                                                                                           | Same module: retry loop 3 attempts, exponential backoff 1s/4s/16s                                                     | Retry + graceful degradation                  |
| 5   | `tests/unit/runner.test.ts` — inject mock adapter returns articles, mock `insertEvents` returns inserted, mock `extractLocation` returns geoJson, mock `updateLocation` succeeds, mock logger → `runSource(config, deps)` asserts effect counts (N enrich, M updates, summary log) not call order | `src/runner.ts` — orchestrate: fetch → insert → filter new → enrich each → update each → log summary                  | Orchestration wiring, effect-count assertions |
| 6   | Same file: insert returns 0 inserted → `extractLocation` never called                                                                                                                                                                                                                             | Same module                                                                                                           | Skip enrichment on duplicates                 |
| 7   | `tests/unit/scheduler.test.ts` — mock `cron.schedule()`, mock `runFn` → `startScheduler([source1, source2], runFn)` calls `cron.schedule()` twice                                                                                                                                                 | `src/scheduler.ts` — loop sources, `cron.schedule(source.schedule, () => runFn(source))`                              | Cron registration                             |
| 8   | `tests/unit/index.test.ts` — mock all deps, `main()` starts scheduler + health server responding `{status:"ok"}`                                                                                                                                                                                  | `src/index.ts` — init logger, load config, start scheduler, create express app on $PORT, `GET /health` returns status | Entry point wiring                            |

### Integration Cycles (real I/O, Docker services)

| #   | RED: write this test                                                                                                                                                     | GREEN: implement                                                                                                           | Infrastructure                       |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| 9   | `tests/integration/mock-feed.test.ts` — `fetchArticles({url:"http://localhost:3001/feed?count=3", source:"mock-feed"})` returns 3 normalized articles with correct shape | `src/sources/mock-feed.ts` — fetch RSS XML, parse with `fast-xml-parser`, normalize each `<item>` via `normalizeArticle()` | Docker: mock-feed on :3001           |
| 10  | `tests/integration/enrich.test.ts` — `extractLocation("Flood in Paris", {url:"http://localhost:8000"})` returns `{type:"FeatureCollection", features:[...]}`             | Already implemented in unit cycles. Integration confirms real service.                                                     | Docker: location-extraction on :8000 |
| 11  | `tests/integration/db.test.ts` — migrate DB, `insertEvents(realPool, articles)` returns actual inserted count, verify row exists, `updateLocation()` updates row         | Integration confirms real SQL (no unit mock).                                                                              | Docker: PostgreSQL                   |
| 12  | `tests/integration/config.test.ts` — seed `sources` table, `loadSources(realPool)` returns correct config                                                                | Integration confirms real config loading (no unit mock).                                                                   | Docker: PostgreSQL                   |
| 13  | `tests/integration/full-cycle.test.ts` — seed `sources` row for mock-feed, call `runSource(config, realDeps)`, verify events table has enriched rows with location       | Wiring of all real modules                                                                                                 | Docker: PG + mock-feed + LE          |

## Integration Test Infrastructure

Each integration test uses `tests/integration/helpers.js` which provides:

```ts
// Before all integration tests:
//   1. Check Docker services are healthy (mock-feed:3001, LE:8000, PG:5432)
//   2. Run migrations against test DB
//   3. Export service URLs

export const MOCK_FEED_URL: string = "http://localhost:3001";
export const LE_URL: string = "http://localhost:8000";
export const DATABASE_URL: string =
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
node --test --experimental-strip-types tests/unit/*.test.ts

# Integration tests (requires Docker services)
node --test --experimental-strip-types tests/integration/*.test.ts

# All tests
node --test --experimental-strip-types tests/**/*.test.ts

# Type-check (no emit)
tsc --noEmit
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

| Cycle | Module            | Test file                            | Src file                 | Status  | Notes                                       |
| ----- | ----------------- | ------------------------------------ | ------------------------ | ------- | ------------------------------------------- |
| 0     | setup             | —                                    | —                        | done    | Scaffold, tsconfig, migration, test helpers |
| 1     | normalizer        | tests/unit/normalizer.test.ts        | src/normalizer.ts        | done    | Stable guid → source_id                     |
| 2     | normalizer        | tests/unit/normalizer.test.ts        | src/normalizer.ts        | done    | Content hash fallback (no guid)             |
| 3     | enrich            | tests/unit/enrich.test.js            | src/enrich.js            | pending | Mock fetch returns GeoJSON                  |
| 4     | enrich            | tests/unit/enrich.test.js            | src/enrich.js            | pending | Retry 3x then return null                   |
| 5     | runner            | tests/unit/runner.test.js            | src/runner.js            | pending | Effect-count assertions                     |
| 6     | runner            | tests/unit/runner.test.js            | src/runner.js            | pending | Skip enrich on duplicate                    |
| 7     | scheduler         | tests/unit/scheduler.test.js         | src/scheduler.js         | pending | Cron registration per source                |
| 8     | index             | tests/unit/index.test.js             | src/index.js             | pending | Health endpoint + init wiring               |
| 9     | mock-feed adapter | tests/integration/mock-feed.test.js  | src/sources/mock-feed.js | pending | Real HTTP to mock-feed                      |
| 10    | enrich            | tests/integration/enrich.test.js     | src/enrich.js            | pending | Real POST to LE service                     |
| 11    | db                | tests/integration/db.test.js         | src/db.js                | pending | Real PG insert/update                       |
| 12    | config            | tests/integration/config.test.js     | src/config.js            | pending | Real PG config loading                      |
| 13    | full-cycle        | tests/integration/full-cycle.test.js | all modules              | pending | End-to-end with all real services           |

## Last Session

**Date:** 2026-05-20
**Cycles completed:** 0, 1, 2
**Cycles attempted:** 0, 1, 2
**Outcome:** Cycles 0-2 done in JS. Then converted to TS per ADR-015:

- ADR-015 written
- All existing `.js` files converted to `.ts` with type annotations
- `tsconfig.json` created
- `typescript`, `@types/node`, `@types/pg` added as devDeps
- `--experimental-strip-types` flag added to all scripts
- Tests pass with TS (2/2), `tsc --noEmit` clean
- Docs updated: `overview.md`, `ingestion-worker.md`
  **Blockers:** none
  **Files created/modified:**
- docs/decisions/ADR-015-typescript-for-node-services.md (new)
- backend/ingestion-worker/tsconfig.json (new)
- backend/ingestion-worker/src/normalizer.ts (new, was .js)
- backend/ingestion-worker/tests/unit/normalizer.test.ts (new, was .js)
- backend/ingestion-worker/tests/helpers.ts (new, was .js)
- backend/ingestion-worker/tests/integration/helpers.ts (new, was .js)
- backend/ingestion-worker/package.json (updated)
- docs/architecture/ingestion-worker.md (updated)
- docs/architecture/overview.md (updated)
- CONTEXT.md (this file, updated)
  **Tests passing:** 2/2 (normalizer unit tests with TS)
  **Next action:** Cycle 3 — enrich.ts basic HTTP client (RED→GREEN).

## Handoff

_Fresh agent starts here. Read Progress table and Last Session. Start at the first `pending` cycle. Update this file after each session._
