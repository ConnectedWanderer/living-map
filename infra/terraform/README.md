# Terraform — Oracle Cloud Infrastructure + Coolify

Provisions an Oracle Cloud Always-Free ARM instance (`VM.Standard.A1.Flex`) running Ubuntu 24.04, installs Docker and Coolify, then configures the Coolify project and triggers a deployment of the Living Map stack.

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.15.6
- [Oracle Cloud CLI (`oci`)](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm) — used to create the remote state bucket
- An [Oracle Cloud](https://cloud.oracle.com) account with the Always-Free tier enabled
- Python 3 (for post-deploy script JSON parsing and `oci` CLI dependency)
- `curl`
- OpenSSH (for `ssh-keygen` and `ssh` commands)

## One-time setup

### 1. OCI API key

Terraform authenticates to OCI via an API key pair. Generate one and upload it to your OCI user.

```bash
mkdir -p ~/.oci
openssl genrsa -out ~/.oci/oci_api_key.pem 2048
chmod 600 ~/.oci/oci_api_key.pem
openssl rsa -pubout -in ~/.oci/oci_api_key.pem -out ~/.oci/oci_api_key_public.pem
```

**Upload the public key:**

1. Go to [OCI Console](https://cloud.oracle.com) → Identity → Users
2. Click your username → scroll to **API Keys** → **Add API Key**
3. Select **Paste Public Key**, paste the contents of `~/.oci/oci_api_key_public.pem`
4. Click **Add** — a fingerprint (e.g. `aa:bb:cc:dd:...`) is displayed. Copy it.

### 2. Collect OCIDs

From the OCI Console, navigate to each page and copy the OCID:

| Value | Where to find it |
|---|---|
| **Tenancy OCID** | Identity → Tenancy → **Tenancy Details** |
| **Compartment OCID** | Identity → Compartments → click your compartment |
| **User OCID** | Identity → Users → click your user |
| **Tenancy Namespace** | Identity → Tenancy → **Tenancy Details** (Object Storage Settings) |

### 3. SSH key pair

Generate an SSH key pair to access the VM:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/living-map -N ""
```

This creates `~/.ssh/living-map` (private) and `~/.ssh/living-map.pub` (public).

### 4. Create the state bucket

The bucket must exist before `terraform init`. Create it with the OCI CLI:

```bash
oci os bucket create \
  --namespace <tenancy-namespace> \
  --compartment-id <compartment-ocid> \
  --name living-map-terraform-state
```

> **No OCI CLI?** Create the bucket via the OCI Console: Storage → Object Storage → Buckets → **Create Bucket**, name it `living-map-terraform-state`.

The state backend uses Terraform's native `backend "oci"`, which authenticates with the same OCI API key from step 1 — no additional credentials needed.

## Configuration

### Create `terraform.tfvars`

Copy the example and fill in your values:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with the OCIDs, key paths, and namespace collected above.

### Create the post-deploy `.env` (optional)

If you want the automated Coolify setup to run, create `scripts/.env`:

```env
COOLIFY_ADMIN_NAME=Admin
COOLIFY_ADMIN_EMAIL=admin@example.com
COOLIFY_ADMIN_PASSWORD=<generate-a-strong-password>
GITHUB_REPO=https://github.com/your-org/living-map
GITHUB_BRANCH=main
DB_PASSWORD=<choose-a-database-password>
```

## Deploy

```bash
# 1. Init Terraform with remote state backend
terraform init \
  -backend-config="bucket=living-map-terraform-state" \
  -backend-config="key=infra/terraform.tfstate" \
  -backend-config="region=$(grep ^region terraform.tfvars | cut -d= -f2 | tr -d ' \"')" \
  -backend-config="namespace=$(grep ^tenancy_namespace terraform.tfvars | cut -d= -f2 | tr -d ' \"')"

# 2. Review the plan
terraform plan

# 3. Apply
terraform apply
```

After `terraform apply` completes, note the `instance_public_ip` output.

## Post-deploy: Coolify configuration

Run the automation script with the VM's public IP:

```bash
./scripts/configure-coolify.sh <instance_public_ip>
```

The script will:
1. Wait for Coolify to start (takes 1-3 minutes after instance boot)
2. Register the admin account
3. Log in and obtain an API token
4. Create a `living-map` project with a `production` environment
5. Create an application from your GitHub repo (Docker Compose build)
6. Set environment variables per service
7. Trigger the first deployment

If any step fails, the script prints manual instructions to finish via the Coolify UI at `http://<ip>:8000`.

## Troubleshooting

### "Out of capacity" for A1.Flex

Oracle's free-tier ARM capacity is limited. If `terraform apply` fails with a capacity error:

1. Try a different availability domain: set `availability_domain_number = 2` (or 3) in `terraform.tfvars`
2. Try a different region (some have more capacity than others)
3. Wait a few hours and retry

### Can't find Ubuntu 24.04 Minimal image

If the image data source returns no results, find the image OCID manually:

1. Go to OCI Console → Compute → Images
2. Filter for "Canonical Ubuntu 24.04 Minimal"
3. Copy the image OCID and set `image_ocid` in `terraform.tfvars`

### Coolify doesn't start

SSH into the VM and check the installation log:

```bash
ssh ubuntu@<ip>
sudo journalctl -u docker -n 50
docker logs coolify -f
```

## Clean up

Destroy all resources when you no longer need them:

```bash
terraform destroy
```

## File reference

| File | Purpose |
|---|---|
| `versions.tf` | Terraform version, backend, and provider constraints |
| `provider.tf` | OCI provider authentication |
| `variables.tf` | All input variables with documentation |
| `data.tf` | Data sources: availability domain, Ubuntu image |
| `network.tf` | VCN, internet gateway, route table, public subnet |
| `security.tf` | Security list: SSH (22), HTTP (80), HTTPS (443), Coolify (8000) |
| `compute.tf` | A1.Flex instance with cloud-init |
| `outputs.tf` | Public IP, OCIDs, SSH command |
| `user-data.sh.tftpl` | Cloud-init script: Docker + Coolify installation |
| `terraform.tfvars.example` | Documented variable values template |
| `scripts/configure-coolify.sh` | Post-deploy Coolify API automation |
