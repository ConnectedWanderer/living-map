# AI Agent Instructions

AI-specific guidance for this service. For human docs see [README.md](README.md), for architecture see [architecture doc](../../docs/architecture/ingestion-worker.md), for repo-wide conventions (formatting, pre-commit) see [root AGENTS.md](../../AGENTS.md). All commands are in [README.md Code Quality section](README.md#code-quality) and `package.json`.

## Development Workflow

TDD: red-green-refactor, one behavior at a time, vertical slices only.

To add a test: create `tests/unit/<module>.test.ts` using `node:test` + `node:assert`.

Adding a source: create adapter in `src/sources/` implementing the adapter interface, add tests, register type in `src/config.ts`.

Adding a module: create in `src/`, add tests, integrate in `src/runner.ts`, update integration tests.

## Code Conventions

- **Lint/format**: [biome.json](biome.json)
- **JSDoc required**: all exported declarations via `scripts/check-jsdoc.mjs` (TypeScript API, zero deps)
- **`console.log`**: banned — use `logger.info()` from pino
- **No mocks at system boundaries**: HTTP and DB mocked only in unit tests

## Integration Testing

Integration tests use Testcontainers (no Docker Compose in test code):

- `npm run test:int` — runner builds shared containers from Dockerfiles, per-file PostGIS via `withPostgres()` in `setup.ts`.

## Troubleshooting

| Symptom                        | Fix                                                                                                                      |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| Dependencies not found         | `npm install`                                                                                                            |
| Type errors                    | `tsc --noEmit` to check                                                                                                  |
| Integration tests fail         | Run `npm run test:int` to auto-start Testcontainers. Debug logs: inspect container logs via `docker logs <container-id>` |
| node-cron jobs not firing      | Check cron expressions in `sources` table                                                                                |
| Location enrichment returns [] | Verify Location Extraction service is healthy on port 8000                                                               |
| Want to test without waiting   | `curl -X POST http://localhost:3000/trigger` — runs all sources immediately                                              |

## Related Documentation

- [README.md](README.md), [Architecture Doc](../../docs/architecture/ingestion-worker.md)
- [ADR-013](../../docs/decisions/ADR-013-npm-package-manager.md), [ADR-014](../../docs/decisions/ADR-014-node-pg-migrate-for-db-migrations.md), [ADR-015](../../docs/decisions/ADR-015-typescript-for-node-services.md), [ADR-018](../../docs/decisions/ADR-018-testcontainers-for-integration-testing.md)
