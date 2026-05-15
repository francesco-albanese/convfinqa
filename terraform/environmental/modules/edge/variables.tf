variable "app_domain" {
  description = "Fully-qualified domain name for the SPA + API (primary cert domain and CloudFront CNAME)"
  type        = string
}

variable "apex_domain" {
  description = "Apex project domain included as a SAN on the ACM cert"
  type        = string
}

variable "parent_zone_name" {
  description = "Route53 hosted zone name in shared-services for ACM DNS-validation CNAMEs"
  type        = string
}
