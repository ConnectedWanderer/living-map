# AI Agent Instructions

This document provides AI-specific guidance for developing or maintaining this service.
For human-oriented documentation, see [README.md](README.md).

For architecture details, see [Architecture Documentation](../../docs/architecture/ingestion-worker.md).
For repo-wide code quality conventions (formatting, pre-commit), see [Root AGENTS.md](../../AGENTS.md).

## Quick Commands

```bash
# Unit tests only (fast)
node --test --experimental-strip-types tests/unit/*.test.ts

# Integration tests (auto-manages Docker via orchestrator)
npm run test:int

# All tests (unit + integration via orchestrator)
npm run test:all

# Type-check (no emit)
tsc --noEmit

# Start service
npm start

# Docker
docker-compose up --build
```

## Development Workflow

### TDD Approach

Each cycle:

1. **RED** — Write a failing test for one behavior
2. **GREEN** — Write minimal code to pass
3. **REFACTOR** — Clean up, run all previous tests

One test at a time. Vertical slices only — never write all tests first.

### Adding New Sources

1. Create adapter in `src/sources/` implementing the adapter interface
2. Add unit tests in `tests/unit/`
3. Add integration tests in `tests/integration/`
4. Register source type in `src/config.ts` if needed

### Adding New Modules

1. Create module in appropriate `src/` subdirectory
2. Add corresponding test file in `tests/unit/`
3. Update `src/runner.ts` to integrate new module
4. Update integration tests

## Code Conventions

TypeScript (strict) via `tsconfig.json`:

- **Module system**: ESM (`"type": "module"` in package.json)
- **Runtime flag**: `--experimental-strip-types` — run `.ts` directly, no build step
- **Test runner**: `node:test` + `node:assert` — zero dep, Node built-in
- **No mocks at system boundaries** — HTTP and DB mocked only in unit tests

## Structure

```
src/
├── index.ts            # Entry: init logger, load sources, start scheduler, health endpoint
├── scheduler.ts        # node-cron: register per-source cron jobs
├── runner.ts           # Per-source cycle: fetch → normalize → dedup → enrich → write
├── normalizer.ts       # Pure function: raw article → normalized article
├── enrich.ts           # Location Extraction client: POST /api/extract-location, retry logic
├── db.ts               # pg pool: INSERT ON CONFLICT, UPDATE location
├── config.ts           # Load enabled sources from PostgreSQL `sources` table
├── logger.ts           # pino structured logger wrapper
└── sources/
    ├── adapter.ts      # Abstract adapter interface + type defs
    └── mock-feed.ts    # Fetch mock-feed RSS, parse, normalize
```

## Troubleshooting

| Symptom                        | Fix                                                                                                          |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| Dependencies not found         | `npm install`                                                                                                |
| Type errors                    | `tsc --noEmit` to check                                                                                      |
| Integration tests fail         | Run `npm run test:int` to auto-start Docker. Debug logs: `docker compose -f ../docker-compose.test.yml logs` |
| node-cron jobs not firing      | Check cron expressions in `sources` table                                                                    |
| Location enrichment returns [] | Verify Location Extraction service is healthy on port 8000                                                   |

## npm Commands Reference

| Command             | Description                                              |
| ------------------- | -------------------------------------------------------- |
| `npm install`       | Install all dependencies                                 |
| `npm start`         | Run service (node --experimental-strip-types)            |
| `npm test`          | Run unit tests only                                      |
| `npm run test:all`  | All tests (unit + integration via orchestrator)          |
| `npm run test:int`  | Integration tests (auto-manages Docker via orchestrator) |
| `npm run typecheck` | Type-check with `tsc --noEmit`                           |

## Related Documentation

- [README.md](README.md) — End-user documentation (setup, API, Docker)
- [Architecture Documentation](../../docs/architecture/ingestion-worker.md) — Deep design doc
- [ADR-013](../../docs/decisions/ADR-013-npm-package-manager.md) — npm package manager choice
- [ADR-014](../../docs/decisions/ADR-014-node-pg-migrate-for-db-migrations.md) — node-pg-migrate for DB migrations
- [ADR-015](../../docs/decisions/ADR-015-typescript-for-node-services.md) — TypeScript for Node services
