resource "aws_ecs_cluster" "main" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

locals {
  api_image = "${aws_ecr_repository.api.repository_url}:${var.api_image_tag}"

  api_environment = [
    { name = "GRAPHINTEL_ENV", value = var.environment },
    { name = "LOG_LEVEL", value = "INFO" },
    { name = "GRAPH_BACKEND", value = "neptune" },
    { name = "NEPTUNE_ENDPOINT", value = aws_neptune_cluster.main.endpoint },
    { name = "NEPTUNE_PORT", value = tostring(aws_neptune_cluster.main.port) },
    { name = "NEPTUNE_USE_IAM_AUTH", value = "true" },
    { name = "EMBEDDING_PROVIDER", value = var.embedding_provider },
    { name = "FASTEMBED_EMBEDDING_MODEL", value = var.fastembed_embedding_model },
    { name = "BEDROCK_EMBEDDING_MODEL", value = var.bedrock_embedding_model },
    { name = "LLM_PROVIDER", value = var.llm_provider },
    { name = "EXTRACTION_PROVIDER", value = var.extraction_provider },
    { name = "AWS_REGION", value = var.aws_region },
    { name = "REDIS_URL", value = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:6379/0" },
  ]

  api_secrets = [
    { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.database_url.arn },
    { name = "ANTHROPIC_API_KEY", valueFrom = aws_secretsmanager_secret.anthropic_api_key.arn },
    { name = "VOYAGE_API_KEY", valueFrom = aws_secretsmanager_secret.voyage_api_key.arn },
  ]
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name        = "api"
      image       = local.api_image
      essential   = true
      environment = local.api_environment
      secrets     = local.api_secrets

      portMappings = [{
        containerPort = var.api_container_port
        protocol      = "tcp"
      }]

      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:${var.api_container_port}/health').status==200 else 1)\""]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 20
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "api" {
  name            = "${local.name}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  # Rolling deploy with circuit breaker so a bad image auto-rolls back.
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = var.api_container_port
  }

  # CI updates the task definition out-of-band (new image tag); ignore the
  # desired_count so autoscaling (if added) doesn't fight Terraform.
  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_lb_listener.http]
}
