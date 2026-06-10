# Living Map - Deployment & Hosting Architecture

## Overview

This document describes the deployment and hosting architecture for the Living Map application. It covers the current local development setup, the production target infrastructure, container strategy, and operational runbook.

## Current State: Local Development

All services run via Docker Compose on a single host. The compose file at `backend/docker-compose.yml` orchestrates:

| Service               | Image/Build                                              | Port | Dependencies        |
| --------------------- | -------------------------------------------------------- | ---- | ------------------- |
| `postgres`            | `postgis/postgis:16-3.4`                                 | 5432 | —                   |
| `migrate`             | `node:22-alpine` (ephemeral)                             | —    | postgres (healthy)  |
| `ingestion-worker`    | `./ingestion-worker/Dockerfile`                          | 3000 | migrate (completed) |
| `api`                 | `./api/Dockerfile`                                       | 3002 | migrate (completed) |
| `location-extraction` | `./location-extraction-service/Dockerfile` (via include) | 8000 | —                   |
| `frontend`            | `../frontend/Dockerfile`                                 | 8080 | api                 |

`mock-feed` runs outside compose — started manually for testing or via Testcontainers in integration tests.

The frontend nginx (`frontend/nginx.conf`) proxies `/tiles/` requests to the api service over the Docker internal network.

## Target Infrastructure

| Layer             | Choice                                              | Rationale                                                 |
| ----------------- | --------------------------------------------------- | --------------------------------------------------------- |
| Compute           | Oracle Cloud Always Free (VM.Standard.A1.Flex)      | 4 OCPUs, 24 GB RAM, 200 GB storage — $0/mo                |
| Platform          | Coolify (self-hosted)                               | Git-push deploys, auto SSL, web UI, Docker Compose native |
| Container Runtime | Docker Engine + Docker Compose                      | Consistent with local dev, well-supported on ARM          |
| Reverse Proxy     | Traefik (managed by Coolify)                        | Auto Let's Encrypt SSL, docker-aware routing              |
| Domain            | User-provided domain (e.g., living-map.example.com) | Subdomain per service via Coolify                         |

### Why Oracle ARM + Coolify

The Oracle Always Free tier is the only cloud provider offering sufficient free compute (24 GB RAM) to run the full stack — including spaCy model weights and PostGIS — without artificial constraints. Coolify adds a Heroku-like deployment layer: connect a GitHub repo, push, and Coolify builds the Docker image, deploys, and provisions SSL.

The trade-off is ARM CPU architecture. Most images used (Node, Python, PostgreSQL, nginx) have native ARM64 variants, but occasional x86-only dependencies may require multi-arch builds or alternatives.

## Production Architecture

```mermaid
flowchart TD
    subgraph Internet["Internet"]
        User[User Browser]
        GitHub
    end

    subgraph Coolify["Coolify (on Oracle ARM VM)"]
        subgraph Proxy["Traefik Reverse Proxy"]
            TLS[Let's Encrypt SSL]
        end

        subgraph Services["Application Services"]
            FE[Frontend<br/>nginx:alpine]
            API[Serving API<br/>Node.js + Express]
            IW[Ingestion Worker<br/>Node.js + cron]
            LE[Location Extraction<br/>Python + FastAPI]
        end

        DB[(PostgreSQL<br/>+ PostGIS)]
    end

    User -->|HTTPS| TLS
    TLS -->|living-map.example.com| FE
    TLS -->|api.example.com| API

    FE -->|proxy /tiles/| API
    API -->|SELECT| DB
    IW -->|INSERT| DB
    IW -->|POST /api/extract-location| LE
    IW -->|poll| RSS[External RSS Feeds]

    GitHub -->|git push| Coolify
```

### Service-to-domain mapping (Coolify)

| Service             | Coolify Resource       | Domain                             |
| ------------------- | ---------------------- | ---------------------------------- |
| Frontend            | Docker Compose service | `living-map.example.com` (public)  |
| API                 | Docker Compose service | Internal (Coolify private network) |
| Ingestion Worker    | Docker Compose service | Internal (no public port)          |
| Location Extraction | Docker Compose service | Internal (Coolify private network) |
| PostgreSQL          | Docker Compose service | Internal (no public port)          |

