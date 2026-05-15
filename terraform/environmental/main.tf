module "network" {
  source = "./modules/network"
}

module "data" {
  source = "./modules/data"

  public_subnet_ids = module.network.public_subnet_ids
  aurora_sg_id      = module.network.aurora_sg_id
  account_name      = var.account_name
}

module "edge" {
  source = "./modules/edge"

  app_domain       = var.app_domain
  apex_domain      = var.apex_domain
  parent_zone_name = var.parent_zone_name

  providers = {
    aws                 = aws
    aws.shared_services = aws.shared_services
    aws.us_east_1       = aws.us_east_1
  }
}

module "compute" {
  source = "./modules/compute"

  account_name             = var.account_name
  app_domain               = var.app_domain
  cognito_hosted_ui_prefix = var.cognito_hosted_ui_prefix
  public_subnet_ids        = module.network.public_subnet_ids
  ecs_sg_id                = module.network.ecs_sg_id
}

module "keepalive" {
  source = "./modules/keepalive"
}
