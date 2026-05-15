data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_kms_key" "ssm" {
  key_id = "alias/aws/ssm"
}

data "aws_ssm_parameter" "google_client_id" {
  name = "/convfinqa/${var.account_name}/google/client_id"
}

data "aws_ssm_parameter" "google_client_secret" {
  name            = "/convfinqa/${var.account_name}/google/client_secret"
  with_decryption = true
}

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

  callback_urls = ["https://${var.app_domain}/api/auth/callback"]
  logout_urls   = ["https://${var.app_domain}/"]

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  allowed_oauth_flows_user_pool_client = true
  supported_identity_providers         = [aws_cognito_identity_provider.google.provider_name]

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
  name  = "/convfinqa/${var.account_name}/cognito_client_secret"
  type  = "SecureString"
  value = aws_cognito_user_pool_client.app.client_secret

  tags = {
    Name = "convfinqa-cognito-client-secret"
  }
}

resource "aws_ecr_repository" "app" {
  name                 = "convfinqa"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "convfinqa"
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Retain last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ssm_parameter" "bedrock_region" {
  name  = "/convfinqa/${var.account_name}/bedrock_region"
  type  = "String"
  value = var.bedrock_region

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_ssm_parameter" "system_prompt_override" {
  name  = "/convfinqa/${var.account_name}/system_prompt_override"
  type  = "SecureString"
  value = var.system_prompt_override

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_iam_policy" "ssm_read" {
  name        = "convfinqa-${var.account_name}-ssm-read"
  description = "Read access to all convfinqa SSM parameters for this environment"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath",
        ]
        Resource = "arn:aws:ssm:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:parameter/convfinqa/${var.account_name}/*"
      },
      {
        Effect   = "Allow"
        Action   = "kms:Decrypt"
        Resource = data.aws_kms_key.ssm.arn
      },
    ]
  })

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}