The frontend is the only service exposed publicly. The API, worker, and location extraction communicate over Coolify's internal Docker network.

## Container Strategy

| Service             | Base Image                                           | Build Context               | Notes                                         |
| ------------------- | ---------------------------------------------------- | --------------------------- | --------------------------------------------- |
| Frontend            | `node:22-alpine` (build) / `nginx:alpine` (serve)    | `frontend/`                 | Multi-stage: Vite build, then copy to nginx   |
| API                 | `node:22-alpine`                                     | `backend/api/`              | Compiles TS with `--experimental-strip-types` |
| Ingestion Worker    | `node:22-alpine`                                     | `backend/ingestion-worker/` | TypeScript via `--experimental-strip-types`   |
| Location Extraction | Dockerfile in `backend/location-extraction-service/` | Python 3.14 + spaCy models  | Largest image (~500 MB with models)           |
| PostgreSQL          | `postgis/postgis:16-3.4`                             | —                           | Official image, no custom build               |

### ARM Compatibility

| Image                    | ARM64 Support | Notes                      |
| ------------------------ | ------------- | -------------------------- |
| `node:22-alpine`         | ✅ Native     | Works out of the box       |
| `python:3.14-slim`       | ✅ Native     | Works out of the box       |
| `nginx:alpine`           | ✅ Native     | Works out of the box       |
| `postgis/postgis:16-3.4` | ✅ Native     | ARM64 image published      |
| spaCy models             | ✅ Native     | Installable on ARM via pip |

No ARM-specific issues expected for the current stack. If an x86-only Python dependency arises, use `--platform=linux/arm64` or build from source.

## Environment Configuration

Coolify manages environment variables per service via its UI. The required variables:

### Frontend

- `VITE_API_URL` (not used directly — uses nginx proxy `/tiles/ → api:3002`)

### API

- `DATABASE_URL` — `postgres://user:password@host:5432/livingmap`
- `CORS_ORIGIN` — set to frontend domain

### Ingestion Worker

- `DATABASE_URL` — same as API
- `LOCATION_EXTRACTION_URL` — `http://location-extraction:8000`
- `PORT` — `3000`
- `LOG_LEVEL` — `info`

### Location Extraction

- `HOST` — `0.0.0.0`
- `PORT` — `8000`
- `LOG_LEVEL` — `INFO`
- `SPACY_EN_MODEL` — `en_core_web_sm`
- `SPACY_FR_MODEL` — `fr_core_news_sm`

## Deployment Workflow

1. Develop locally, commit, push to GitHub
2. Coolify detects push to linked branch
3. Coolify pulls repo, builds Docker images from each service's Dockerfile
4. Coolify deploys containers, runs health checks
5. Traefik auto-provisions/renews Let's Encrypt certificates
6. Rolling restart — no downtime for frontend

No manual SSH or `docker compose up` needed after initial Coolify setup.

## Database & Backup

**Database**: PostgreSQL with PostGIS runs as a Docker container managed by Coolify. Data lives on a Coolify persistent volume mapped to the host's attached block storage volume.

**Backup strategy**: Coolify supports scheduled S3-compatible backups (Cloudflare R2, AWS S3, etc.). For the free-tier setup:

1. **Application data**: Events in PostGIS have no hard state beyond what external RSS feeds produce. Losing DB means re-ingesting from sources.
2. **Recommended**: Configure Coolify weekly backups to Cloudflare R2 (free tier: 10 GB storage, no egress cost).
3. **Cold backup**: `pg_dump` via cron script on the host.

## Monitoring

| Capability        | Tool               | Notes                              |
| ----------------- | ------------------ | ---------------------------------- |
| Container logs    | Coolify dashboard  | Built-in log viewer per service    |
| Container metrics | Coolify Sentinel   | CPU, RAM per container             |
| Service health    | Docker HEALTHCHECK | Defined in each Dockerfile/compose |
| Host monitoring   | Coolify dashboard  | Disk usage, uptime, load           |

