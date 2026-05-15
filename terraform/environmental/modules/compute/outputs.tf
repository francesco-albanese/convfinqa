output "repository_url" {
  description = "ECR repository URL for the FastAPI image."
  value       = aws_ecr_repository.app.repository_url
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID."
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_arn" {
  description = "Cognito User Pool ARN."
  value       = aws_cognito_user_pool.main.arn
}

output "cognito_client_id" {
  description = "Cognito app client ID."
  value       = aws_cognito_user_pool_client.app.id
}

output "cognito_hosted_ui_base_url" {
  description = "Cognito hosted UI base URL (https://<prefix>.auth.<region>.amazoncognito.com)."
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${data.aws_region.current.id}.amazoncognito.com"
}

output "ssm_read_policy_arn" {
  description = "ARN of the IAM policy granting read access to all /convfinqa/{env}/* SSM parameters."
  value       = aws_iam_policy.ssm_read.arn
}
