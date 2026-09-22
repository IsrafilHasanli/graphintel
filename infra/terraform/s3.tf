# Bucket for uploaded source documents and generated artifacts. Every stored
# object key is traceable back to an ingestion job / document id.
resource "aws_s3_bucket" "documents" {
  bucket        = "${local.name}-documents-${data.aws_caller_identity.current.account_id}"
  force_destroy = var.environment != "prod"
  tags          = { Name = "${local.name}-documents" }
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
