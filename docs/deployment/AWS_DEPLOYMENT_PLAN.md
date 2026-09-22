# AWS Deployment Plan

This document describes the intended AWS deployment model for GraphIntel. Local
development remains offline and reproducible; staging and production should use
managed AWS services and real model providers.

## Target Architecture

| Component | AWS service |
| --- | --- |
| Frontend | ECS Fargate service behind ALB |
| API | ECS Fargate service behind ALB |
| Relational database | RDS PostgreSQL |
| Graph database | Amazon Neptune |
| Cache / job coordination | ElastiCache Redis |
| Raw documents | S3 |
| Container registry | ECR |
| Secrets | AWS Secrets Manager |
| Logs and metrics | CloudWatch |
| TLS | ACM certificate on ALB |

## Runtime Requirements

Production and staging must not use local-only substitutes:

- no SQLite
- no SQL graph backend
- no deterministic LLM provider
- no deterministic embeddings
- no wildcard CORS
- no local filesystem document storage

Required environment configuration:

| Variable | Requirement |
| --- | --- |
| `GRAPHINTEL_ENV` | `staging` or `production` |
| `DATABASE_URL` | RDS PostgreSQL DSN from Secrets Manager |
| `GRAPH_BACKEND` | `neptune` |
| `NEPTUNE_ENDPOINT` | Terraform Neptune endpoint output |
| `NEPTUNE_PORT` | `8182` unless the cluster uses a different port |
| `LLM_PROVIDER` | real provider, for example `anthropic` |
| `EXTRACTION_PROVIDER` | `llm` |
| `EMBEDDING_PROVIDER` | `bedrock`, `fastembed`, or `voyage` |
| `CORS_ALLOW_ORIGINS` | explicit frontend origin list |

## Infrastructure

Terraform assets live in `infra/terraform` and provision:

- VPC, public/private subnets, routing, and security groups
- ECR repositories
- RDS PostgreSQL with pgvector support
- Amazon Neptune cluster and instances
- ElastiCache Redis
- S3 document bucket
- Secrets Manager secrets
- ALB and target groups
- ECS cluster, task definition, and service
- CloudWatch log group
- IAM roles and policies

See [infra/README.md](../../infra/README.md) for the operational runbook.

## Deployment Flow

1. Run tests and builds locally or in CI.
2. Validate Terraform formatting and provider schema.
3. Apply Terraform to create infrastructure.
4. Build API and web images.
5. Push images to ECR.
6. Roll out ECS task definitions.
7. Run smoke tests against the deployed API.
8. Configure DNS, TLS, alarms, and dashboards.

## CI/CD

The deploy workflow is intentionally gated. Without repository variables such as
`AWS_DEPLOY_ROLE_ARN`, it exits without touching AWS. When configured, it uses
GitHub OIDC to assume a deploy role, pushes images, updates ECS, waits for
service stability, and runs the smoke test.

## Smoke Tests

Minimum post-deploy checks:

- `GET /health` returns `ok`.
- `GET /ready` returns `ready` with no production safety errors.
- API can reach RDS.
- API can reach Neptune.
- Seeded demo question returns a cited answer in staging.
- Frontend loads and can call the API.

## Security

- Store credentials only in Secrets Manager or equivalent secret storage.
- Use least-privilege task and execution roles.
- Keep RDS, Neptune, and Redis in private subnets.
- Allow ingress to private services only from application security groups.
- Use HTTPS for public traffic.
- Restrict CORS to known frontend domains.
- Keep Terraform state in a secure remote backend for team environments.

## Rollback

Rollback should use ECS task-definition revisions and retained ECR image tags.
Avoid destructive migrations without snapshots. RDS and Neptune backups should
be enabled before production launch.

## Teardown

Non-production environments should document teardown steps and expected costs.
Neptune, NAT gateways, ALB, and RDS are the primary always-on cost drivers.
