variable "vpc_id" {
  description = "VPC ID for the Lambda security group."
  type        = string
}

variable "public_subnet_ids" {
  description = "Subnet IDs where the Lambda function will run."
  type        = list(string)
}

variable "aurora_sg_id" {
  description = "Security group ID of the Aurora cluster. An ingress rule for the Lambda SG will be added."
  type        = string
}

variable "account_name" {
  description = "Environment name (sandbox/staging/uat/production) — scopes resource names."
  type        = string
}

variable "database_url" {
  description = "Plain postgresql:// URL for Aurora cluster (passed as Lambda env var DATABASE_URL)."
  type        = string
  sensitive   = true
}
