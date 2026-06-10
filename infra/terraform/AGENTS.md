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

## Conventions

- See `README.md` for full setup guide and OCI credential workflow.
- `terraform.tfvars` is gitignored — secrets live there.
- Script `.env` at `scripts/.env` is also gitignored.
- Always run `terraform fmt -recursive .` before committing.
- The `.terraform.lock.hcl` file should be committed (provider pinning).
