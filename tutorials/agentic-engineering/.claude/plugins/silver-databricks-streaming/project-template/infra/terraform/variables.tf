variable "aws_region" {
  description = "AWS region for the EC2 instance"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type — t3.small for Stages 3-8 (CDC only), t3.medium for Stage 9+ (adds PySpark OpenSearch sink)"
  type        = string
  default     = "t3.small"
}

variable "key_pair_name" {
  description = "Name of the EC2 key pair for SSH access"
  type        = string
}

variable "key_path" {
  description = "Local path to the private key file (for SSH)"
  type        = string
}

variable "databricks_nat_cidrs" {
  description = "Databricks control plane NAT gateway CIDR blocks (for Kafka access)"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Open for tutorial — restrict in production
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into the EC2 instance"
  type        = string
  default     = "0.0.0.0/0"  # Restrict to your IP in production
}

variable "enable_opensearch" {
  description = "Set to true when ready for OpenSearch (Stage 11) — adds ~$0.036/hr"
  type        = bool
  default     = false
}

variable "opensearch_instance_type" {
  description = "OpenSearch instance type — t3.small.search is sufficient for tutorial"
  type        = string
  default     = "t3.small.search"
}

variable "opensearch_master_user" {
  description = "OpenSearch master username"
  type        = string
  default     = "admin"
}

variable "opensearch_master_password" {
  description = "OpenSearch master password (min 8 chars, uppercase, lowercase, number, special)"
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Project name used for resource tagging"
  type        = string
  default     = "silveraiwolf-streaming"
}
