resource "aws_iam_role" "github_actions_deploy" {
  name = "convfinqa-github-actions-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = local.github_oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = [
            "repo:francesco-albanese/convfinqa:environment:${var.account_name}",
          ]
        }
      }
    }]
  })

  tags = {
    Name = "convfinqa-github-actions-deploy"
  }
}

data "aws_iam_policy_document" "github_actions_deploy" {
  statement {
    sid       = "AssumeSharedServicesRole"
    effect    = "Allow"
    actions   = ["sts:AssumeRole"]
    resources = ["arn:aws:iam::${var.shared_services_account_id}:role/${var.shared_services_role_name}"]
  }
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name   = "github-actions-deploy"
  role   = aws_iam_role.github_actions_deploy.id
  policy = data.aws_iam_policy_document.github_actions_deploy.json
}
