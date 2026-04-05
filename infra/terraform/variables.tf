variable "vultr_api_key" {
  description = "Vultr API key"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "Vultr region (London)"
  type        = string
  default     = "lhr"
}

variable "k8s_version" {
  description = "Kubernetes version"
  type        = string
  default     = "v1.33.9+1"
}

variable "node_plan" {
  description = "Vultr plan for worker nodes"
  type        = string
  default     = "vc2-2c-4gb"  # 2 vCPU, 4GB RAM, ~$24/mo  (resize requires new node pool)
}

variable "node_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 1
}
