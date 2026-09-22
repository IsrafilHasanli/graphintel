output "api_url" {
  description = "Public base URL for the GraphIntel API (HTTP; front with HTTPS/ACM for prod)."
  value       = "http://${aws_lb.main.dns_name}"
}

output "web_url" {
  description = "Public base URL for the GraphIntel frontend."
  value       = "http://${aws_lb.web.dns_name}"
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "ecr_api_repository_url" {
  description = "Push API images here (used by CI)."
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_web_repository_url" {
  value = aws_ecr_repository.web.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_api_service_name" {
  value = aws_ecs_service.api.name
}

output "ecs_web_service_name" {
  value = aws_ecs_service.web.name
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "neptune_endpoint" {
  value = aws_neptune_cluster.main.endpoint
}

output "neptune_reader_endpoint" {
  value = aws_neptune_cluster.main.reader_endpoint
}

output "documents_bucket" {
  value = aws_s3_bucket.documents.bucket
}

output "database_url_secret_arn" {
  description = "Secrets Manager ARN holding the DATABASE_URL DSN."
  value       = aws_secretsmanager_secret.database_url.arn
}
