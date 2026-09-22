resource "aws_neptune_subnet_group" "main" {
  name       = "${local.name}-neptune-subnets"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${local.name}-neptune-subnets" }
}

resource "aws_neptune_cluster" "main" {
  cluster_identifier                  = "${local.name}-graph"
  engine                              = "neptune"
  iam_database_authentication_enabled = true
  storage_encrypted                   = true
  neptune_subnet_group_name           = aws_neptune_subnet_group.main.name
  vpc_security_group_ids              = [aws_security_group.data.id]
  backup_retention_period             = 7
  preferred_backup_window             = "02:00-03:00"
  preferred_maintenance_window        = "sun:03:00-sun:04:00"
  skip_final_snapshot                 = var.environment != "prod"
  deletion_protection                 = var.environment == "prod"

  tags = { Name = "${local.name}-graph" }
}

resource "aws_neptune_cluster_instance" "main" {
  count              = var.environment == "prod" ? 2 : 1
  identifier         = "${local.name}-graph-${count.index}"
  cluster_identifier = aws_neptune_cluster.main.id
  instance_class     = var.neptune_instance_class
  engine             = aws_neptune_cluster.main.engine

  tags = { Name = "${local.name}-graph-${count.index}" }
}
