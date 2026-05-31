resource "aws_cognito_user_pool" "main" {
  name = "convfinqa-${var.account_name}"

  auto_verified_attributes = ["email"]

  username_configuration {
    case_sensitive = false
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  schema {
    name                     = "email"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 1
      max_length = 2048
    }
  }

  lambda_config {
    post_confirmation = aws_lambda_function.bff_post_confirmation.arn
  }

  tags = {
    Name = "convfinqa-${var.account_name}"
  }
}

resource "aws_cognito_identity_provider" "google" {
  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    client_id        = data.aws_ssm_parameter.google_client_id.value
    client_secret    = data.aws_ssm_parameter.google_client_secret.value
    authorize_scopes = "openid email profile"
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
  }
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = var.cognito_hosted_ui_prefix
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "aws_cognito_user_pool_client" "app" {
  name         = "convfinqa-app"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = true

  callback_urls = concat(
    ["https://${var.app_domain}/api/auth/callback"],
    var.extra_cognito_callback_urls,
  )
  logout_urls = concat(
    ["https://${var.app_domain}/"],
    var.extra_cognito_logout_urls,
  )

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  allowed_oauth_flows_user_pool_client = true
  supported_identity_providers = concat(
    [aws_cognito_identity_provider.google.provider_name],
    local.cognito_native_auth_enabled ? ["COGNITO"] : [],
  )

  enable_token_revocation       = true
  prevent_user_existence_errors = "ENABLED"

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30
}

resource "aws_ssm_parameter" "cognito_user_pool_id" {
  name  = "/convfinqa/${var.account_name}/cognito_user_pool_id"
  type  = "String"
  value = aws_cognito_user_pool.main.id

  tags = {
    Name = "convfinqa-cognito-user-pool-id"
  }
}

resource "aws_ssm_parameter" "cognito_client_id" {
  name  = "/convfinqa/${var.account_name}/cognito_client_id"
  type  = "String"
  value = aws_cognito_user_pool_client.app.id

  tags = {
    Name = "convfinqa-cognito-client-id"
  }
}

resource "aws_ssm_parameter" "cognito_client_secret" {
  name   = "/convfinqa/${var.account_name}/cognito_client_secret"
  type   = "SecureString"
  value  = aws_cognito_user_pool_client.app.client_secret
  key_id = local.secure_string_kms_key_arn

  tags = {
    Name = "convfinqa-cognito-client-secret"
  }
}

resource "random_password" "e2e" {
  count            = local.cognito_native_auth_enabled ? 1 : 0
  length           = 24
  special          = true
  override_special = "!@#$%^&*()-_=+[]{}"
  min_lower        = 1
  min_upper        = 1
  min_numeric      = 1
  min_special      = 1
}

resource "aws_cognito_user" "e2e" {
  count        = local.cognito_native_auth_enabled ? 1 : 0
  user_pool_id = aws_cognito_user_pool.main.id
  username     = local.e2e_email
  # The provider's `password` argument maps to a permanent Cognito password.
  # Do not switch this to a temporary AdminCreateUser flow; Playwright must not
  # hit a first-login password-reset challenge.
  password = random_password.e2e[0].result
  enabled  = true

  message_action = "SUPPRESS"

  attributes = {
    email          = local.e2e_email
    email_verified = "true"
  }
}

resource "aws_ssm_parameter" "e2e_email" {
  count = local.cognito_native_auth_enabled ? 1 : 0
  name  = "/convfinqa/${var.account_name}/e2e_email"
  type  = "String"
  value = local.e2e_email

  tags = {
    Name = "convfinqa-e2e-email"
  }
}

resource "aws_ssm_parameter" "e2e_password" {
  count  = local.cognito_native_auth_enabled ? 1 : 0
  name   = "/convfinqa/${var.account_name}/e2e_password"
  type   = "SecureString"
  value  = random_password.e2e[0].result
  key_id = local.secure_string_kms_key_arn

  tags = {
    Name = "convfinqa-e2e-password"
  }
}
