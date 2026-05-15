output "bucket_id" {
  description = "ID (name) of the S3 site bucket"
  value       = aws_s3_bucket.site.id
}

output "bucket_arn" {
  description = "ARN of the S3 site bucket"
  value       = aws_s3_bucket.site.arn
}

output "bucket_regional_domain_name" {
  description = "Regional domain name of the S3 site bucket (used as CloudFront S3 origin to avoid 307 redirects)"
  value       = aws_s3_bucket.site.bucket_regional_domain_name
}

output "oac_id" {
  description = "ID of the CloudFront Origin Access Control"
  value       = aws_cloudfront_origin_access_control.site.id
}
