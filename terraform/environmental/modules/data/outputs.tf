output "cluster_endpoint" {
  description = "Writer endpoint of the Aurora cluster"
  value       = aws_rds_cluster.main.endpoint
}

output "cluster_reader_endpoint" {
  description = "Reader endpoint of the Aurora cluster"
  value       = aws_rds_cluster.main.reader_endpoint
}

output "database_url_ssm_name" {
  description = "SSM parameter name storing the database URL (SecureString)"
  value       = aws_ssm_parameter.database_url.name
}

output "database_url" {
  description = "Plain postgresql:// URL for keepalive Lambda (pg8000 format, no driver prefix)"
  value       = "postgresql://convfinqa:${random_password.db.result}@${aws_rds_cluster.main.endpoint}:5432/convfinqa"
  sensitive   = true
}
