# ADR-013: npm as Package Manager

## Status

Accepted

## Date

2026-05-19

## Context

The project has multiple Node.js services planned: `mock-feed` (existing), `api` (planned), `ingestion-worker` (planned), and a Vue 3 + Vite frontend (planned). A package manager choice affects developer workflow, CI speed, Docker image size, and cross-service consistency.

Options considered:

- **npm** — bundled with Node.js, lockfile v3
- **pnpm** — content-addressable storage, disk-efficient, strict dependency isolation
- **yarn (v4)** — fast, PnP mode, mature workspaces
- **bun** — all-in-one runtime + package manager, fastest installs

### Current State

`mock-feed` already uses npm (`package-lock.json` with lockfileVersion 3). No other package manager traces exist in the repository. The project is not a monorepo — each service lives in its own `backend/<name>/` directory with independent `package.json`.

## Decision

Use **npm** as the package manager for all Node.js services in this project.

## Consequences

### Positive

- **Zero migration cost** — mock-feed already uses npm. All future services match existing convention.
- **Built into Node.js** — no extra install step in Docker images or CI. Node 22 ships with npm 10.
- **Universal familiarity** — every Node.js developer knows npm. No learning curve.
- **Simpler Docker images** — `node:22-alpine` includes npm. No need to install pnpm/yarn in build stage.
- **Standard lockfile** — GitHub Dependabot, Renovate, and Snyk all support `package-lock.json` natively.
- **Sufficient for scale** — at ~4 services and <1000 users, npm's performance is more than adequate. pnpm's disk savings and strictness add complexity without meaningful benefit at this scale.
- **Workspaces available if needed** — if the project evolves into a monorepo, npm workspaces (v7+) handle it without migrating package managers.

### Negative

- **No content-addressable storage** — `node_modules` duplication across services wastes disk space (negligible at 4 services, ~50-100MB each).
- **No strict dependency isolation** — pnpm's hoisting prevention catches undeclared dependency usage. npm hoists by default, allowing accidental access to transitive deps. Mitigated by good linting and `node:test` isolation.
- **Slightly slower installs than pnpm/yarn** — differences are seconds, not minutes, at this scale.

### Neutral

- If the project grows to 10+ internal packages, migrating to pnpm (or npm workspaces) is straightforward — just delete `node_modules` + `package-lock.json`, add `pnpm-workspace.yaml`, and reinstall.
- CI caching currently works with `npm ci`; switching managers would require cache invalidation.
