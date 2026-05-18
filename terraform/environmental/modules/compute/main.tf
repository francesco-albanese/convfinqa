data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_kms_key" "ssm" {
  key_id = "alias/aws/ssm"
}

data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

data "aws_ssm_parameter" "google_client_id" {
  name = "/convfinqa/${var.account_name}/google_oauth_client_id"
}

data "aws_ssm_parameter" "google_client_secret" {
  name            = "/convfinqa/${var.account_name}/google_oauth_client_secret"
  with_decryption = true
}
