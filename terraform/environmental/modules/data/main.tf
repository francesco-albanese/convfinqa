resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "main" {
  name       = "convfinqa-${var.account_name}"
  subnet_ids = var.public_subnet_ids

  tags = {
    "franco:terraform_stack" = "convfinqa-data"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_rds_cluster_parameter_group" "pg_cron" {
  name   = "convfinqa-${var.account_name}-aurora-pg16"
  family = "aurora-postgresql16"

  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_cron"
    apply_method = "pending-reboot"
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-data"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_rds_cluster" "main" {
  cluster_identifier              = "convfinqa-${var.account_name}"
  engine                          = "aurora-postgresql"
  engine_mode                     = "provisioned"
  engine_version                  = "16.11"
  database_name                   = "convfinqa"
  master_username                 = "convfinqa"
  master_password                 = random_password.db.result
  vpc_security_group_ids          = [var.aurora_sg_id]
  db_subnet_group_name            = aws_db_subnet_group.main.name
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.pg_cron.name
  skip_final_snapshot             = true
  apply_immediately               = true
  storage_encrypted               = true
  deletion_protection             = false

  serverlessv2_scaling_configuration {
    min_capacity = 0
    max_capacity = 2
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-data"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_rds_cluster_instance" "main" {
  cluster_identifier   = aws_rds_cluster.main.id
  identifier           = "convfinqa-${var.account_name}-instance-1"
  instance_class       = "db.serverless"
  engine               = aws_rds_cluster.main.engine
  engine_version       = aws_rds_cluster.main.engine_version
  db_subnet_group_name = aws_db_subnet_group.main.name
  apply_immediately    = true

  tags = {
    "franco:terraform_stack" = "convfinqa-data"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_ssm_parameter" "database_url" {
  name  = "/convfinqa/${var.account_name}/database_url"
  type  = "SecureString"
  value = "postgresql+asyncpg://convfinqa:${random_password.db.result}@${aws_rds_cluster.main.endpoint}:5432/convfinqa"

  tags = {
    "franco:terraform_stack" = "convfinqa-data"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}
