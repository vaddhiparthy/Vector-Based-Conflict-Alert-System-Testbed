locals {
  cloud_init_script_path = startswith(var.cloud_init_script, "/") ? var.cloud_init_script : "${path.module}/${var.cloud_init_script}"
}

terraform {
  required_version = ">= 1.8"
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  compartment_id   = var.compartment_ocid
  region           = var.region
}

data "oci_core_images" "candidate_images" {
  compartment_id = var.compartment_ocid
  display_name   = var.image_name_filter
}

resource "oci_core_instance" "vcas_node" {
  availability_domain = var.availability_domain
  compartment_id     = var.compartment_ocid
  display_name       = var.instance_name
  shape              = "VM.Standard.A1.Flex"

  shape_config {
    memory_in_gbs = var.shape_memory_gb
    ocpus         = var.shape_ocpu_count
  }

  create_vnic_details {
    assign_public_ip = true
    subnet_id        = var.subnet_id
  }

  source_details {
    source_type               = "image"
    source_id                 = var.image_ocid != "" ? var.image_ocid : data.oci_core_images.candidate_images.images[0].id
    boot_volume_size_in_gbs   = 50
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data          = filebase64(local.cloud_init_script_path)
  }

  preserve_boot_volume = false
}

data "oci_core_vnic_attachments" "attachments" {
  compartment_id = var.compartment_ocid
  instance_id    = oci_core_instance.vcas_node.id
}

data "oci_core_vnic" "vnic" {
  vnic_id = data.oci_core_vnic_attachments.attachments.vnic_attachments[0].vnic_id
}
