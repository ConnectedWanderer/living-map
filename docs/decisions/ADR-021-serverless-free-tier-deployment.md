# ADR-021: Serverless Free-Tier Deployment on Google Cloud Run + Supabase

## Status

Proposed

## Date

2026-06-13

## Context

The original deployment strategy (ADR-020's context, documented in `docs/architecture/deployment.md`) relies on an **Oracle Cloud Always-Free ARM instance** (`VM.Standard.A1.Flex`: 4 OCPUs, 24 GB RAM) managed via **Coolify** with Docker Compose. In practice, Oracle ARM instances are never available — the `Out of capacity` error is persistent across regions. The always-free AMD instances (1 OCPU, 1 GB RAM) are insufficient for the full stack, especially the location extraction service with spaCy models.

The system must run at **$0/month** using only **always-free** tiers (no temporary credits or promotional offers). It must also support upgrading to the `en_core_web_trf` (transformer) spaCy model (~500 MB on disk) to improve NER accuracy.

### Current Architecture

```
Oracle VM.Standard.A1.Flex (unavailable)
  └─ Coolify → Docker Compose
       ├─ Frontend (nginx)
       ├─ API (Node.js, tile serving)
       ├─ Ingestion Worker (Node.js, node-cron)
       ├─ Location Extraction (Python + FastAPI + spaCy)
       └─ PostgreSQL + PostGIS
```

### Requirements

| Requirement | Detail |
|---|---|
| Cost | $0/month (always-free, no temporary offers) |
| spaCy model | Must support `en_core_web_trf` (~500 MB, 2 GB RAM needed) |
| Execution | Daily scheduled batch processing |
| Frontend | Static site, globally fast |
| API / Tiles | Dedicated tile server, always reachable |
| Database | Spatial queries (PostGIS or equivalent MVT-capable) |
| Full-stack | Must cover frontend → API → ingestion → NLP → DB |

### Considerations

1. **500 MB model constraint**: The transformer model needs ~2 GB memory at runtime. Many free-tier platforms cap at 512 MB or 1 GB.
2. **Scheduled vs always-on**: The ingestion pipeline and NLP processing only need to run once daily. A persistent VM is wasteful.
3. **Database spatial support**: Vector tiles require spatial queries/indexing. PostGIS is the established choice but must be available on free-tier managed Postgres.
4. **Temporary offers**: Credit-based free tiers (e.g., Modal's $30/mo, AWS free trial) are excluded — the solution must work indefinitely without payment.

## Options Considered

### Compute Platforms

| Platform | Free Tier | Max Memory | trf Model | Notes |
|---|---|---|---|---|
| **Google Cloud Run** ⭐ | 2M req/mo, 360K GB-s, 180K vCPU-s, 1 GB egress | 8 GB | ✅ Yes | Serverless containers, startup CPU boost, Cloud Scheduler |
| AWS Lambda | 1M req/mo, 400K GB-s | 10 GB (container) | ⚠️ Tight | Cold start slower, no CPU boost for init |
| Koyeb | 1 x 512 MB / 1 vCPU | 512 MB | ❌ No | Pivoting to Mistral Compute, free tier insufficient |
| Fly.io | No free tier for new orgs | — | ❌ No | Removed free tier 2025 |
| Render | 512 MB / 0.1 CPU | 512 MB | ❌ No | Insufficient RAM |
| Cloudflare Workers | 100k req/day | 128 MB | ❌ No | No Python spaCy support |
| Railway | $5 credit (temporary) | 512 MB | ❌ No | Credit-based, insufficient |
| Modal | $30/mo free credits | GPU | ⚠️ Credit | Temporary credits, not always-free |

### Database Platforms

| Platform | Free Tier | PostGIS | 7d Pause | Notes |
|---|---|---|---|---|
| **Supabase** ⭐ | 500 MB DB, 5 GB bandwidth, 2 projects | ✅ Pre-installed | ✅ Yes | Best PostGIS integration, auto-pauses after 7d idle |
| **Neon** | 0.5 GB/project (100 projects), 100 CU-hrs/mo | ✅ Extension | ❌ No | Scale-to-zero compute, storage persists |
| CockroachDB | 10 GB storage | ⚠️ Limited | ❌ No | No PostGIS, basic spatial only |
| PlanetScale | 1 GB storage | ❌ No | ❌ No | MySQL-only, no spatial |
| Turso | 9 GB storage, 1 GB per DB | ❌ No | ❌ No | SQLite-based, no PostGIS |

### Execution Models

| Option | Description | Cold Start Mitigation |
|---|---|---|
| **A: LES as Cloud Run Job** ⭐ | Both ingestion and LES run as scheduled jobs. LES loads model once per run, batch-processes all articles, exits. | Perfect — one cold start per daily run |
| B: LES as Cloud Run Service | HTTP server, called per-article by ingestion job | Needs batch endpoint to avoid N cold starts per run |
| C: Mono-job | Single container with Node + Python + spaCy | Eliminates inter-service calls but image is huge |

## Decision

### Chosen Architecture

```
GitHub Pages (free, global CDN)
  └─ Frontend (static Vite build)

Google Cloud Platform (always free tier)
  ├─ Cloud Scheduler: triggers 2 cron jobs daily
  │
  ├─ Cloud Run Job: "ingestion-job"
  │   1. Fetch RSS feeds → normalize articles
  │   2. INSERT into Supabase events table
  │   3. Exit → scale to zero
  │
  ├─ Cloud Run Job: "les-job"
  │   1. SELECT unprocessed articles from Supabase
  │   2. Load en_core_web_trf (~500 MB, once per run)
  │   3. Batch NER + geocoding → update locations
  │   4. Exit → scale to zero
  │
  └─ Cloud Run Service: "tile-api"
       ├─ Express server serving MVT tiles
       ├─ min_instances = 0 (scale-to-zero on idle)
       └─ Queries Supabase PostGIS for tile generation

Supabase (free: 500 MB, PostGIS 3.3.7)
  ├─ events table with GEOMETRY(Point, 4326)
  └─ sources table with cron schedules
```

### Component Breakdown

| Component | Platform | Type | Cost | Rationale |
|---|---|---|---|---|
| Frontend | GitHub Pages | Static site | $0 | Global CDN, automatic HTTPS, simple git-push deploy |
| Tile API | Cloud Run Service | HTTP, scale-to-zero | $0 | Lightweight Express server, stays within 360K GB-s/mo |
| Ingestion | Cloud Run Job | Daily cron | $0 | One-shot container, ~3 min run, well within free tier |
| LES | Cloud Run Job | Daily cron | $0 | Batch processing with single model load per run |
| Scheduling | Cloud Scheduler | 2 cron jobs | $0 | 3 free jobs per project |
| Database | Supabase | PostGIS 500 MB | $0 | Pre-installed PostGIS, PostgREST, in-browser SQL editor |

### Estimated Free-Tier Usage

| Resource | Daily Need | Monthly Total | Free Limit | Headroom |
|---|---|---|---|---|
| Cloud Run GB-seconds (LES, 2 GB x 5 min) | 600 | 18,000 | 360,000 | 95% free |
| Cloud Run GB-seconds (Ingestion, 512 MB x 3 min) | 90 | 2,700 | 360,000 | 99% free |
| Cloud Run GB-seconds (Tile API, 256 MB x 2 min avg) | 30 | 900 | 360,000 | 99.7% free |
| Cloud Run vCPU-seconds (total) | ~400 | 12,000 | 180,000 | 93% free |
| Cloud Run requests | ~50 | 1,500 | 2,000,000 | 99.9% free |
| Cloud Scheduler jobs | 2 | 60 | 3 free jobs | OK |
| Supabase database storage | — | < 500 MB | 500 MB | Must monitor growth |
| Supabase bandwidth | — | < 1 GB | 5 GB/month | OK |

### Batch LES Job Design

The existing FastAPI server pattern is replaced by a script entry point:

```
1. Start → load spaCy model + geonamescache data
2. Query "unprocessed" articles from Supabase (WHERE location IS NULL)
3. For each article in batch:
   a. Run NER pipeline (spaCy)
   b. Run geocoding (geonamescache)
   c. Run disambiguation
   d. Collect result
4. UPDATE events SET location = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
   WHERE source = $1 AND source_id = $2
5. Exit
```

The `en_core_web_trf` model loads once at cold start (~20-40s with Cloud Run startup CPU boost), then stays hot for the batch. No HTTP server, no per-request overhead.

### Dependency Decoupling

By making both jobs independent (scheduled separately, communicating via the database), we gain:

- **LES can be disabled** without breaking ingestion (articles just won't have locations)
- **Each can have its own schedule** (LES might run less frequently if article volume is low)
- **Independent failure domains** — if LES OOMs, ingestion still captures articles
- **Scalable independently** — each job can increase memory/CPU without affecting the other

### Supabase Idle-Pause Mitigation

Supabase free-tier projects auto-pause after 7 days of inactivity. To prevent this for a portfolio app:

1. The daily scheduled jobs generate database activity, naturally resetting the timer
2. If the tile API has no visitors for 7+ days and ingestion is also dormant, the project pauses
3. Recovery: click "Restore" in Supabase dashboard (data is preserved)
4. Long-term: an external uptime monitor (e.g., Uptime Kuma, cron-job.org free) pinging `/rest/v1/rpc/health` every 6h keeps it active

For a demo/portfolio app, the 7-day pause is acceptable. If it becomes a blocker, upgrade to Supabase Pro ($25/mo) which removes the pause.

## Consequences

### Positive

1. **Zero cost** — Entire stack runs at $0/month indefinitely
2. **No capacity contention** — No reliance on Oracle's scarce ARM instances
3. **Right-sized compute** — Jobs use memory only during execution, not 24/7
4. **Independent scaling** — Each Cloud Run job/service can be configured independently
5. **Simpler operational model** — No VM to patch, no Docker daemon to monitor, no Coolify to maintain
6. **Global frontend** — GitHub Pages CDN serves static assets fast everywhere
7. **Upgrade path** — `en_core_web_trf` (500 MB, ~2 GB RAM) fits within Cloud Run's limits; just change the model env var and increase job memory

### Negative

1. **No always-warm tile API** — First tile request after idle incurs a 1-3s cold start. Acceptable for portfolio traffic.
2. **Supabase 7-day pause** — If both jobs and visitors are absent for 7 days, DB pauses. Recovery is manual but data is safe.
3. **500 MB DB limit** — Event storage is capped at 500 MB. At ~1 KB/article this holds ~500K articles. Monitor and purge old events.
4. **No real-time ingestion** — Jobs run on a fixed schedule. Articles fetched between runs are processed on the next cycle.
5. **Node.js + Python split** — Two runtimes, two container images, two build pipelines. Dev setup already handles this.
6. **Cloud Scheduler dependency** — If Cloud Scheduler is down, no daily processing occurs. Low risk (Google's SLA).
7. **Network latency** — Cloud Run to Supabase goes over the public internet (not a VPC peering). Adds ~10-30ms per query. Acceptable for batch jobs.

### Migration Path

1. **Deploy Supabase** — Create project, enable PostGIS, run migrations
2. **Deploy Cloud Run tile API** — Build container, push to Artifact Registry, deploy with `gcloud run deploy`
3. **Deploy Cloud Run jobs** — Build ingestion and LES containers, create jobs, add Cloud Scheduler triggers
4. **Configure GitHub Pages** — Build frontend, push to `gh-pages` branch, configure custom domain
5. **Update environment** — Point all services at Supabase connection string
6. **Decommission Oracle VM** — Once the new stack is verified, tear down the old VM and Coolify

## Related Documentation

- [Deployment Architecture](../../docs/architecture/deployment.md) — superseded by this ADR for compute decisions
- [ADR-010: PostgreSQL + PostGIS for Event Persistence](ADR-010-postgresql-postgis-for-persistence.md) — database schema and PostGIS decisions
- [ADR-011: Separate Ingestion and Serving Services](ADR-011-separate-ingestion-and-serving-services.md) — service boundary rationale
- [ADR-001: Location Extraction Approach](ADR-001-location-extraction-approach.md) — spaCy NER approach
- [Google Cloud Run Pricing](https://cloud.google.com/run/pricing) — always free tier details
- [Supabase Free Tier](https://supabase.com/pricing) — database limits
