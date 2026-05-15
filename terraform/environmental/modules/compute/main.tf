data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_kms_key" "ssm" {
  key_id = "alias/aws/ssm"
}

data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
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

# ── ECS cluster ──────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "convfinqa-${var.account_name}"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/convfinqa-${var.account_name}"
  retention_in_days = 7

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

# ── ECS IAM roles ─────────────────────────────────────────────────────────────

resource "aws_iam_role" "ecs_task" {
  name = "convfinqa-${var.account_name}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_ssm" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ssm_read.arn
}

resource "aws_iam_role_policy" "ecs_task_bedrock" {
  name = "bedrock-invoke"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
      ]
      Resource = [
        "arn:aws:bedrock:eu-*::foundation-model/*",
        "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/eu.*",
      ]
    }]
  })
}

resource "aws_iam_role" "ecs_execution" {
  name = "convfinqa-${var.account_name}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "ecs_execution_ssm" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = aws_iam_policy.ssm_read.arn
}

# ── ECS task definition & service ────────────────────────────────────────────

resource "aws_ecs_task_definition" "api" {
  family                   = "convfinqa-${var.account_name}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  task_role_arn            = aws_iam_role.ecs_task.arn
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
    essential = true

    portMappings = [{ containerPort = 8000, protocol = "tcp" }]

    environment = [
      { name = "API_HOST", value = "0.0.0.0" },
      { name = "API_PORT", value = "8000" },
      { name = "COGNITO_REGION", value = data.aws_region.current.id },
    ]

    secrets = [
      { name = "DATABASE_URL", valueFrom = "/convfinqa/${var.account_name}/database_url" },
      { name = "COGNITO_USER_POOL_ID", valueFrom = "/convfinqa/${var.account_name}/cognito_user_pool_id" },
      { name = "COGNITO_CLIENT_ID", valueFrom = "/convfinqa/${var.account_name}/cognito_client_id" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
        "awslogs-region"        = data.aws_region.current.id
        "awslogs-stream-prefix" = "api"
      }
    }
  }])

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_ecs_service" "api" {
  name            = "convfinqa-${var.account_name}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [var.ecs_sg_id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

# ── ALB ───────────────────────────────────────────────────────────────────────

resource "aws_security_group" "alb" {
  name        = "convfinqa-${var.account_name}-alb"
  description = "ALB SG: ingress HTTP from CloudFront origin-facing prefix list"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTP from CloudFront"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_security_group_rule" "ecs_from_alb" {
  type                     = "ingress"
  description              = "Allow HTTP from ALB"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  security_group_id        = var.ecs_sg_id
  source_security_group_id = aws_security_group.alb.id
}

resource "aws_lb" "main" {
  name               = "convfinqa-${var.account_name}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  idle_timeout = 300

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_lb_target_group" "api" {
  name        = "convfinqa-${var.account_name}-api"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/api/v1/healthz"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

# ── BFF Lambda functions ──────────────────────────────────────────────────────

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

resource "aws_lambda_function" "bff_login" {
  function_name    = "convfinqa-${var.account_name}-bff-login"
  role             = aws_iam_role.bff_lambda.arn
  handler          = "login.handler"
  runtime          = "nodejs22.x"
  filename         = "${path.module}/login.zip"
  source_code_hash = filebase64sha256("${path.module}/login.zip")
  timeout          = 10
  memory_size      = 128

  environment {
    variables = local.bff_common_env
  }

  depends_on = [aws_cloudwatch_log_group.bff_login]

  lifecycle {
    ignore_changes = [source_code_hash, filename]
  }

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
  filename         = "${path.module}/callback.zip"
  source_code_hash = filebase64sha256("${path.module}/callback.zip")
  timeout          = 15
  memory_size      = 128

  environment {
    variables = merge(local.bff_common_env, {
      DATABASE_URL = var.database_url
    })
  }

  depends_on = [aws_cloudwatch_log_group.bff_callback]

  lifecycle {
    ignore_changes = [source_code_hash, filename]
  }

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
  filename         = "${path.module}/refresh.zip"
  source_code_hash = filebase64sha256("${path.module}/refresh.zip")
  timeout          = 10
  memory_size      = 128

  environment {
    variables = local.bff_common_env
  }

  depends_on = [aws_cloudwatch_log_group.bff_refresh]

  lifecycle {
    ignore_changes = [source_code_hash, filename]
  }

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
  filename         = "${path.module}/logout.zip"
  source_code_hash = filebase64sha256("${path.module}/logout.zip")
  timeout          = 10
  memory_size      = 128

  environment {
    variables = local.bff_common_env
  }

  depends_on = [aws_cloudwatch_log_group.bff_logout]

  lifecycle {
    ignore_changes = [source_code_hash, filename]
  }

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
  filename         = "${path.module}/post_confirmation.zip"
  source_code_hash = filebase64sha256("${path.module}/post_confirmation.zip")
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      DATABASE_URL = var.database_url
    }
  }

  depends_on = [aws_cloudwatch_log_group.bff_post_confirmation]

  lifecycle {
    ignore_changes = [source_code_hash, filename]
  }

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
