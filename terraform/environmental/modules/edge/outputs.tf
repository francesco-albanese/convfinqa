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

output "acm_certificate_arn" {
  description = "ARN of the validated ACM certificate (us-east-1, for CloudFront)"
  value       = aws_acm_certificate_validation.app.certificate_arn
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (used for cache invalidations in CI)"
  value       = aws_cloudfront_distribution.app.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (*.cloudfront.net)"
  value       = aws_cloudfront_distribution.app.domain_name
}
