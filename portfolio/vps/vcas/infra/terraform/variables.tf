variable "tenancy_ocid" {
  type        = string
  description = "OCI tenancy OCID."
}

variable "compartment_ocid" {
  type        = string
  description = "OCI compartment OCID for VM resources."
}

variable "availability_domain" {
  type        = string
  description = "Availability domain name in the target compartment."
}

variable "subnet_id" {
  type        = string
  description = "Subnet OCID for the instance nic."
}

variable "ssh_public_key_path" {
  type        = string
  description = "Path to SSH public key file."
}

variable "cloud_init_script" {
  type        = string
  description = "Path to cloud-init script under this module root."
  default     = "../../cloud-init/install-vcas.sh"
}

variable "instance_name" {
  type        = string
  description = "Human-readable instance name."
  default     = "vcas-always-free-arm"
}

variable "shape_memory_gb" {
  type        = number
  description = "ARM shape memory."
  default     = 24
}

variable "shape_ocpu_count" {
  type        = number
  description = "ARM shape OCPU count."
  default     = 4
}

variable "image_ocid" {
  type        = string
  description = "OCI image OCID used for boot volume (Oracle Linux recommended)."
  default     = ""
}
