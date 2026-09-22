terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.40"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.6"
    }
  }

  # Remote state is recommended for real deployments. Kept commented so the
  # config validates offline with no backend/credentials. Copy to backend.tf
  # and fill in a bucket + DynamoDB lock table when you actually deploy.
  # backend "s3" {
  #   bucket         = "graphintel-tfstate"
  #   key            = "graphintel/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "graphintel-tflock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "GraphIntel"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
