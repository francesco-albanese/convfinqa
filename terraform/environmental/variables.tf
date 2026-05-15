variable "region" {
  description = "AWS region for infrastructure"
  type        = string
  default     = "eu-west-2"
}

variable "account_id" {
  description = "AWS account ID for this environmental account"
  type        = string
}

variable "account_name" {
  description = "The name of the account (sandbox/staging/uat/production)"
  type        = string
}

variable "shared_services_account_id" {
  description = "AWS account ID for shared-services (Route53, state backend)"
  type        = string
  default     = "088994864650"
}

variable "shared_services_role_name" {
  description = "IAM role name in shared-services for cross-account access"
  type        = string
  default     = "terraform"
}

variable "cognito_hosted_ui_prefix" {
  description = "Subdomain prefix for the Cognito hosted UI (e.g. 'convfinqa-sandbox' → 'convfinqa-sandbox.auth.<region>.amazoncognito.com'). Must be globally unique within the region."
  type        = string
}