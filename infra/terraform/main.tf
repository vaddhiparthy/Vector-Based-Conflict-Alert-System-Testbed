terraform {
  required_version = ">= 1.8"
}

module "oracle_free_vm" {
  source = "./modules/oracle_free_arm_vm"

  tenancy_ocid          = var.tenancy_ocid
  compartment_ocid      = var.compartment_ocid
  availability_domain   = var.availability_domain
  subnet_id             = var.subnet_id
  ssh_public_key_path   = var.ssh_public_key_path
  cloud_init_script     = var.cloud_init_script
  instance_name         = var.instance_name
  shape_memory_gb       = var.shape_memory_gb
  shape_ocpu_count      = var.shape_ocpu_count
  image_ocid            = var.image_ocid
}

