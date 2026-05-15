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
