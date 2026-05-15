output "repository_url" {
  description = "ECR repository URL for the FastAPI image."
  value       = aws_ecr_repository.app.repository_url
}