No external monitoring service required at this scale. Coolify's built-in dashboards are sufficient for a portfolio/demo app.

## Cost Breakdown

| Resource              | Cost         | Notes                                                   |
| --------------------- | ------------ | ------------------------------------------------------- |
| Oracle Cloud ARM VM   | $0/mo        | 4 OCPUs, 24 GB RAM, 200 GB storage                      |
| Domain name           | $0–$12/yr    | Free subdomain via nip.io, or ~$12/yr for a real domain |
| Cloudflare (optional) | $0/mo        | DNS, optional CDN caching                               |
| S3 backups (optional) | $0/mo        | Cloudflare R2 free tier or Backblaze B2                 |
| **Total**             | **$0–$1/mo** | Domain registration is the only potential cost          |

## Key Design Decisions

| Decision          | Choice                        | Rationale                                              |
| ----------------- | ----------------------------- | ------------------------------------------------------ |
| Compute provider  | Oracle Cloud Always Free      | 24 GB RAM free, sufficient for full stack              |
| Platform layer    | Coolify                       | Git-push deploys, auto SSL, web UI — near-Heroku DX    |
| Frontend serving  | nginx container               | Production build, SPA routing, proxy to API            |
| Database location | Docker container on same host | Low latency, no cross-network costs, simple ops        |
| Public exposure   | Frontend only                 | API, worker, location-extraction are internal services |
| Backup target     | S3-compatible (optional)      | Coolify-native, cheap, off-server redundancy           |

## Constraints & Assumptions

- Oracle ARM instance stays active (Oracle may reclaim idle Always Free instances — mitigate by keeping traffic or setting a health-ping every hour)
- ARM compatibility holds for all dependencies (unlikely to break, but possible with niche Python packages)
- Single-node deployment (Coolify can scale to multi-server, but not needed at this scale)
- No CDN or edge caching — nginx serves directly; acceptable for portfolio/demo traffic
- No automated CI/CD pipeline — Coolify's git-push deploy is sufficient

## Runbook

### Initial Setup (one-time)

```bash
# 1. Provision Oracle Cloud ARM instance (VM.Standard.A1.Flex, Ubuntu 24.04)
# 2. SSH in, install Docker
sudo apt update && sudo apt install -y docker.io docker-compose-v2
# 3. Install Coolify
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash
# 4. Open ports in Oracle Cloud firewall (80, 443, 8000 for Coolify UI)
# 5. Access Coolify UI at http://<ip>:8000, configure admin account
# 6. Connect GitHub repo, configure domain, deploy
```

### Common Operations

| Task                 | Command                                                                 |
| -------------------- | ----------------------------------------------------------------------- |
| SSH into host        | `ssh ubuntu@<oracle-ip>`                                                |
| View Coolify logs    | `docker logs coolify -f`                                                |
| Restart all services | Via Coolify UI — Restart project                                        |
| Force rebuild        | Via Coolify UI — Redeploy with force rebuild                            |
| Manual DB backup     | `docker exec postgres pg_dump -U livingmap livingmap > backup.sql`      |
| Restore DB           | `cat backup.sql \| docker exec -i postgres psql -U livingmap livingmap` |
| Check disk usage     | `df -h` on host                                                         |

### Recovery

If the Oracle instance is reclaimed:

1. Provision a new ARM instance (same region or different)
2. Install Docker + Coolify
3. Connect the same GitHub repo
4. Re-deploy — Coolify rebuilds all images from source
5. Restore latest DB backup
6. Point DNS to new IP

Total downtime: ~30 minutes. The application is stateless on the frontend; only the database needs restoration.

## Future Considerations

- **CI/CD pipeline**: Add GitHub Actions to run tests on PR, then auto-deploy via Coolify webhook on merge to main
- **CDN caching**: Put Cloudflare CDN in front of the nginx container to reduce load and improve global latency
- **Managed database**: Migrate to Neon or Supabase for managed PostGIS with automated backups, branching, and higher durability
- **Multi-server**: Coolify supports adding additional VPS nodes for load balancing
- **Monitoring upgrade**: Add Uptime Kuma or Grafana for deeper observability
