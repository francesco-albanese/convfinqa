output "github_actions_deploy_role_arn" {
  description = "Set as AWS_ROLE_ARN secret in the GitHub sandbox Environment"
  value       = aws_iam_role.github_actions_deploy.arn
}

output "ecr_registry" {
  description = "ECR repository URL — set as ECR_REGISTRY GitHub Actions variable"
  value       = module.compute.repository_url
}

output "ecs_cluster" {
  description = "ECS cluster name — set as ECS_CLUSTER GitHub Actions variable"
  value       = module.compute.ecs_cluster_name
}

output "ecs_service" {
  description = "ECS service name — set as ECS_SERVICE GitHub Actions variable"
  value       = module.compute.ecs_service_name
}

output "ecs_task_family" {
  description = "ECS task definition family — set as ECS_TASK_FAMILY GitHub Actions variable"
  value       = module.compute.ecs_task_family
}

output "ecs_sg_id" {
  description = "ECS task security group ID — set as ECS_SG_ID GitHub Actions variable"
  value       = module.network.ecs_sg_id
}

output "public_subnet_ids" {
  description = "Comma-separated public subnet IDs — set as PUBLIC_SUBNET_IDS GitHub Actions variable"
  value       = join(",", module.network.public_subnet_ids)
}

output "bff_function_prefix" {
  description = "BFF Lambda function name prefix — set as BFF_FUNCTION_PREFIX GitHub Actions variable"
  value       = module.compute.bff_function_prefix
}

output "s3_bucket" {
  description = "S3 site bucket name — set as S3_BUCKET GitHub Actions variable"
  value       = module.edge.bucket_id
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID — set as CLOUDFRONT_DISTRIBUTION_ID GitHub Actions variable"
  value       = module.edge.cloudfront_distribution_id
}
