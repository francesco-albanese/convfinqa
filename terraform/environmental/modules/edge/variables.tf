variable "app_domain" {
  description = "Fully-qualified domain name for the SPA + API (primary cert domain and CloudFront CNAME)"
  type        = string
}

variable "parent_zone_name" {
  description = "Route53 hosted zone name in shared-services for ACM DNS-validation CNAMEs"
  type        = string
}

variable "bff_login_url" {
  description = "Lambda Function URL for /api/auth/login."
  type        = string
}

variable "bff_callback_url" {
  description = "Lambda Function URL for /api/auth/callback."
  type        = string
}

variable "bff_refresh_url" {
  description = "Lambda Function URL for /api/auth/refresh."
  type        = string
}

variable "bff_logout_url" {
  description = "Lambda Function URL for /api/auth/logout."
  type        = string
}
