# Context: Applying ADR-021 — Serverless Free-Tier Deployment

> **Status:** Step 1 (Ingestion Worker → ingestion-job) **DONE**. Next: Step 2 (LES → les-job).

## Objective

Migrate from Oracle ARM + Coolify to **Google Cloud Run + Supabase + GitHub Pages**. Transform the two long-running HTTP services (Ingestion Worker, LES) into one-shot Cloud Run Jobs, keep the Tile API as a scale-to-zero Cloud Run Service, and serve the frontend as a static site from GitHub Pages.

## Summary of Architectural Changes

| Component | Current | Target |
|---|---|---|
| Frontend | Docker + nginx on Oracle VM | Static build on GitHub Pages |
| Tile API | Express server (Docker) | Cloud Run Service (scale-to-zero) |
| Ingestion Worker | node-cron + HTTP server (Docker) | Cloud Run Job (one-shot, no cron) |
| Location Extraction | FastAPI HTTP server (Docker) | Cloud Run Job (batch, DB-driven) |
| Database | Self-hosted PostGIS (Docker) | Supabase managed PostGIS |
| Scheduling | node-cron in code | Cloud Scheduler (2 jobs) |
| CI/CD | Manual via Coolify git-push | GitHub Actions |
| Infra | OCI Terraform | gcloud CLI in CI/CD |
| Inter-service comm | Ingestion → LES via HTTP | Both jobs communicate via DB only |

---

## Prerequisites (manual one-time setup, must be done first)

These are NOT automated and must be done before the CI/CD can work.

1. **Create Supabase project**
   - Go to https://supabase.com → New project → select region close to Cloud Run
   - Note connection string: `postgresql://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres`
   - Enable PostGIS in the SQL editor: `CREATE EXTENSION IF NOT EXISTS postgis;`
   - Run existing migration (`backend/migrations/001_schema.js`) against Supabase (manually or via `node-pg-migrate`)
   - **Caution:** Remove or guard the `pgm.createExtension("postgis")` line — Supabase may already have it

2. **Create GCP project**
   - Enable APIs: Cloud Run, Artifact Registry, Cloud Scheduler, Cloud Build
   - Create Artifact Registry repository: `gcloud artifacts repositories create living-map --repository-format=docker --location=<REGION>`

3. **Create GCP service account**
   - Roles: `roles/run.admin`, `roles/cloudscheduler.admin`, `roles/artifactregistry.writer`
   - Download JSON key

4. **Add GitHub secrets** (in repo settings)

   | Secret | Value |
   |---|---|
   | `GCP_SA_KEY` | Content of service account JSON key |
   | `GCP_PROJECT_ID` | GCP project ID |
   | `GCP_REGION` | e.g., `us-central1` |
   | `SUPABASE_DATABASE_URL` | Supabase connection string with `?sslmode=require` |
   | `CORS_ORIGIN` | GitHub Pages URL (e.g., `https://<user>.github.io`) |
   | `VITE_API_URL` | Cloud Run tile API URL (set after first deploy) |

---

## Step-by-step file changes

### Step 1: Refactor Ingestion Worker → `ingestion-job` ✅ DONE

**Goal:** Rewrite as a one-shot Cloud Run Job. Fetch all sources, insert articles, exit. No HTTP server, no cron, no enrichment.

**Approach:** TDD (red-green-refactor). Started with `runSource()` (fetch→insert→log, no enrich), then `main()` (one-shot orchestration), then refactor cleanup.

#### Changes made (actual vs plan)

| File | What was done | Notes |
|------|---------------|-------|
| `src/index.ts` | `main()` returns `Promise<void>` — creates pool, loads sources, runs all, closes pool. Removed HTTP server, cron, enrich imports, `PORT`/`LOCATION_EXTRACTION_URL` env vars | `runSourceDeps` simplified — no enrich fields |
| `src/runner.ts` | Removed `GeoJsonFeatureCollection` import, enrich fields from `RunnerDeps`, enrich loop, `newArticles` slicing | Now fetch → insert → log only |
| `src/enrich.ts` | **Deleted** | LES job handles enrichment |
| `src/scheduler.ts` | **Deleted** | Cloud Scheduler handles timing |
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

