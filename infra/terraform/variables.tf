variable "region" {
  description = "OCI region identifier (e.g. us-ashburn-1, eu-frankfurt-1)"
  type        = string
}

variable "tenancy_ocid" {
  description = "OCID of the OCI tenancy"
  type        = string
  sensitive   = true
}

variable "compartment_ocid" {
  description = "OCID of the compartment to deploy into"
  type        = string
}

variable "user_ocid" {
  description = "OCID of the API user"
  type        = string
  sensitive   = true
}

variable "api_fingerprint" {
  description = "Fingerprint of the OCI API key"
  type        = string
}

variable "api_private_key_path" {
  description = "Local filesystem path to the OCI API private key PEM"
  type        = string
}

variable "ssh_public_key_path" {
  description = "Local filesystem path to the SSH public key for VM access"
  type        = string
}

variable "tenancy_namespace" {
  description = "OCI Object Storage namespace (found in Tenancy Details page)"
  type        = string
}

variable "state_bucket_name" {
  description = "Name of the OCI Object Storage bucket for Terraform remote state"
  type        = string
  default     = "living-map-terraform-state"
}

variable "availability_domain_number" {
  description = "Availability domain number (1-3). Change if capacity is exhausted in AD-1."
  type        = number
  default     = 1

  validation {
    condition     = var.availability_domain_number >= 1 && var.availability_domain_number <= 3
    error_message = "Availability domain number must be 1, 2, or 3."
  }
}

variable "instance_shape" {
  description = "Compute instance shape"
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "instance_ocpus" {
  description = "Number of OCPUs for the instance"
  type        = number
  default     = 1
}

variable "instance_memory_gb" {
  description = "Memory in GB for the instance"
  type        = number
  default     = 6
}

variable "image_ocid" {
  description = "Override image OCID. If null, auto-selects the latest Canonical Ubuntu 24.04 image."
  type        = string
  default     = null
}

variable "vcn_cidr" {
  description = "CIDR block for the VCN"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "project_name" {
  description = "Project name used as a prefix for resource naming"
  type        = string
  default     = "living-map"
}

variable "coolify_version" {
  description = "Coolify version tag to install (or 'latest')"
  type        = string
  default     = "latest"
}
