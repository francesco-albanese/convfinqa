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
  parent_zone_name = var.parent_zone_name

  bff_login_url    = module.compute.bff_login_url
  bff_callback_url = module.compute.bff_callback_url
  bff_refresh_url  = module.compute.bff_refresh_url
  bff_logout_url   = module.compute.bff_logout_url
  alb_dns_name     = module.compute.alb_dns_name

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
  vpc_id                   = module.network.vpc_id
  database_url             = module.data.database_url
  langfuse_public_key      = var.langfuse_public_key
  langfuse_secret_key      = var.langfuse_secret_key
}

module "keepalive" {
  source = "./modules/keepalive"

  vpc_id            = module.network.vpc_id
  public_subnet_ids = module.network.public_subnet_ids
  aurora_sg_id      = module.network.aurora_sg_id
  account_name      = var.account_name
  database_url      = module.data.database_url
}
