variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (e.g. staging, prod)."
  type        = string
  default     = "staging"
}

variable "project" {
  description = "Resource name prefix."
  type        = string
  default     = "graphintel"
}

# --- Network ---
variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "az_count" {
  description = "Number of Availability Zones to span (min 2 for RDS/ALB)."
  type        = number
  default     = 2
}

# --- Containers ---
variable "api_image_tag" {
  description = "Image tag deployed for the API service. CI overrides this with the commit SHA."
  type        = string
  default     = "latest"
}

variable "api_container_port" {
  description = "Port the API listens on inside the container."
  type        = number
  default     = 8000
}

variable "api_desired_count" {
  description = "Number of API tasks to run."
  type        = number
  default     = 2
}

variable "api_cpu" {
  description = "Fargate task CPU units for the API (1024 = 1 vCPU)."
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Fargate task memory (MiB) for the API."
  type        = number
  default     = 1024
}

variable "web_desired_count" {
  description = "Number of frontend tasks to run."
  type        = number
  default     = 2
}

variable "web_cpu" {
  description = "Fargate task CPU units for the frontend."
  type        = number
  default     = 256
}

variable "web_memory" {
  description = "Fargate task memory (MiB) for the frontend."
  type        = number
  default     = 512
}

# --- Data stores ---
variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GiB."
  type        = number
  default     = 20
}

variable "db_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "graphintel"
}

variable "db_username" {
  description = "PostgreSQL master username."
  type        = string
  default     = "graphintel"
}

variable "redis_node_type" {
  description = "ElastiCache node type for the Celery/RQ broker."
  type        = string
  default     = "cache.t4g.micro"
}

# --- Application config surfaced as env / secrets ---
variable "llm_provider" {
  description = "LLM provider for AWS. Use a real provider for staging/prod."
  type        = string
  default     = "anthropic"
}

variable "embedding_provider" {
  description = "Embedding provider for AWS. Use fastembed, bedrock, or voyage for staging/prod."
  type        = string
  default     = "fastembed"
}

variable "extraction_provider" {
  description = "Extraction provider for AWS free-text extraction."
  type        = string
  default     = "llm"
}

variable "anthropic_api_key" {
  description = "Anthropic API key for production answer generation/extraction. Stored in Secrets Manager, never in plaintext outputs."
  type        = string
  default     = ""
  sensitive   = true
}

variable "voyage_api_key" {
  description = "Optional Voyage API key when embedding_provider=voyage. Stored in Secrets Manager."
  type        = string
  default     = ""
  sensitive   = true
}

variable "bedrock_embedding_model" {
  description = "Amazon Bedrock embedding model id."
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "fastembed_embedding_model" {
  description = "FastEmbed ONNX model baked into the API image."
  type        = string
  default     = "BAAI/bge-small-en-v1.5"
}

variable "neptune_instance_class" {
  description = "Neptune instance class."
  type        = string
  default     = "db.t4g.medium"
}

variable "log_retention_days" {
  description = "CloudWatch log retention."
  type        = number
  default     = 30
}
