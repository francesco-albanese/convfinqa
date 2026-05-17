resource "aws_security_group" "lambda" {
  name        = "convfinqa-${var.account_name}-keepalive"
  description = "Keepalive Lambda SG: egress to Aurora on port 5432 only"
  vpc_id      = var.vpc_id

  egress {
    description     = "Postgres to Aurora"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.aurora_sg_id]
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-keepalive"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_security_group_rule" "aurora_from_keepalive" {
  type                     = "ingress"
  description              = "Allow Postgres from keepalive Lambda"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = var.aurora_sg_id
  source_security_group_id = aws_security_group.lambda.id
}

resource "aws_iam_role" "lambda" {
  name = "convfinqa-${var.account_name}-keepalive"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    "franco:terraform_stack" = "convfinqa-keepalive"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/convfinqa-${var.account_name}-keepalive"
  retention_in_days = 7

  tags = {
    "franco:terraform_stack" = "convfinqa-keepalive"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

data "aws_region" "current" {}

resource "aws_ecr_repository" "keepalive" {
  name                 = "convfinqa-${var.account_name}-keepalive"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-keepalive"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_ecr_lifecycle_policy" "keepalive" {
  repository = aws_ecr_repository.keepalive.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Retain last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

resource "null_resource" "keepalive_image" {
  depends_on = [aws_ecr_repository.keepalive]

  triggers = {
    handler    = filemd5("${path.module}/handler.py")
    pyproject  = filemd5("${path.module}/pyproject.toml")
    dockerfile = filemd5("${path.module}/Dockerfile")
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      unset AWS_PROFILE
      REPO="${aws_ecr_repository.keepalive.repository_url}"
      REGION="${data.aws_region.current.name}"
      aws ecr get-login-password --region "$REGION" | \
        docker login --username AWS --password-stdin "$(echo "$REPO" | cut -d/ -f1)"
      docker build --platform linux/amd64 -t keepalive:local -t "$REPO:latest" "${abspath(path.module)}"
      docker push "$REPO:latest"
    EOT
  }
}

resource "aws_lambda_function" "keepalive" {
  function_name = "convfinqa-${var.account_name}-keepalive"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.keepalive.repository_url}:latest"
  timeout       = 60
  memory_size   = 128

  lifecycle {
    replace_triggered_by = [null_resource.keepalive_image]
  }

  vpc_config {
    subnet_ids         = var.public_subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DATABASE_URL = var.database_url
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda, null_resource.keepalive_image]

  tags = {
    "franco:terraform_stack" = "convfinqa-keepalive"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_cloudwatch_event_rule" "keepalive" {
  name                = "convfinqa-${var.account_name}-keepalive"
  description         = "Aurora keepalive ping every 12h"
  schedule_expression = "rate(12 hours)"

  tags = {
    "franco:terraform_stack" = "convfinqa-keepalive"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_cloudwatch_event_target" "keepalive" {
  rule      = aws_cloudwatch_event_rule.keepalive.name
  target_id = "keepalive"
  arn       = aws_lambda_function.keepalive.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.keepalive.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.keepalive.arn
}
