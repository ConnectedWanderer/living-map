data "oci_identity_availability_domain" "main" {
  compartment_id = var.tenancy_ocid
  ad_number      = var.availability_domain_number
}

data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

locals {
  ubuntu_24_04_images = [
    for img in data.oci_core_images.ubuntu.images : img
    if can(regex("(?i)minimal", img.display_name))
  ]

  image_id = var.image_ocid != null ? var.image_ocid : try(local.ubuntu_24_04_images[0].id, data.oci_core_images.ubuntu.images[0].id)
}
