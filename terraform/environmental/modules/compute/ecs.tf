resource "aws_ecs_cluster" "main" {
  name = "convfinqa-${var.account_name}"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/convfinqa-${var.account_name}"
  retention_in_days = 7

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_iam_role" "ecs_task" {
  name = "convfinqa-${var.account_name}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_ssm" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ssm_read.arn
}

resource "aws_iam_role_policy_attachment" "ecs_task_cloudwatch_agent" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy" "ecs_task_bedrock" {
  name = "bedrock-invoke"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
      ]
      Resource = [
        "arn:aws:bedrock:eu-*::foundation-model/*",
        "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/eu.*",
      ]
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_exec" {
  name = "ecs-exec"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel",
      ]
      Resource = "*"
    }]
  })
}

resource "aws_iam_role" "ecs_execution" {
  name = "convfinqa-${var.account_name}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "ecs_execution_ssm" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = aws_iam_policy.ssm_read.arn
}

resource "aws_ecs_task_definition" "api" {
  family                   = "convfinqa-${var.account_name}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  task_role_arn            = aws_iam_role.ecs_task.arn
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
      essential = true

      portMappings = [{ containerPort = 8000, protocol = "tcp" }]

      environment = [
        { name = "API_HOST", value = "0.0.0.0" },
        { name = "API_PORT", value = "8000" },
        { name = "COGNITO_REGION", value = data.aws_region.current.id },
        { name = "LANGFUSE_ENABLED", value = "true" },
        { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = "http://localhost:4318/v1/traces" },
        { name = "OTEL_SERVICE_NAME", value = "convfinqa" },
        { name = "OTEL_RESOURCE_ATTRIBUTES", value = "service.namespace=convfinqa,environment=${var.account_name},aws.log.group.names=${aws_cloudwatch_log_group.ecs.name}" },
      ]

      secrets = [
        { name = "DATABASE_URL", valueFrom = "/convfinqa/${var.account_name}/database_url" },
        { name = "COGNITO_USER_POOL_ID", valueFrom = "/convfinqa/${var.account_name}/cognito_user_pool_id" },
        { name = "COGNITO_CLIENT_ID", valueFrom = "/convfinqa/${var.account_name}/cognito_client_id" },
        { name = "LANGFUSE_PUBLIC_KEY", valueFrom = "/convfinqa/${var.account_name}/langfuse_public_key" },
        { name = "LANGFUSE_SECRET_KEY", valueFrom = "/convfinqa/${var.account_name}/langfuse_secret_key" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.id
          "awslogs-stream-prefix" = "api"
        }
      }
    },
    {
      name              = "cloudwatch-agent"
      image             = var.cloudwatch_agent_image
      essential         = true
      memory            = 64
      memoryReservation = 32

      environment = [
        { name = "CW_CONFIG_CONTENT", value = jsonencode(local.cloudwatch_agent_config) },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.id
          "awslogs-stream-prefix" = "cloudwatch-agent"
        }
      }
    },
  ])

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_ecs_service" "api" {
  name                   = "convfinqa-${var.account_name}-api"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.api.arn
  desired_count          = 1
  enable_execute_command = true

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [var.ecs_sg_id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_security_group" "alb" {
  name        = "convfinqa-${var.account_name}-alb"
  description = "ALB SG: ingress HTTP from CloudFront origin-facing prefix list"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTP from CloudFront"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_security_group_rule" "ecs_from_alb" {
  type                     = "ingress"
  description              = "Allow HTTP from ALB"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  security_group_id        = var.ecs_sg_id
  source_security_group_id = aws_security_group.alb.id
}

resource "aws_lb" "main" {
  name               = "convfinqa-${var.account_name}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  idle_timeout = 300

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_lb_target_group" "api" {
  name        = "convfinqa-${var.account_name}-api"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/healthz"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  tags = {
    "franco:terraform_stack" = "convfinqa-compute"
    "franco:environment"     = var.account_name
    "franco:managed_by"      = "terraform"
  }
}
