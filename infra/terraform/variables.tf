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
  default     = "vc2-4c-8gb"  # 4 vCPU, 8GB RAM, ~$48/mo
}

variable "node_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 1
}
