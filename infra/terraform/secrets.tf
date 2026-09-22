# Database master password is generated, never hard-coded, and only ever lives
# in Secrets Manager. The API reads it at task start via the ECS secrets block.
resource "random_password" "db" {
  length  = 24
  special = false
}

resource "aws_secretsmanager_secret" "db_password" {
  name        = "${local.name}/db-password"
  description = "GraphIntel RDS master password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db.result
}

# Full SQLAlchemy DSN assembled from the RDS endpoint + generated password.
# Injected into the API as DATABASE_URL so no credentials appear in the task def.
resource "aws_secretsmanager_secret" "database_url" {
  name        = "${local.name}/database-url"
  description = "GraphIntel DATABASE_URL (postgresql+psycopg DSN)"
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = format(
    "postgresql+psycopg://%s:%s@%s:%s/%s",
    var.db_username,
    random_password.db.result,
    aws_db_instance.main.address,
    aws_db_instance.main.port,
    var.db_name,
  )
}

resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name        = "${local.name}/anthropic-api-key"
  description = "Anthropic API key for real LLM generation/extraction"
}

resource "aws_secretsmanager_secret" "voyage_api_key" {
  name        = "${local.name}/voyage-api-key"
  description = "Voyage API key when EMBEDDING_PROVIDER=voyage"
}
