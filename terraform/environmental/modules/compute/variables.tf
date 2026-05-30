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

variable "extra_cognito_callback_urls" {
  description = "Additional Cognito OAuth callback URLs for non-production local development."
  type        = list(string)
  default     = []
}

variable "extra_cognito_logout_urls" {
  description = "Additional Cognito OAuth logout URLs for non-production local development."
  type        = list(string)
  default     = []
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

variable "langfuse_enabled" {
  description = "Whether to inject manually managed Langfuse SSM parameters into the ECS API task."
  type        = bool
  default     = false
}

variable "gemini_enabled" {
  description = "Whether to inject the manually managed Gemini API key SSM parameter into the ECS API task (required when llm_models offers a gemini/* model)."
  type        = bool
  default     = false
}

variable "ssm_kms_key_arn" {
  description = "Optional KMS key ARN used for SecureString SSM parameters; defaults to alias/aws/ssm."
  type        = string
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
