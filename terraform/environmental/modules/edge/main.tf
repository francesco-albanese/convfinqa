data "aws_caller_identity" "current" {}

data "aws_route53_zone" "parent" {
  provider     = aws.shared_services
  name         = var.parent_zone_name
  private_zone = false
}

locals {
  s3_origin_id  = "convfinqa-site-s3"
  alb_origin_id = "convfinqa-api-alb"
  bff_origins = {
    login    = trimsuffix(trimprefix(var.bff_login_url, "https://"), "/")
    callback = trimsuffix(trimprefix(var.bff_callback_url, "https://"), "/")
    refresh  = trimsuffix(trimprefix(var.bff_refresh_url, "https://"), "/")
    logout   = trimsuffix(trimprefix(var.bff_logout_url, "https://"), "/")
  }
}
