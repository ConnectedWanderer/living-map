output "instance_public_ip" {
  description = "Public IP address of the VM"
  value       = oci_core_instance.main.public_ip
}

output "instance_ocid" {
  description = "OCID of the created compute instance"
  value       = oci_core_instance.main.id
}

output "coolify_url" {
  description = "Coolify web UI URL"
  value       = "http://${oci_core_instance.main.public_ip}:8000"
}

output "ssh_command" {
  description = "SSH command to access the VM"
  value       = "ssh ubuntu@${oci_core_instance.main.public_ip}"
}

output "availability_domain" {
  description = "Availability domain the instance was provisioned in"
  value       = data.oci_identity_availability_domain.main.name
}

output "vcn_ocid" {
  description = "OCID of the created VCN"
  value       = oci_core_vcn.main.id
}

output "subnet_ocid" {
  description = "OCID of the public subnet"
  value       = oci_core_subnet.public.id
}
