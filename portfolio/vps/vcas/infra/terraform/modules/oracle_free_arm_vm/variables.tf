variable "tenancy_ocid" {
  type        = string
  description = "OCI tenancy OCID."
}

variable "compartment_ocid" {
  type        = string
  description = "OCI compartment OCID."
}

variable "availability_domain" {
  type        = string
  description = "Availability domain."
}

variable "subnet_id" {
  type        = string
  description = "Subnet OCID."
}

variable "region" {
  type        = string
  description = "OCI region."
  default     = "us-ashburn-1"
}

variable "ssh_public_key_path" {
  type        = string
  description = "Path to SSH public key file."
}

variable "instance_name" {
  type        = string
  description = "Instance display name."
}

variable "shape_memory_gb" {
  type        = number
  description = "RAM size in GiB."
}

variable "shape_ocpu_count" {
  type        = number
  description = "OCPU count."
}

variable "image_ocid" {
  type        = string
  description = "Optional explicit image OCID."
  default     = ""
}

variable "image_name_filter" {
  type        = string
  default     = "Oracle-Linux-Cloudinit"
}

