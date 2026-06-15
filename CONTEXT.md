# Context: Applying ADR-022 — Scaleway Serverless Deployment

> **Status:** Steps 1-2 (refactoring ingestion-job & les-job) **DONE** (from ADR-021 plan). Step 3 (Tile API → Serverless Container) **PENDING**. Provider switched from GCP Cloud Run to **Scaleway Serverless** per ADR-022.

## Objective

Migrate from Oracle ARM + Coolify to **Scaleway Serverless + Supabase + GitHub Pages**. Transform the two long-running HTTP services (Ingestion Worker, LES) into one-shot Serverless Jobs, keep the Tile API as a scale-to-zero Serverless Container, and serve the frontend as a static site from GitHub Pages. No code changes needed from the ADR-021 refactoring — only the provider CLI and CI/CD pipeline change.

## Summary of Architectural Changes

| Component | Current | Target |
|---|---|---|
| Frontend | Docker + nginx on Oracle VM | Static build on GitHub Pages |
| Tile API | Express server (Docker) | Scaleway Serverless Container (scale-to-zero) |
| Ingestion Worker | node-cron + HTTP server (Docker) | Scaleway Serverless Job (one-shot, no cron) |
| Location Extraction | FastAPI HTTP server (Docker) | Scaleway Serverless Job (batch, DB-driven) |
| Database | Self-hosted PostGIS (Docker) | Supabase managed PostGIS |
| Scheduling | node-cron in code | Scaleway CRON triggers (2 triggers) |
| CI/CD | Manual via Coolify git-push | GitHub Actions |
| Infra | OCI Terraform | `scw` CLI in CI/CD |
| Inter-service comm | Ingestion → LES via HTTP | Both jobs communicate via DB only |

---

## Prerequisites (manual one-time setup, must be done first)

These are NOT automated and must be done before the CI/CD can work.

1. **Create Supabase project**
   - Go to https://supabase.com → New project → select region close to Scaleway (e.g., `fr-par`)
   - Note connection string: `postgresql://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres`
   - Enable PostGIS in the SQL editor: `CREATE EXTENSION IF NOT EXISTS postgis;`
   - Run existing migration (`backend/migrations/001_schema.js`) against Supabase (manually or via `node-pg-migrate`)
   - **Caution:** Remove or guard the `pgm.createExtension("postgis")` line — Supabase may already have it

2. **Create Scaleway account**
   - Go to https://console.scaleway.com → Sign up (credit card for verification, no prepayment)
   - Create an IAM API key pair (Access Key + Secret Key) in IAM → API Keys
   - Create a Project (or use the default) and note the Project ID

3. **Create Scaleway namespaces (via `scw` CLI)**
   ```bash
   sudo pacman -S scaleway-cli
   scw init access-key=<ACCESS_KEY> secret-key=<SECRET_KEY> organization-id=<ORGANIZATION_ID> project-id=<PROJECT_ID> send-telemetry=false
   scw registry namespace create name=living-map
   scw container namespace create name=living-map
   ```
   - Note the namespace IDs for GitHub secrets

4. **Add GitHub secrets** (in repo settings)

   | Secret | Value |
   |---|---|
   | `SCW_ACCESS_KEY` | Scaleway IAM access key |
   | `SCW_SECRET_KEY` | Scaleway IAM secret key |
    | `SCW_PROJECT_ID` | Scaleway project ID |
    | `SCW_ORGANIZATION_ID` | Scaleway organization ID |
    | `SCW_NAMESPACE_ID` | Scaleway container namespace UUID |
   | `SUPABASE_DATABASE_URL` | Supabase direct connection (IPv6) for jobs |
   | `SUPABASE_POOLER_URL` | Supabase Supavisor transaction pooler (IPv4, port 6543) for Tile API |
   | `CORS_ORIGIN` | GitHub Pages URL (e.g., `https://<user>.github.io`) |
   | `VITE_API_URL` | Scaleway container URL (set after first deploy) |

---

## Step-by-step file changes

### Step 1: Refactor Ingestion Worker → `ingestion-job` ✅ DONE

