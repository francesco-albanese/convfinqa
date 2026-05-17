data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ec2_managed_prefix_list" "cloudfront_origin_facing" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

locals {
  az_names = slice(data.aws_availability_zones.available.names, 0, 2)
  vpc_cidr = "10.0.0.0/16"
}

resource "aws_vpc" "main" {
  cidr_block           = local.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "convfinqa"
  }
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(local.vpc_cidr, 8, count.index)
  availability_zone = local.az_names[count.index]

  tags = {
    Name = "convfinqa-public-${count.index}"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "convfinqa"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "convfinqa-public"
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "ecs_task" {
  name        = "convfinqa-ecs-task"
  description = "ECS task SG: ingress from CloudFront origin-facing prefix list on port 8000"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "convfinqa-ecs-task"
  }
}

resource "aws_security_group_rule" "ecs_task_from_cloudfront" {
  type              = "ingress"
  description       = "HTTP from CloudFront origin-facing"
  from_port         = 8000
  to_port           = 8000
  protocol          = "tcp"
  security_group_id = aws_security_group.ecs_task.id
  prefix_list_ids   = [data.aws_ec2_managed_prefix_list.cloudfront_origin_facing.id]
}

resource "aws_security_group" "aurora" {
  name        = "convfinqa-aurora"
  description = "Aurora SG: ingress from ECS task SG and public internet (BFF Lambda) on port 5432"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "convfinqa-aurora"
  }
}

resource "aws_security_group_rule" "aurora_from_ecs_task" {
  type                     = "ingress"
  description              = "Postgres from ECS task"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.aurora.id
  source_security_group_id = aws_security_group.ecs_task.id
}

# BFF Lambda (callback, post_confirmation) runs without VPC config to avoid NAT Gateway.
# 32-char random password is the auth boundary. Demo-grade: acceptable for this deployment.
resource "aws_security_group_rule" "aurora_from_public" {
  type              = "ingress"
  description       = "Postgres from BFF Lambda (no-VPC, public internet)"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  security_group_id = aws_security_group.aurora.id
  cidr_blocks       = ["0.0.0.0/0"]
}
