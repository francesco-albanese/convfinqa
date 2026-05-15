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
