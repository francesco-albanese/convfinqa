variable "public_subnet_ids" {
  description = "IDs of the public subnets for the DB subnet group."
  type        = list(string)
}

variable "aurora_sg_id" {
  description = "Security group ID for the Aurora cluster (inbound from ECS tasks only)."
  type        = string
}

variable "account_name" {
  description = "Environment name (sandbox/staging/uat/production) — scopes SSM paths and resource names."
  type        = string
}
