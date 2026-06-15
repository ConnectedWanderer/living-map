# ADR-022: Serverless Free-Tier Deployment on Scaleway + Supabase

## Status

Proposed

## Date

2026-06-15

## Context

ADR-021 proposed deploying on **Google Cloud Run + Cloud Scheduler** with Supabase for the database and GitHub Pages for the frontend. The architecture was sound — one-shot Cloud Run Jobs for ingestion and LES, a scale-to-zero Cloud Run Service for the tile API — but setting up GCP requires a **10€ refundable prepayment** to create a billing account. While this prepayment is refundable, the user prefers a provider that does not require upfront payment at all.

The system requirements remain unchanged:

| Requirement | Detail |
|---|---|
| Cost | $0/month (always-free, no temporary offers) |
| spaCy model | Must support `en_core_web_trf` (~500 MB, 2 GB RAM needed) |
| Execution | Daily scheduled batch processing |
| Frontend | Static site, globally fast |
| API / Tiles | Dedicated tile server, always reachable |
| Database | Spatial queries (PostGIS or equivalent MVT-capable) |
| Full-stack | Must cover frontend → API → ingestion → NLP → DB |

The compute requirements stay the same — only the cloud provider changes. Supabase remains the database (free PostGIS, no upfront payment needed), and GitHub Pages remains the frontend host.

## Options Considered

### Compute Platforms

| Platform | Free Tier | Max Memory | trf Model | Setup Friction | Notes |
|---|---|---|---|---|---|
| **Scaleway Serverless** ⭐ | 400K GB-s, 200K vCPU-s, shared across containers+jobs+functions | 4 GB | ✅ Yes | Credit card (no prepayment) | European provider, container-native (Docker images), CRON triggers built-in |
| AWS Lambda | 1M req/mo, 400K GB-s | 10 GB (container) | ✅ Yes | Credit card (no prepayment) | Needs Lambda handler wrapper, EventBridge Scheduler 14M free invocations |
| Google Cloud Run | 2M req/mo, 360K GB-s, 180K vCPU-s | 8 GB | ✅ Yes | 10€ refundable prepayment | Original ADR-021 choice, rejected due to upfront payment |
| Koyeb | Free DB only (no free compute) | 512 MB | ❌ No | — | Free compute tier removed |
| Render | 512 MB / 0.1 CPU | 512 MB | ❌ No | — | Insufficient RAM for trf model |
| Fly.io | No free tier for new orgs | — | ❌ No | — | Removed free tier 2025 |
| Cloudflare Workers | 100K req/day | 128 MB | ❌ No | — | No Python, no containers |

### Database

| Platform | Free Tier | PostGIS | Setup Friction |
|---|---|---|---|
| **Supabase** ⭐ (unchanged) | 500 MB DB, 5 GB bandwidth | ✅ Pre-installed | Email signup, no payment needed |

## Decision

### Chosen Architecture

```
GitHub Pages (free, global CDN)
  └─ Frontend (static Vite build)

Scaleway (always free tier, shared across serverless products)
  ├─ Serverless Container: "tile-api" (scale-to-zero)
  │   └─ Express server serving MVT tiles, queries Supabase PostGIS
  │
  ├─ Serverless Job: "ingestion-job" (cron: 06:00 UTC)
  │   1. Fetch RSS feeds → normalize articles
  │   2. INSERT into Supabase events table
  │   3. Exit → scale to zero
  │
  └─ Serverless Job: "les-job" (cron: 07:00 UTC)
      1. SELECT unprocessed articles from Supabase
      2. Load en_core_web_trf (~500 MB, once per run)
      3. Batch NER + geocoding → update locations
      4. Exit → scale to zero

Supabase (free: 500 MB, PostGIS)
  └─ events table with GEOMETRY(Point, 4326)
  └─ sources table with cron schedules
```

### Component Breakdown

| Component | Platform | Type | Cost | Rationale |
|---|---|---|---|---|
| Frontend | GitHub Pages | Static site | $0 | Global CDN, automatic HTTPS, simple git-push deploy |
| Tile API | Scaleway Serverless Container | HTTP, scale-to-zero | $0 | Container-native, Docker image deploys as-is, no code changes |
| Ingestion | Scaleway Serverless Job | Daily cron | $0 | One-shot container, ~3 min run, well within free tier |
| LES | Scaleway Serverless Job | Daily cron | $0 | Batch processing with single model load per run, up to 4 GB RAM |
| Scheduling | Scaleway Container CRON triggers | 2 cron jobs | $0 | Native CRON triggers on containers/jobs |
| Database | Supabase | PostGIS 500 MB | $0 | Pre-installed PostGIS, no payment needed to start |

