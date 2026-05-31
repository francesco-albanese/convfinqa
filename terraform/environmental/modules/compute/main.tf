data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_kms_key" "ssm" {
  key_id = "alias/aws/ssm"
}

data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

locals {
  cognito_native_auth_enabled = var.account_name != "production"
  e2e_email                   = var.e2e_user_email != "" ? var.e2e_user_email : "e2e+${var.account_name}@francescoalbanese.dev"
  langfuse_configured         = var.langfuse_enabled
  gemini_configured           = var.gemini_enabled
  secure_string_kms_key_arn   = coalesce(var.ssm_kms_key_arn, data.aws_kms_key.ssm.arn)
  ssm_decrypt_kms_key_arns    = tolist(toset([data.aws_kms_key.ssm.arn, local.secure_string_kms_key_arn]))

  cloudwatch_agent_config = {
    traces = {
      traces_collected = {
        application_signals = {}
        otlp = {
          grpc_endpoint = "127.0.0.1:4317"
          http_endpoint = "127.0.0.1:4318"
        }
      }
    }
    logs = {
      metrics_collected = {
        application_signals = {}
      }
    }
  }
}

data "aws_ssm_parameter" "google_client_id" {
  name = "/convfinqa/${var.account_name}/google_oauth_client_id"
}

data "aws_ssm_parameter" "google_client_secret" {
  name            = "/convfinqa/${var.account_name}/google_oauth_client_secret"
  with_decryption = true
}
