locals {
  adot_nodejs_layer_name    = "aws-otel-nodejs-amd64-ver-1-30-2"
  adot_nodejs_layer_version = 1
  adot_nodejs_layer_arn     = "arn:aws:lambda:${data.aws_region.current.id}:901920570463:layer:${local.adot_nodejs_layer_name}:${local.adot_nodejs_layer_version}"

  bff_adot_env = {
    AWS_LAMBDA_EXEC_WRAPPER = "/opt/otel-handler"
  }
}
