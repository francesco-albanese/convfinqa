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
  count = var.system_prompt_override != "" ? 1 : 0

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
