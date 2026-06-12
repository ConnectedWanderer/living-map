# AI Agent Instructions — infra/terraform

## Purpose

Terraform configuration for provisioning an Oracle Cloud Always-Free ARM instance and installing Coolify for the Living Map application.

## Commands

```bash
# Format all Terraform files
terraform fmt -recursive .

# Validate configuration
terraform init -backend=false && terraform validate && rm -rf .terraform/ .terraform.lock.hcl

# Full deploy flow
# 1. Init with remote state backend (uses OCI API key from provider config)
terraform init \
  -backend-config="bucket=living-map-terraform-state" \
  -backend-config="key=infra/terraform.tfstate" \
  -backend-config="region=<region>" \
  -backend-config="namespace=<tenancy-namespace>"

# 3. Apply
terraform plan && terraform apply

# 4. Post-deploy Coolify setup
./scripts/configure-coolify.sh <vm-public-ip>

# Destroy
terraform destroy
```

## Retry loop for "Out of capacity"

When OCI returns "Out of capacity" for `VM.Standard.A1.Flex`, run the retry script:

```bash
# Run in foreground (Ctrl+C to stop)
./scripts/retry-apply.sh

# Or run in background
nohup ./scripts/retry-apply.sh >> /tmp/retry.log 2>&1 &

# Custom interval (default 60s)
RETRY_INTERVAL=300 ./scripts/retry-apply.sh
```

The script cycles through ADs 1→2→3 per pass, sleeping 5 minutes after all 3 are exhausted.
On success it runs `configure-coolify.sh` automatically.

## Key files

| File | Purpose |
|---|---|
| `versions.tf` | Pins Terraform >= 1.15.6, OCI provider ~> 5.30 |
| `variables.tf` | All input variables — see README for descriptions |
| `compute.tf` | A1.Flex instance with cloud-init user-data |
| `network.tf` | VCN, subnet, internet gateway, routing |
| `security.tf` | Security list rules: 22, 80, 443, 8000 |
| `data.tf` | Availability domain + Ubuntu 24.04 Minimal image lookup |
| `user-data.sh.tftpl` | Cloud-init: Docker Engine + Coolify installation |
| `scripts/retry-apply.sh` | Retry loop across ADs until ARM capacity becomes available |

## Conventions

- See `README.md` for full setup guide and OCI credential workflow.
- `terraform.tfvars` is gitignored — secrets live there.
- Script `.env` at `scripts/.env` is also gitignored.
- Always run `terraform fmt -recursive .` before committing.
- The `.terraform.lock.hcl` file should be committed (provider pinning).
