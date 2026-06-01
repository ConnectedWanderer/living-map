# AI Agent Instructions

See [README.md](README.md) for human docs.
See [architecture doc](../../docs/architecture/serving-api.md) for design.

## Development Workflow

TDD: red-green-refactor, one behavior at a time, vertical slices only.

To add a test: create `tests/unit/<module>.test.ts` using `node:test` + `node:assert`.

## Code Conventions

- **Lint/format**: [biome.json](biome.json)
- **`console.log`**: banned — use Express error handling
- **No mocks at system boundaries**: HTTP and DB mocked only in unit tests

## Integration Testing

Integration tests use Testcontainers (no Docker Compose in test code):

- `npm run test:int` — runs integration tests with Testcontainers + PostGIS
