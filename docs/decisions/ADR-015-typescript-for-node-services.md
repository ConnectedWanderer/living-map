# ADR-015: TypeScript for Node.js Services

## Status

Proposed

## Date

2026-05-20

## Context

The project has multiple Node.js services — `mock-feed` (existing, JS), `ingestion-worker` (in progress), `api` (planned). Currently all are plain JavaScript. The project has no TypeScript anywhere.

This decision covers the language for **all current and future Node.js services**.

Key factors:

- **Node 24** (`v24.14.1` in this env) ships stable `--experimental-strip-types`, allowing `.ts` files to run directly without a build step
- Services are small (hundreds of LOC each) — migration cost per service is low
- Services have explicit module contracts (adapter interfaces, dep injection shapes, DB query signatures) that benefit from compile-time checking
- `node:test` works with `--experimental-strip-types` — no test runner change
- Docker images must stay lean — no build step in `docker build`

Options considered:

1. **Plain JS with JSDoc** — status quo, consistent across services. No tooling overhead. Module contracts documented as JSDoc comments only — no compile-time enforcement.

2. **TS with `--experimental-strip-types` (Node 24+)** — write `.ts`, run directly, no build step. Type checking via `tsc --noEmit` in CI. Types are real, not comments.

3. **TS with `tsc` build step** — traditional compile-then-run. Adds build step to Docker images and dev workflow. Unnecessary overhead when Node natively runs `.ts`.

4. **JSDoc types + `tsc --allowJs --checkJs`** — type-check JS without migration, but JSDoc annotations are verbose for complex shapes and easy to let drift from implementation.

## Decision

All Node.js services in the project use **TypeScript with `--experimental-strip-types`** (option 2). Write `.ts` files, run directly with:

```
node --experimental-strip-types src/index.ts
```

No build step. Type checking runs separately via `tsc --noEmit` in CI/pre-commit.

## Consequences

### Positive

- **Real types, not comments** — module contracts (adapter return shapes, runner deps, DB interfaces, API payloads) become actual TypeScript types. Catches field-name typos, missing deps, wrong return shapes at compile time.
- **Zero build step** — Docker images are as simple as JS: `CMD ["node", "--experimental-strip-types", "src/index.ts"]`
- **`node:test` works natively** — `node --test --experimental-strip-types` handles `.test.ts` files
- **Refactoring confidence** — renaming a field across 10 files is a compiler-guided operation
- **Cross-service contracts** — types can be shared between services (e.g., RSS response shape, LE API payloads) via a shared package or type file
- **One-time migration** — `mock-feed` is small (4 source files, ~150 LOC)

### Negative

- **Migration cost** — each existing JS service must be converted to `.ts` with type annotations
- **DevDeps per service** — each service needs `typescript` + `@types/node` in devDependencies
- **CI/pre-commit step** — `tsc --noEmit` adds ~5s to the checking pipeline
- **`--experimental-strip-types` stability** — stable in Node 24 but behind a flag. Low risk of removal, but not zero. If removed, the fallback is trivial: run the same files through `tsx` or add `tsc` build.

### Neutral

- Sets a single language convention across all Node.js services
- Vue 3 frontend remains independent (already uses TS ecosystem by default)
- Migration files (`backend/migrations/*.js`) remain CommonJS — `node-pg-migrate` plugin API uses `exports.up`, not affected by this decision