### Step 2: Refactor LES → `les-job`

**Goal:** Rewrite as a one-shot Cloud Run Job. Load spaCy model once, query unprocessed events from Supabase, batch process, update locations, exit.

#### `backend/location-extraction-service/pyproject.toml` — MODIFY
- Add `psycopg2-binary>=2.9.0` to `dependencies`
- Remove `fastapi`, `uvicorn[standard]`, `pydantic` if no longer needed locally (or keep for dev flexibility)

#### `backend/location-extraction-service/src/app.py` — REWRITE
- Replace FastAPI app + uvicorn start with a batch script `main()`
- New flow:
  1. Read `DATABASE_URL`, `SPACY_EN_MODEL`, `SPACY_FR_MODEL` from env
  2. Load `LocationPipeline` (loads spaCy model once)
  3. Connect to Supabase via `psycopg2.connect()`
  4. Query: `SELECT id, title, description FROM events WHERE location IS NULL LIMIT 500`
  5. For each row: combine title + description, run pipeline, extract coordinates
  6. `UPDATE events SET location = ST_SetSRID(ST_MakePoint(%s, %s), 4326), updated_at = now() WHERE id = %s`
  7. Commit batch, close, exit
- Keep `_build_response` and `_build_all_entities` functions if still useful (for logging/metrics)
- Remove FastAPI-specific: `FastAPI`, `Depends`, `get_pipeline`, `@app.get`, `@app.post`, `uvicorn`

#### `backend/location-extraction-service/src/schemas.py` — KEEP for reference (or DELETE if not imported elsewhere)
- Check if any other module imports from `schemas.py`
- If only used by `app.py`, can be deleted

#### `backend/location-extraction-service/Dockerfile` — MODIFY
- CMD changes from uvicorn server to batch script:
  ```
  CMD [".venv/bin/python", "-c", "from src.app import main; main()"]
  ```
  Or add a `__main__.py` entry point
- Add `DATABASE_URL` to build-time docs (not baked in, passed at runtime)

#### `backend/location-extraction-service/tests/integration/test_api.py` — REWRITE or DELETE
- Current tests test FastAPI endpoints via httpx ASGI client
- Replace with tests for the batch job logic:
  - Test that `main()` queries DB, processes articles, updates locations
  - Mock psycopg2 connection and pipeline
  - Test with mock DB rows

#### `backend/location-extraction-service/tests/conftest.py` — CHECK
- May need updates if it references FastAPI app or httpx fixtures

#### Other tests (test_pipeline_integration.py, test_extractor.py, etc.) — KEEP mostly as-is
- Pipeline logic tests should still work since pipeline modules stay the same

---

### Step 3: Tile API → Cloud Run Service (minimal changes)

**Goal:** Deploy as Cloud Run Service with scale-to-zero. The code is already appropriate for this.

#### `backend/api/Dockerfile` — KEEP (minor tweak)
- Already listens on PORT env var (Cloud Run provides this)
- Already uses `--experimental-strip-types`
- Ensure it doesn't hardcode `EXPOSE 3002` — Cloud Run ignores EXPOSE but keep for clarity

#### `backend/api/src/index.ts` — CHECK (no change needed)
- `process.env.PORT` is already used (line 14)
- `process.env.CORS_ORIGIN` is already used (line 7)
- `process.env.DATABASE_URL` is already used by `db/client.ts`

