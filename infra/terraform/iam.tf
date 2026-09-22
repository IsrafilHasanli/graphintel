data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Execution role: used by the ECS agent to pull images, write logs, and read
# the secrets referenced in the task definition.
resource "aws_iam_role" "task_execution" {
  name               = "${local.name}-task-exec"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "exec_secrets" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.database_url.arn,
      aws_secretsmanager_secret.anthropic_api_key.arn,
      aws_secretsmanager_secret.voyage_api_key.arn,
      aws_secretsmanager_secret.db_password.arn,
    ]
  }
}

resource "aws_iam_role_policy" "exec_secrets" {
  name   = "${local.name}-exec-secrets"
  role   = aws_iam_role.task_execution.id
  policy = data.aws_iam_policy_document.exec_secrets.json
}

# Task role: the permissions the running application itself has. Scoped to the
# documents bucket only.
resource "aws_iam_role" "task" {
  name               = "${local.name}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

data "aws_iam_policy_document" "task_s3" {
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:DeleteObject"]
    resources = [aws_s3_bucket.documents.arn, "${aws_s3_bucket.documents.arn}/*"]
  }
}

resource "aws_iam_role_policy" "task_s3" {
  name   = "${local.name}-task-s3"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task_s3.json
}

data "aws_iam_policy_document" "task_bedrock" {
  statement {
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "task_bedrock" {
  name   = "${local.name}-task-bedrock"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task_bedrock.json
}