**Goal:** Rewrite as a one-shot Scaleway Serverless Job. Fetch all sources, insert articles, exit. No HTTP server, no cron, no enrichment.

**Approach:** TDD (red-green-refactor). Started with `runSource()` (fetch→insert→log, no enrich), then `main()` (one-shot orchestration), then refactor cleanup.

#### Changes made (actual vs plan)

| File | What was done | Notes |
|------|---------------|-------|
| `src/index.ts` | `main()` returns `Promise<void>` — creates pool, loads sources, runs all, closes pool. Removed HTTP server, cron, enrich imports, `PORT`/`LOCATION_EXTRACTION_URL` env vars | `runSourceDeps` simplified — no enrich fields |
| `src/runner.ts` | Removed `GeoJsonFeatureCollection` import, enrich fields from `RunnerDeps`, enrich loop, `newArticles` slicing | Now fetch → insert → log only |
| `src/enrich.ts` | **Deleted** | LES job handles enrichment |
| `src/scheduler.ts` | **Deleted** | CRON triggers handle timing |
| `src/db.ts` | Removed `updateLocation()` and `GeoJsonFeatureCollection` import | Dead code — was only used by enrich flow |
| `package.json` | Removed `node-cron` dep, removed `docker:build:location-extraction-service` script, updated description | — |
| `Dockerfile` | Removed `EXPOSE 3000` | CMD unchanged |
| `tests/unit/index.test.ts` | **Deleted** instead of rewritten | Per decision: no unit test for `main()` — covered by integration test |
| `tests/unit/runner.test.ts` | Rewrote — one test asserting `insertEvents` receives articles from `fetchArticles` | Dropped logger assertion (impl detail per TDD ref). No enrich assertions |
| `tests/unit/enrich.test.ts` | **Deleted** | Module gone |
| `tests/unit/scheduler.test.ts` | **Deleted** | Module gone |
| `tests/integration/full-cycle.test.ts` | Rewrote — calls `main()` with real Postgres (Testcontainers) + mock-feed, verifies events in DB | Calls `main()` end-to-end (not just manual fetch→insert) |
| `tests/integration/db.test.ts` | Removed `updateLocation` import + location-update test case | `updateLocation` removed from db.ts |
| `tests/integration/enrich.test.ts` | **Deleted** | Module gone |
| `tests/integration/helpers.ts` | Removed `LOCATION_EXTRACTION_SERVICE_URL` | Only `MOCK_FEED_URL` remains |
| `tests/integration-runner.ts` | Removed LES container startup | Only mock-feed container started |

#### Current test results
- **6 unit tests** — all pass ✅
- **3 integration tests** — all pass ✅ (db inserts, dedup, full cycle via `main()`)
- **TypeScript** — clean, no errors ✅

#### Key design decisions (TDD)
1. **`runSource` test** — asserts `fetchArticles`→`insertEvents` orchestration through public interface (deps object). Logger assertion dropped (implementation detail, brittle).
2. **No unit test for `main()`** — decided to rely on the integration test for end-to-end coverage.
3. **`main()` doesn't close injected pool** — if `deps.pool` is provided, caller owns cleanup. Only closes pool it creates internally.
4. **Minimal `RunnerDeps`** — removed 3 enrich-related fields. `FetchDeps` kept for adapter pattern.
5. **No "0 inserted" test** — after removing enrich loop, `runSource` doesn't branch on `inserted`. Test would add no value.

---

### Step 2: Refactor LES → `les-job` ✅ DONE

**Goal:** Rewrite as a one-shot Scaleway Serverless Job. Load spaCy model once, query unprocessed events from Supabase, batch process, update locations, exit.

**Approach:** TDD (red-green-refactor). 4 cycles: `run_batch()` core logic (DB interaction with canned pipeline, no spaCy), then `main()` orchestration (injected deps + env var), then real pipeline test.

#### Changes made (actual vs plan)

