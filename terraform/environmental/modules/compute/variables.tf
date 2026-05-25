variable "cognito_hosted_ui_prefix" {
  description = "Subdomain prefix for the Cognito hosted UI domain."
  type        = string
}

variable "account_name" {
  description = "Environment name used to scope SSM parameter paths (sandbox/staging/uat/production)."
  type        = string
}

variable "app_domain" {
  description = "Fully-qualified app domain for constructing Cognito callback and logout URLs."
  type        = string
}

variable "bedrock_region" {
  description = "AWS region where the Bedrock LLM endpoint is hosted."
  type        = string
  default     = "eu-west-1"
}

variable "system_prompt_override" {
  description = "Optional system-prompt override stored in SSM. Leave empty to use the application default."
  type        = string
  default     = ""
}

variable "langfuse_public_key" {
  description = "Langfuse public key stored as an SSM SecureString."
  type        = string
  sensitive   = true
  nullable    = true
  default     = null
}

variable "langfuse_secret_key" {
  description = "Langfuse secret key stored as an SSM SecureString."
  type        = string
  sensitive   = true
  nullable    = true
  default     = null
}

variable "cloudwatch_agent_image" {
  description = "Pinned CloudWatch agent image for application signals sidecar."
  type        = string
  default     = "public.ecr.aws/cloudwatch-agent/cloudwatch-agent:1.300062.0b1304"
}

variable "public_subnet_ids" {
  description = "IDs of the public subnets where ECS tasks run."
  type        = list(string)
}

variable "ecs_sg_id" {
  description = "Security group ID for ECS tasks (CloudFront-locked inbound on port 8000)."
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy (e.g. git SHA)."
  type        = string
  default     = "latest"
}

variable "vpc_id" {
  description = "VPC ID for the ALB security group."
  type        = string
}

variable "database_url" {
  description = "PostgreSQL connection URL injected into DB-touching BFF Lambda functions."
  type        = string
  sensitive   = true
}
