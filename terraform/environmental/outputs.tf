output "github_actions_deploy_role_arn" {
  description = "Set as AWS_ROLE_ARN secret in the GitHub sandbox Environment"
  value       = aws_iam_role.github_actions_deploy.arn
}