### Why Scaleway Over AWS Lambda

Both are viable, but Scaleway is the **path of least resistance** given the work already done:

1. **Container-native** — The same Docker images built for Cloud Run deploy to Scaleway Serverless Containers/Jobs with zero code changes
2. **Same execution model** — Jobs run as containers with `CMD`, not as Lambda handlers. The ingestion and LES code as refactored per ADR-021 works as-is
3. **CRON triggers** — Built-in, no extra service needed
4. **No adapter code** — No need to wrap Express with `@vendia/serverless-express` or wrap `main()` as a Lambda handler

### Estimated Free-Tier Usage

Scaleway's free tier is pooled across all serverless products (containers, functions, jobs):

| Resource | Monthly Limit | Estimated Usage | Headroom |
|---|---|---|---|
| GB-seconds | 400,000 | ~21,700 (LES 18K + ingestion 2.7K + tile API ~1K) | 94.6% free |
| vCPU-seconds | 200,000 | ~20,000 (LES at 2 vCPU + ingestion + tile API) | 90% free |

### Supabase Idle-Pause Mitigation

Same as ADR-021. Daily jobs naturally reset the 7-day timer. If all activity stops for 7+ days, click "Restore" in the Supabase dashboard.

## Consequences

### Positive

1. **Zero upfront payment** — Scaleway requires a credit card but no prepayment/refundable deposit
2. **No code changes from ADR-021** — The ingestion-job, les-job, and tile API Docker images deploy as-is
3. **Same $0/month cost model** — The free tier is slightly more generous than GCP's (400K vs 360K GB-s)
4. **European provider** — Data stays in EU (Paris, Amsterdam, Warsaw regions) for GDPR compliance
5. **No capacity contention** — Unlike Oracle ARM, no resource scarcity
6. **Right-sized compute** — Jobs use memory only during execution, not 24/7
7. **Simpler operational model** — No VM to patch, no Docker daemon to monitor

### Negative

1. **No startup CPU boost** — Cloud Run has explicit CPU boost during cold start; Scaleway may cold-start slower for the LES model load (acceptable — LES runs once daily)
2. **Cold starts on tile API** — First request after idle may take 1-3s (same as Cloud Run scale-to-zero)
3. **Scaleway ecosystem is smaller** — Fewer regions, smaller community, less documentation than GCP/AWS
4. **Free tier pooled** — The 400K GB-s / 200K vCPU-s are shared across all serverless products in the account (still ample headroom)
5. **Price increase (June 2026)** — Scaleway raised serverless pricing effective June 1, 2026. The free tier limits remain unchanged for now.
6. **Supabase 7-day pause** — Same as ADR-021. If both jobs and visitors are absent for 7 days, DB pauses. Recovery is manual but data is safe.

### Migration Path from ADR-021

Since no code changes are needed (same Docker images), the migration is purely infrastructure/CI:

1. **Create Scaleway account** — No prepayment, credit card for verification
2. **Keep Supabase** — Already created per ADR-021 prerequisites
3. **Keep GitHub Pages** — Already configured per ADR-021
4. **Rewrite CI/CD** — Replace `gcloud` commands with `scw` CLI commands in `.github/workflows/deploy.yml`
5. **Replace GitHub secrets** — `SCW_ACCESS_KEY`/`SCW_SECRET_KEY` instead of `GCP_SA_KEY`/`GCP_PROJECT_ID`
6. **Deploy** — Push to `main`, GitHub Actions builds and deploys to Scaleway

## Related Documentation

- [ADR-021: Serverless Free-Tier Deployment on Google Cloud Run + Supabase](ADR-021-serverless-free-tier-deployment.md) — superseded by this ADR for compute decisions
- [Deployment Architecture](../architecture/deployment.md) — updated for Scaleway
- [CONTEXT.md](../../CONTEXT.md) — step-by-step implementation plan
- [Scaleway Serverless Pricing](https://www.scaleway.com/en/pricing/serverless/) — free tier details
- [Scaleway Serverless Containers Documentation](https://www.scaleway.com/en/docs/serverless-containers/)
- [Scaleway Serverless Jobs Documentation](https://www.scaleway.com/en/docs/serverless-jobs/)
