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

  statement {
    sid    = "ConvfinqaInfraServices"
    effect = "Allow"
    actions = [
      "ec2:*",
      "ecs:*",
      "ecr:*",
      "rds:*",
      "cognito-idp:*",
      "s3:*",
      "cloudfront:*",
      "route53:*",
      "acm:*",
      "lambda:*",
      "events:*",
      "logs:*",
      "ssm:*",
      "elasticloadbalancing:*",
      "kms:Describe*",
      "kms:Get*",
      "kms:List*",
      "sts:GetCallerIdentity",
      "tag:GetResources",
      "tag:GetTagKeys",
      "tag:GetTagValues",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageConvfinqaRoles"
    effect = "Allow"
    actions = [
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:CreateRole",
      "iam:UpdateRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:DeleteRole",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:ListRolePolicies",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
    ]
    resources = ["arn:aws:iam::${var.account_id}:role/convfinqa-*"]
  }

  statement {
    sid    = "ManageConvfinqaPolicies"
    effect = "Allow"
    actions = [
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:CreatePolicy",
      "iam:CreatePolicyVersion",
      "iam:DeletePolicy",
      "iam:DeletePolicyVersion",
      "iam:ListPolicyVersions",
      "iam:TagPolicy",
      "iam:UntagPolicy",
    ]
    resources = ["arn:aws:iam::${var.account_id}:policy/convfinqa-*"]
  }

  statement {
    sid    = "IAMReadForPlanRefresh"
    effect = "Allow"
    actions = [
      "iam:ListRoles",
      "iam:ListPolicies",
      "iam:GetOpenIDConnectProvider",
      "iam:ListOpenIDConnectProviders",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "PassConvfinqaRolesToServices"
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = ["arn:aws:iam::${var.account_id}:role/convfinqa-*"]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values = [
        "lambda.amazonaws.com",
        "ecs-tasks.amazonaws.com",
        "events.amazonaws.com",
        "cognito-idp.amazonaws.com",
        "rds.amazonaws.com",
        "scheduler.amazonaws.com",
      ]
    }
  }

  statement {
    sid       = "CreateServiceLinkedRoleForRDS"
    effect    = "Allow"
    actions   = ["iam:CreateServiceLinkedRole"]
    resources = ["arn:aws:iam::${var.account_id}:role/aws-service-role/rds.amazonaws.com/AWSServiceRoleForRDS"]
  }
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name   = "github-actions-deploy"
  role   = aws_iam_role.github_actions_deploy.id
  policy = data.aws_iam_policy_document.github_actions_deploy.json
}
