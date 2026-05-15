output "lambda_function_arn" {
  description = "ARN of the keepalive Lambda function"
  value       = aws_lambda_function.keepalive.arn
}
