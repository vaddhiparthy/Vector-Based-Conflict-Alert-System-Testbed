output "instance_id" {
  description = "OCI instance OCID for the deployed vCAS node."
  value       = oci_core_instance.vcas_node.id
}

output "public_ip" {
  description = "Public IPv4 address for the deployed vCAS node."
  value       = oci_core_vnic.vnic.public_ip
}
