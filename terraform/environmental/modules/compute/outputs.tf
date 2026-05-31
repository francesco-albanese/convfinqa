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

output "e2e_email_ssm_name" {
  description = "SSM parameter name containing the non-production e2e email, or null in production."
  value       = try(one(aws_ssm_parameter.e2e_email[*].name), null)
}

output "e2e_password_ssm_name" {
  description = "SSM SecureString parameter name containing the non-production e2e password, or null in production."
  value       = try(one(aws_ssm_parameter.e2e_password[*].name), null)
}

output "ssm_read_policy_arn" {
  description = "ARN of the IAM policy granting read access to all /convfinqa/{env}/* SSM parameters."
  value       = aws_iam_policy.ssm_read.arn
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN."
  value       = aws_ecs_cluster.main.arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role (runtime permissions)."
  value       = aws_iam_role.ecs_task.arn
}

output "ecs_execution_role_arn" {
  description = "ARN of the ECS task execution role."
  value       = aws_iam_role.ecs_execution.arn
}

output "ecs_service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.api.name
}

output "alb_dns_name" {
  description = "ALB DNS name (used as CloudFront /api/v1/* origin)."
  value       = aws_lb.main.dns_name
}

output "alb_arn_suffix" {
  description = "ALB ARN suffix for CloudWatch metrics."
  value       = aws_lb.main.arn_suffix
}

output "bff_login_url" {
  description = "Lambda Function URL for /api/auth/login."
  value       = aws_lambda_function_url.bff_login.function_url
}

output "bff_callback_url" {
  description = "Lambda Function URL for /api/auth/callback."
  value       = aws_lambda_function_url.bff_callback.function_url
}

output "bff_refresh_url" {
  description = "Lambda Function URL for /api/auth/refresh."
  value       = aws_lambda_function_url.bff_refresh.function_url
}

output "bff_logout_url" {
  description = "Lambda Function URL for /api/auth/logout."
  value       = aws_lambda_function_url.bff_logout.function_url
}

output "ecs_task_family" {
  description = "ECS task definition family name."
  value       = aws_ecs_task_definition.api.family
}

output "bff_function_prefix" {
  description = "Common prefix for all BFF Lambda function names (append -login, -callback, etc.)."
  value       = "convfinqa-${var.account_name}-bff"
}
