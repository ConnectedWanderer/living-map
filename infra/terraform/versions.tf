terraform {
  required_version = ">= 1.15.6"

  backend "oci" {
  }

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.30"
    }
  }
}
