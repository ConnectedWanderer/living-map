# Deployment Guide — Scaleway Serverless + Supabase + GitHub Pages

Manual one-time setup steps. Must be done before the CI/CD pipeline can work.

## 1. Create Supabase project

1. Go to https://supabase.com → New project → select region close to Scaleway (e.g., `fr-par`)
2. Note connection string: `postgresql://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres`
3. Enable PostGIS in the SQL editor: `CREATE EXTENSION IF NOT EXISTS postgis;`
4. Run the migration against Supabase:

```bash
DATABASE_URL="postgresql://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres" \
npx node-pg-migrate up --migration-file-language js --migration-dir backend/migrations
```

## 2. Create Scaleway account

1. Go to https://console.scaleway.com → Sign up (credit card for verification, no prepayment)
2. Create an IAM API key pair (Access Key + Secret Key) in IAM → API Keys
3. Create a Project (or use the default) and note the Project ID

## 3. Create Scaleway namespaces (via `scw` CLI)

```bash
sudo pacman -S scaleway-cli
scw init access-key=<ACCESS_KEY> secret-key=<SECRET_KEY> organization-id=<ORGANIZATION_ID> project-id=<PROJECT_ID> send-telemetry=false
scw registry namespace create name=living-map is-public=true
```

Note the namespace IDs for GitHub secrets.

## 4. Add GitHub secrets

Add these secrets in the repository Settings → Secrets and variables → Actions:

| Secret                  | Value                                                                |
| ----------------------- | -------------------------------------------------------------------- |
| `SCW_ACCESS_KEY`        | Scaleway IAM access key                                              |
| `SCW_SECRET_KEY`        | Scaleway IAM secret key                                              |
| `SCW_PROJECT_ID`        | Scaleway project ID                                                  |
| `SCW_ORGANIZATION_ID`   | Scaleway organization ID                                             |
| `SCW_NAMESPACE_ID`      | Scaleway container namespace UUID                                    |
| `SUPABASE_DATABASE_URL` | Supabase direct connection (IPv6) for jobs                           |
| `SUPABASE_POOLER_URL`   | Supabase Supavisor transaction pooler (IPv4, port 6543) for Tile API |
| `CORS_ORIGIN`           | GitHub Pages URL (e.g., `https://<user>.github.io`)                  |
| `VITE_API_URL`          | Scaleway container URL (set after first deploy)                      |
