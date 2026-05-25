locals {
  cognito_base_url = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${data.aws_region.current.id}.amazoncognito.com"
  callback_url     = "https://${var.app_domain}/api/auth/callback"
  bff_common_env = {
    COGNITO_TOKEN_URL          = "${local.cognito_base_url}/oauth2/token"
    COGNITO_CLIENT_ID          = aws_cognito_user_pool_client.app.id
    COGNITO_CLIENT_SECRET      = aws_cognito_user_pool_client.app.client_secret
    COGNITO_HOSTED_UI_BASE_URL = local.cognito_base_url
    COGNITO_REVOKE_URL         = "${local.cognito_base_url}/oauth2/revoke"
    CALLBACK_URL               = local.callback_url
  }
  bff_handlers = ["login", "callback", "refresh", "logout", "post_confirmation"]
  bff_dist_dir = "${path.module}/../../../../auth-lambda/dist"
}

resource "aws_iam_role" "bff_lambda" {
  name = "convfinqa-${var.account_name}-bff-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "bff_lambda_basic" {
  role       = aws_iam_role.bff_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "bff_lambda_ssm" {
  role       = aws_iam_role.bff_lambda.name
  policy_arn = aws_iam_policy.ssm_read.arn
}

resource "aws_iam_role_policy_attachment" "bff_lambda_xray" {
  role       = aws_iam_role.bff_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_iam_role_policy_attachment" "bff_lambda_application_signals" {
  role       = aws_iam_role.bff_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLambdaApplicationSignalsExecutionRolePolicy"
}

resource "aws_cloudwatch_log_group" "bff_login" {
  name              = "/aws/lambda/convfinqa-${var.account_name}-bff-login"
  retention_in_days = 7

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "bff_callback" {
  name              = "/aws/lambda/convfinqa-${var.account_name}-bff-callback"
  retention_in_days = 7

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "bff_refresh" {
  name              = "/aws/lambda/convfinqa-${var.account_name}-bff-refresh"
  retention_in_days = 7

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "bff_logout" {
  name              = "/aws/lambda/convfinqa-${var.account_name}-bff-logout"
  retention_in_days = 7

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "bff_post_confirmation" {
  name              = "/aws/lambda/convfinqa-${var.account_name}-bff-post-confirmation"
  retention_in_days = 7

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

data "archive_file" "bff" {
  for_each = toset(local.bff_handlers)

  type        = "zip"
  source_file = "${local.bff_dist_dir}/${each.key}.mjs"
  output_path = "${path.module}/.build/${each.key}.zip"
}

resource "aws_lambda_function" "bff_login" {
  function_name    = "convfinqa-${var.account_name}-bff-login"
  role             = aws_iam_role.bff_lambda.arn
  handler          = "login.handler"
  runtime          = "nodejs22.x"
  filename         = data.archive_file.bff["login"].output_path
  source_code_hash = data.archive_file.bff["login"].output_base64sha256
  timeout          = 10
  memory_size      = 128
  layers           = [local.adot_nodejs_layer_arn]

  environment {
    variables = merge(local.bff_common_env, local.bff_adot_env)
  }

  depends_on = [aws_cloudwatch_log_group.bff_login]

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_lambda_function" "bff_callback" {
  function_name    = "convfinqa-${var.account_name}-bff-callback"
  role             = aws_iam_role.bff_lambda.arn
  handler          = "callback.handler"
  runtime          = "nodejs22.x"
  filename         = data.archive_file.bff["callback"].output_path
  source_code_hash = data.archive_file.bff["callback"].output_base64sha256
  timeout          = 15
  memory_size      = 128
  layers           = [local.adot_nodejs_layer_arn]

  environment {
    variables = merge(local.bff_common_env, local.bff_adot_env, {
      DATABASE_URL = var.database_url
    })
  }

  depends_on = [aws_cloudwatch_log_group.bff_callback]

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_lambda_function" "bff_refresh" {
  function_name    = "convfinqa-${var.account_name}-bff-refresh"
  role             = aws_iam_role.bff_lambda.arn
  handler          = "refresh.handler"
  runtime          = "nodejs22.x"
  filename         = data.archive_file.bff["refresh"].output_path
  source_code_hash = data.archive_file.bff["refresh"].output_base64sha256
  timeout          = 10
  memory_size      = 128
  layers           = [local.adot_nodejs_layer_arn]

  environment {
    variables = merge(local.bff_common_env, local.bff_adot_env)
  }

  depends_on = [aws_cloudwatch_log_group.bff_refresh]

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_lambda_function" "bff_logout" {
  function_name    = "convfinqa-${var.account_name}-bff-logout"
  role             = aws_iam_role.bff_lambda.arn
  handler          = "logout.handler"
  runtime          = "nodejs22.x"
  filename         = data.archive_file.bff["logout"].output_path
  source_code_hash = data.archive_file.bff["logout"].output_base64sha256
  timeout          = 10
  memory_size      = 128
  layers           = [local.adot_nodejs_layer_arn]

  environment {
    variables = merge(local.bff_common_env, local.bff_adot_env)
  }

  depends_on = [aws_cloudwatch_log_group.bff_logout]

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_lambda_function" "bff_post_confirmation" {
  function_name    = "convfinqa-${var.account_name}-bff-post-confirmation"
  role             = aws_iam_role.bff_lambda.arn
  handler          = "post_confirmation.handler"
  runtime          = "nodejs22.x"
  filename         = data.archive_file.bff["post_confirmation"].output_path
  source_code_hash = data.archive_file.bff["post_confirmation"].output_base64sha256
  timeout          = 10
  memory_size      = 128
  layers           = [local.adot_nodejs_layer_arn]

  environment {
    variables = merge(local.bff_adot_env, {
      DATABASE_URL = var.database_url
    })
  }

  depends_on = [aws_cloudwatch_log_group.bff_post_confirmation]

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_lambda_function_url" "bff_login" {
  function_name      = aws_lambda_function.bff_login.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["https://${var.app_domain}"]
    allow_methods = ["GET"]
  }
}

resource "aws_lambda_function_url" "bff_callback" {
  function_name      = aws_lambda_function.bff_callback.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["https://${var.app_domain}"]
    allow_methods = ["GET"]
  }
}

resource "aws_lambda_function_url" "bff_refresh" {
  function_name      = aws_lambda_function.bff_refresh.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["https://${var.app_domain}"]
    allow_methods = ["POST"]
  }
}

resource "aws_lambda_function_url" "bff_logout" {
  function_name      = aws_lambda_function.bff_logout.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["https://${var.app_domain}"]
    allow_methods = ["POST"]
  }
}

resource "aws_lambda_permission" "cognito_post_confirmation" {
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bff_post_confirmation.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}
