resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name}-redis-subnets"
  subnet_ids = aws_subnet.private[*].id
}

# Redis broker for Celery/RQ background ingestion jobs.
resource "aws_elasticache_cluster" "main" {
  cluster_id           = "${local.name}-redis"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  port                 = 6379
  parameter_group_name = "default.redis7"
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.data.id]

  tags = { Name = "${local.name}-redis" }
}
