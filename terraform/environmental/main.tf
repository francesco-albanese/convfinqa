module "network" {
  source = "./modules/network"
}

module "data" {
  source = "./modules/data"
}

module "edge" {
  source = "./modules/edge"

  providers = {
    aws                 = aws
    aws.shared_services = aws.shared_services
  }
}

module "compute" {
  source = "./modules/compute"

  cognito_hosted_ui_prefix = var.cognito_hosted_ui_prefix
}

module "keepalive" {
  source = "./modules/keepalive"
}