| File | What was done | Notes |
|------|---------------|-------|
| `src/app.py` | Rewritten: removed FastAPI, uvicorn, `get_pipeline()`, route handlers, `_build_response()`, `_build_all_entities()`, `start()`. Added `run_batch(connection, pipeline) -> int` and `main(database_url, connection, pipeline)` | `main()` accepts optional connection/pipeline injection for testing. `run_batch()` returns count of processed events |
| `src/schemas.py` | **Deleted** | Only used by FastAPI endpoint — dead code |
| `pyproject.toml` | Added `psycopg2-binary>=2.9.0`; removed `fastapi`, `uvicorn[standard]`, `pydantic`; added `testcontainers[postgres]>=4.0.0` to dev | — |
| `Dockerfile` | Removed `EXPOSE 8000`. CMD changed to `["python", "-c", "from src.app import main; main()"]`. Removed uvicorn docs | DATABASE_URL passed at runtime |
| `.env.example` | Replaced `HOST`/`PORT` env vars with `DATABASE_URL`, `SPACY_EN_MODEL`, `SPACY_FR_MODEL` | — |
| `tests/integration/test_api.py` | **Deleted** | Was testing FastAPI endpoints via httpx ASGI client |
| `tests/integration/test_batch_job.py` | **New** — 6 tests: `run_batch()` (no unprocessed, 1 event, 3 events) + `main()` (injected deps, real pipeline, env var URL) | Uses Testcontainer PostGIS. Canned pipeline for non-model-dependent tests; real `LocationPipeline` for model_dependent test |
| `tests/integration/conftest.py` | Removed `autouse=True` from `small_nlp_models` fixture | New batch job tests don't need spaCy |

#### Current test results
- **76 unit/integration tests** — all pass (non-model-dependent) ✅
- **6 new batch job tests** — all pass (5 non-model-dependent + 1 model_dependent) ✅
- **Ruff** — clean, no errors ✅
- **TypeScript** — not applicable (Python project)

#### Key design decisions (TDD)
1. **`run_batch()` returns int** — caller (`main()`) can log count
2. **No mocking at DB boundary** — tests use real Postgres (Testcontainer); only spaCy pipeline is canned for non-model-dependent tests
3. **`main()` doesn't close injected connection** — if `connection` is provided, caller owns cleanup
4. **No unit tests for `run_batch()`** — covered by integration tests with real DB
5. **`_build_response` / `_build_all_entities` deleted** — were only used by FastAPI response layer

---

### Step 3: Tile API → Scaleway Serverless Container

**Goal:** Deploy as Serverless Container with scale-to-zero. The code is already appropriate for this.

#### `backend/api/Dockerfile` — KEEP (minor tweak)
- Already listens on PORT env var (Scaleway provides this)
- Already uses `--experimental-strip-types`
- Ensure it doesn't hardcode `EXPOSE 3002` — Scaleway ignores EXPOSE but keep for clarity

#### `backend/api/src/index.ts` — CHECK (no change needed)
- `process.env.PORT` is already used (line 14)
- `process.env.CORS_ORIGIN` is already used (line 7)
- `process.env.DATABASE_URL` is already used by `db/client.ts`

#### Scaleway Container config — NOT NEEDED (all config is in CI/CD)
- No separate YAML file needed — all configuration is passed via `scw container container create` CLI args in CI/CD

---

### Step 4: Frontend → GitHub Pages

**Goal:** Build static site with Vite, deploy to GitHub Pages. Tile API URL configured via build-time env var.

#### `frontend/src/services/api.ts` — CHECK (no change needed)
- Already reads `import.meta.env.VITE_API_URL` with fallback to `window.location.origin`
- No code change needed

#### `frontend/vite.config.ts` — MODIFY
- Add `base: '/<repo-name>/'` for GitHub Pages subpath deployment
- Or set `base` via env var for flexibility

#### `frontend/.env.production` — NEW (optional)
- Create `VITE_API_URL=https://tile-api-xxxxx.containers.fr-par.scw.cloud` (set after tile API deployed)

#### `frontend/Dockerfile` — KEEP for local dev
- No longer used for production (GitHub Pages serves static files)

#### `frontend/nginx.conf` — KEEP for local dev
- No longer used for production