#### Cloud Run YAML config — NEW
- Create `backend/api/cloud-run-service.yaml`:
  ```yaml
  apiVersion: serve.knative.dev/v1
  kind: Service
  metadata:
    name: tile-api
  spec:
    template:
      spec:
        containers:
          - image: REGION-docker.pkg.dev/PROJECT/living-map/tile-api:latest
            ports:
              - containerPort: 3002
            env:
              - name: DATABASE_URL
                valueFrom:
                  secretKeyRef:
                    name: supabase-url
                    key: url
              - name: CORS_ORIGIN
                value: "https://<user>.github.io"
        minScale: 0  # scale to zero
        maxScale: 1
        containerConcurrency: 80
        startupCpuBoost: true  # faster cold start
  ```

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
- Create `VITE_API_URL=https://tile-api-xxxxx-uc.a.run.app` (set after tile API deployed)

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
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/setup-gcloud@v2
      - run: gcloud auth configure-docker ${{ secrets.GCP_REGION }}-docker.pkg.dev
      - name: Build & push tile-api
        run: |
          docker build -t ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/living-map/tile-api:${{ github.sha }} -t ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/living-map/tile-api:latest backend/api
          docker push --all-tags ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/living-map/tile-api
      - name: Build & push ingestion-job
        run: |
          docker build -t ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/living-map/ingestion-job:${{ github.sha }} -t ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/living-map/ingestion-job:latest backend/ingestion-worker
          docker push --all-tags ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/living-map/ingestion-job
      - name: Build & push les-job
        run: |
          docker build -t ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/living-map/les-job:${{ github.sha }} -t ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/living-map/les-job:latest backend/location-extraction-service
          docker push --all-tags ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/living-map/les-job

  deploy-tile-api:
    needs: [build-and-push]
    runs-on: ubuntu-latest
    outputs:
      url: ${{ steps.deploy.outputs.url }}
    steps:
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/setup-gcloud@v2
      - id: deploy
        run: |
          gcloud run deploy tile-api \
            --image=${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/living-map/tile-api:${{ github.sha }} \
            --region=${{ secrets.GCP_REGION }} \
            --allow-unauthenticated \
            --cpu-boost \
            --min-instances=0 \
            --max-instances=1 \
            --concurrency=80 \
            --set-env-vars=DATABASE_URL=${{ secrets.SUPABASE_DATABASE_URL }},CORS_ORIGIN=${{ secrets.CORS_ORIGIN }}
          echo "url=$(gcloud run services describe tile-api --region=${{ secrets.GCP_REGION }} --format='value(status.url)')" >> $GITHUB_OUTPUT

  deploy-ingestion-job:
    needs: [build-and-push]
    runs-on: ubuntu-latest
    steps:
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/setup-gcloud@v2
      - run: |
          gcloud run jobs deploy ingestion-job \
            --image=${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/living-map/ingestion-job:${{ github.sha }} \
            --region=${{ secrets.GCP_REGION }} \
            --set-env-vars=DATABASE_URL=${{ secrets.SUPABASE_DATABASE_URL }}

  deploy-les-job:
    needs: [build-and-push]
    runs-on: ubuntu-latest
    steps:
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/setup-gcloud@v2
      - run: |
          gcloud run jobs deploy les-job \
            --image=${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/living-map/les-job:${{ github.sha }} \
            --region=${{ secrets.GCP_REGION }} \
            --memory=2Gi \
            --set-env-vars=DATABASE_URL=${{ secrets.SUPABASE_DATABASE_URL }}

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

  setup-scheduler:
    needs: [deploy-ingestion-job, deploy-les-job]
    runs-on: ubuntu-latest
    steps:
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/setup-gcloud@v2
      - name: Get service account email
        id: sa
        run: echo "email=$(gcloud iam service-accounts list --filter='displayName:"Compute Engine default service account"' --format='value(email)')" >> $GITHUB_OUTPUT
      - name: Create or update ingestion trigger
        run: |
          gcloud scheduler jobs create http ingestion-trigger \
            --location=${{ secrets.GCP_REGION }} \
            --schedule="0 6 * * *" \
            --uri="https://${{ secrets.GCP_REGION }}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${{ secrets.GCP_PROJECT_ID }}/jobs/ingestion-job:run" \
            --http-method=POST \
            --oauth-service-account-email=${{ steps.sa.outputs.email }} \
            --attempt-deadline=600s 2>/dev/null || \
          gcloud scheduler jobs update http ingestion-trigger \
            --location=${{ secrets.GCP_REGION }} \
            --schedule="0 6 * * *" \
            --uri="https://${{ secrets.GCP_REGION }}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${{ secrets.GCP_PROJECT_ID }}/jobs/ingestion-job:run" \
            --http-method=POST \
            --oauth-service-account-email=${{ steps.sa.outputs.email }} \
            --attempt-deadline=600s
      - name: Create or update LES trigger
        run: |
          gcloud scheduler jobs create http les-trigger \
            --location=${{ secrets.GCP_REGION }} \
            --schedule="0 7 * * *" \
            --uri="https://${{ secrets.GCP_REGION }}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${{ secrets.GCP_PROJECT_ID }}/jobs/les-job:run" \
            --http-method=POST \
            --oauth-service-account-email=${{ steps.sa.outputs.email }} \
            --attempt-deadline=600s 2>/dev/null || \
          gcloud scheduler jobs update http les-trigger \
            --location=${{ secrets.GCP_REGION }} \
            --schedule="0 7 * * *" \
            --uri="https://${{ secrets.GCP_REGION }}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${{ secrets.GCP_PROJECT_ID }}/jobs/les-job:run" \
            --http-method=POST \
            --oauth-service-account-email=${{ steps.sa.outputs.email }} \
            --attempt-deadline=600s
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

#### `docs/architecture/deployment.md` — UPDATE
- Replace the production architecture section with the new Cloud Run + Supabase + GitHub Pages architecture
- Keep the local development section as-is (Docker Compose still works for local dev)
- Add section on the new CI/CD pipeline (GitHub Actions)
- Add section on Cloud Run configuration (memory, CPU, startup boost)
- Add section on Supabase connection with SSL
- Add section on Supabase idle-pause mitigation (daily job resets 7-day timer)
- Mark the old Oracle ARM + Coolify section as superseded
- Update the mermaid diagram:

  ```
  GitHub → push → GitHub Actions
    ├─ Build & push containers → Artifact Registry
    ├─ Deploy Cloud Run Service → tile-api (scale-to-zero)
    ├─ Deploy Cloud Run Jobs → ingestion-job, les-job (one-shot)
    └─ Deploy static site → GitHub Pages

  Cloud Scheduler (daily):
    ├─ 06:00 UTC → ingestion-job → fetch RSS → INSERT Supabase
    └─ 07:00 UTC → les-job → SELECT unprocessed → NER → UPDATE locations

  User browser → GitHub Pages (CDN) → tile-api (Cloud Run) → Supabase PostGIS
  ```

- Mark the OCI Terraform as superseded by ADR-021

---

## Gotchas & Warnings

1. **Supabase SSL:** Connection string needs `?sslmode=require` — verify `pg` and `psycopg2` handle this
2. **Supabase PostGIS version:** It may differ from local (3.3.7 vs 3.4). Check `SELECT PostGIS_Version();` after project creation
3. **node-pg-migrate on Supabase:** `createExtension("postgis")` may fail if already installed — `ifNotExists: true` is already set
4. **CORS:** Tile API must include GitHub Pages domain in `CORS_ORIGIN`. Current code uses a single origin — may need `CORS_ORIGIN` to allow multiple origins if both localhost and production are needed
5. **LES memory:** `en_core_web_trf` needs ~2 GB. Set `--memory=2Gi` on the les-job
6. **Cloud Run Job timeout:** Default is 10 minutes — ingestion ~3 min, LES ~5 min, fine
7. **Frontend base path:** If deploying to `https://<user>.github.io/<repo>/`, set `base: '/<repo>/'` in `vite.config.ts`
8. **CI ordering:** `deploy-frontend` needs tile API URL from `deploy-tile-api` — passed as job output
9. **Database URL in CI:** Stored as a GitHub secret. Both jobs require it at deploy time
10. **Mock feed:** Not affected — only used in tests and local dev
