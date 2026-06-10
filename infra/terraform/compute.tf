resource "oci_core_instance" "main" {
  availability_domain = data.oci_identity_availability_domain.main.name
  compartment_id      = var.compartment_ocid
  display_name        = "${var.project_name}-vm"
  shape               = var.instance_shape

  shape_config {
    ocpus         = var.instance_ocpus
    memory_in_gbs = var.instance_memory_gb
  }

  source_details {
    source_type = "image"
    source_id   = local.image_id
  }

  create_vnic_details {
    assign_public_ip = true
    subnet_id        = oci_core_subnet.public.id
    display_name     = "${var.project_name}-vnic"
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data = base64encode(templatefile("${path.module}/user-data.sh.tftpl", {
      coolify_version = var.coolify_version
    }))
  }
}