---

### Step 5: CI/CD Pipeline — GitHub Actions

**Goal:** One workflow that tests, builds, pushes, and deploys all components.

#### `.github/workflows/deploy.yml` — NEW

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test-ingestion:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend/ingestion-worker
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
      - run: npm test

  test-api:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend/api
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
      - run: npm test

  test-les:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend/location-extraction-service
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen
      - run: uv run python -m pytest -m "not model_dependent"

  test-frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
      - run: npm test
      - run: npm run build

  build-and-push:
    needs: [test-ingestion, test-api, test-les, test-frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install scw CLI
        run: |
          curl -o scw -sL "https://github.com/scaleway/scaleway-cli/releases/latest/download/scw-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)"
          chmod +x scw && sudo mv scw /usr/local/bin/scw
      - name: Configure scw
        run: scw init access-key=${{ secrets.SCW_ACCESS_KEY }} secret-key=${{ secrets.SCW_SECRET_KEY }} organization-id=${{ secrets.SCW_ORGANIZATION_ID }} project-id=${{ secrets.SCW_PROJECT_ID }} send-telemetry=false
      - name: Login to Container Registry
        run: scw registry login
      - name: Build & push tile-api
        run: |
          docker build -t rg.fr-par.scw.cloud/living-map/tile-api:${{ github.sha }} -t rg.fr-par.scw.cloud/living-map/tile-api:latest backend/api
          docker push --all-tags rg.fr-par.scw.cloud/living-map/tile-api
      - name: Build & push ingestion-job
        run: |
          docker build -t rg.fr-par.scw.cloud/living-map/ingestion-job:${{ github.sha }} -t rg.fr-par.scw.cloud/living-map/ingestion-job:latest backend/ingestion-worker
          docker push --all-tags rg.fr-par.scw.cloud/living-map/ingestion-job
      - name: Build & push les-job
        run: |
          docker build -t rg.fr-par.scw.cloud/living-map/les-job:${{ github.sha }} -t rg.fr-par.scw.cloud/living-map/les-job:latest backend/location-extraction-service
          docker push --all-tags rg.fr-par.scw.cloud/living-map/les-job

  deploy-tile-api:
    needs: [build-and-push]
    runs-on: ubuntu-latest
    outputs:
      url: ${{ steps.deploy.outputs.url }}
    steps:
      - name: Install & configure scw
        run: |
          curl -o scw -sL "https://github.com/scaleway/scaleway-cli/releases/latest/download/scw-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)"
          chmod +x scw && sudo mv scw /usr/local/bin/scw
          scw init access-key=${{ secrets.SCW_ACCESS_KEY }} secret-key=${{ secrets.SCW_SECRET_KEY }} organization-id=${{ secrets.SCW_ORGANIZATION_ID }} project-id=${{ secrets.SCW_PROJECT_ID }} send-telemetry=false
      - id: deploy
        run: |
          scw container container create \
            namespace-id=${{ secrets.SCW_NAMESPACE_ID }} \
            name=tile-api \
            registry-image=rg.fr-par.scw.cloud/living-map/tile-api:${{ github.sha }} \
            min-scale=0 max-scale=1 \
            memory-limit=256 \
            privacy=public \
            env.DATABASE_URL=${{ secrets.SUPABASE_POOLER_URL }} \
            env.CORS_ORIGIN=${{ secrets.CORS_ORIGIN }} \
            2>/dev/null || \
          scw container container update ${{ secrets.SCW_NAMESPACE_ID }}/tile-api \
            registry-image=rg.fr-par.scw.cloud/living-map/tile-api:${{ github.sha }} \
            env.DATABASE_URL=${{ secrets.SUPABASE_POOLER_URL }} \
            env.CORS_ORIGIN=${{ secrets.CORS_ORIGIN }}
          echo "url=$(scw container container get ${{ secrets.SCW_NAMESPACE_ID }}/tile-api -o json | jq -r '.status.url')" >> $GITHUB_OUTPUT

  deploy-ingestion-job:
    needs: [build-and-push]
    runs-on: ubuntu-latest
    steps:
      - name: Install & configure scw
        run: |
          curl -o scw -sL "https://github.com/scaleway/scaleway-cli/releases/latest/download/scw-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)"
          chmod +x scw && sudo mv scw /usr/local/bin/scw
          scw init access-key=${{ secrets.SCW_ACCESS_KEY }} secret-key=${{ secrets.SCW_SECRET_KEY }} organization-id=${{ secrets.SCW_ORGANIZATION_ID }} project-id=${{ secrets.SCW_PROJECT_ID }} send-telemetry=false
      - run: |
          scw container job create \
            namespace-id=${{ secrets.SCW_NAMESPACE_ID }} \
            name=ingestion-job \
            registry-image=rg.fr-par.scw.cloud/living-map/ingestion-job:${{ github.sha }} \
            memory-limit=512 \
            env.DATABASE_URL=${{ secrets.SUPABASE_DATABASE_URL }} \
            2>/dev/null || \
          scw container job update ${{ secrets.SCW_NAMESPACE_ID }}/ingestion-job \
            registry-image=rg.fr-par.scw.cloud/living-map/ingestion-job:${{ github.sha }} \
            env.DATABASE_URL=${{ secrets.SUPABASE_DATABASE_URL }}

  deploy-les-job:
    needs: [build-and-push]
    runs-on: ubuntu-latest
    steps:
      - name: Install & configure scw
        run: |
          curl -o scw -sL "https://github.com/scaleway/scaleway-cli/releases/latest/download/scw-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)"
          chmod +x scw && sudo mv scw /usr/local/bin/scw
          scw init access-key=${{ secrets.SCW_ACCESS_KEY }} secret-key=${{ secrets.SCW_SECRET_KEY }} organization-id=${{ secrets.SCW_ORGANIZATION_ID }} project-id=${{ secrets.SCW_PROJECT_ID }} send-telemetry=false
      - run: |
          scw container job create \
            namespace-id=${{ secrets.SCW_NAMESPACE_ID }} \
            name=les-job \
            registry-image=rg.fr-par.scw.cloud/living-map/les-job:${{ github.sha }} \
            memory-limit=2048 \
            env.DATABASE_URL=${{ secrets.SUPABASE_DATABASE_URL }} \
            2>/dev/null || \
          scw container job update ${{ secrets.SCW_NAMESPACE_ID }}/les-job \
            registry-image=rg.fr-par.scw.cloud/living-map/les-job:${{ github.sha }} \
            env.DATABASE_URL=${{ secrets.SUPABASE_DATABASE_URL }}

  deploy-frontend:
    needs: [deploy-tile-api]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
        working-directory: frontend
      - run: npm run build
        working-directory: frontend
        env:
          VITE_API_URL: ${{ needs.deploy-tile-api.outputs.url || secrets.VITE_API_URL }}
      - uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./frontend/dist

  setup-cron-triggers:
    needs: [deploy-ingestion-job, deploy-les-job]
    runs-on: ubuntu-latest
    steps:
      - name: Install & configure scw
        run: |
          curl -o scw -sL "https://github.com/scaleway/scaleway-cli/releases/latest/download/scw-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)"
          chmod +x scw && sudo mv scw /usr/local/bin/scw
          scw init access-key=${{ secrets.SCW_ACCESS_KEY }} secret-key=${{ secrets.SCW_SECRET_KEY }} organization-id=${{ secrets.SCW_ORGANIZATION_ID }} project-id=${{ secrets.SCW_PROJECT_ID }} send-telemetry=false
      - name: Get ingestion job ID
        id: ingestion-job-id
        run: echo "id=$(scw container job list -o json | jq -r '.jobs[] | select(.name == "ingestion-job") | .id')" >> $GITHUB_OUTPUT
      - name: Get LES job ID
        id: les-job-id
        run: echo "id=$(scw container job list -o json | jq -r '.jobs[] | select(.name == "les-job") | .id')" >> $GITHUB_OUTPUT
      - name: Create or update ingestion cron (06:00 UTC)
        run: |
          CRON_ID=$(scw container cron list -o json | jq -r --arg CID "${{ steps.ingestion-job-id.outputs.id }}" '.crons[] | select(.container_id == $CID) | .id' | head -1)
          if [ -z "$CRON_ID" ]; then
            scw container cron create container-id=${{ steps.ingestion-job-id.outputs.id }} schedule="0 6 * * *" args="{}"
          else
            scw container cron update $CRON_ID schedule="0 6 * * *"
          fi
      - name: Create or update LES cron (07:00 UTC)
        run: |
          CRON_ID=$(scw container cron list -o json | jq -r --arg CID "${{ steps.les-job-id.outputs.id }}" '.crons[] | select(.container_id == $CID) | .id' | head -1)
          if [ -z "$CRON_ID" ]; then
            scw container cron create container-id=${{ steps.les-job-id.outputs.id }} schedule="0 7 * * *" args="{}"
          else
            scw container cron update $CRON_ID schedule="0 7 * * *"
          fi
```

---

### Step 6: Local Dev Adjustments

Since entry points are replaced (no more HTTP servers for ingestion/LES), the Docker Compose dev flow changes.

#### `backend/docker-compose.yml` — MODIFY
- Remove `ingestion-worker` service (or replace with a version that runs once and exits)
- Remove the `include:` for LES docker-compose (no more long-running LES)
- Remove `location-extraction` references from depends_on
- `ingestion-worker` and `location-extraction` can be run manually for dev

Scripts for local job execution:
- `npm run job` in `ingestion-worker/` — builds and runs the job once
- `uv run python -m src.app` in `location-extraction-service/` — runs batch job once

---

### Step 7: Update Documentation

#### `docs/architecture/deployment.md` — UPDATE (DONE)
- Replaced GCP Cloud Run with Scaleway Serverless
- Marked the GCP architecture as superseded (alongside existing Oracle section)
- Updated the mermaid diagram, CI/CD pipeline, runbook, and cost breakdown

#### `docs/decisions/ADR-022-scaleway-serverless-deployment.md` — NEW (DONE)
- ADR documenting the switch from GCP to Scaleway

---

## Gotchas & Warnings

1. **Supabase SSL:** Connection string needs `?sslmode=require` — verify `pg` and `psycopg2` handle this
2. **Supabase PostGIS version:** It may differ from local (3.3.7 vs 3.4). Check `SELECT PostGIS_Version();` after project creation
3. **node-pg-migrate on Supabase:** `createExtension("postgis")` may fail if already installed — `ifNotExists: true` is already set
4. **CORS:** Tile API must include GitHub Pages domain in `CORS_ORIGIN`. Current code uses a single origin — may need `CORS_ORIGIN` to allow multiple origins if both localhost and production are needed
5. **LES memory:** `en_core_web_trf` needs ~2 GB. Set `--memory-limit=2048` on the les-job
6. **Scaleway Job timeout:** Default is 1 hour — ingestion ~3 min, LES ~5 min, fine. Can be set with `--timeout` if needed
7. **Frontend base path:** If deploying to `https://<user>.github.io/<repo>/`, set `base: '/<repo>/'` in `vite.config.ts`
8. **CI ordering:** `deploy-frontend` needs tile API URL from `deploy-tile-api` — passed as job output
9. **Database URL in CI:** Stored as a GitHub secret. Both jobs require it at deploy time
10. **Mock feed:** Not affected — only used in tests and local dev
11. **Scaleway `create`/`update` pattern:** `scw container container create` fails on re-deploy (resource exists), hence the `create || update` pattern in the CI/CD workflow
12. **Scaleway free tier is pooled:** All serverless usage in an account shares 400K GB-s / 200K vCPU-s. Monitor combined usage in the Scaleway console
13. **No startup CPU boost:** Unlike Cloud Run, Scaleway doesn't offer CPU boost during cold start. The LES model load may be slightly slower on cold start
14. **Scaleway Container Registry domain:** Use `rg.fr-par.scw.cloud` for the Paris region — adjust for other regions (`nl-ams`, `pl-waw`)
