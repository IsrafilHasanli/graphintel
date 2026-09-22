# GraphIntel AWS Deployment Plan

## Goal

Deploy GraphIntel to AWS in a production-friendly way while keeping the local
developer experience simple and reproducible.

## Local Development

The local stack should run with Docker Compose:

- `web`
- `api`
- `postgres`
- `redis`

Local development may support deterministic behavior for tests, but AWS
production/staging must use real providers and managed services.

## AWS Target Architecture

| Component | AWS Service |
| --- | --- |
| Frontend | ECS Fargate service behind ALB, or S3/CloudFront if exported static |
| API | ECS Fargate service behind ALB |
| Worker | ECS Fargate service without public ingress |
| Relational DB | RDS PostgreSQL |
| Vector Search | pgvector in PostgreSQL or another real vector backend |
| Graph Database | Amazon Neptune |
| Job Queue | ElastiCache Redis |
| Raw Files | S3 |
| Container Registry | ECR |
| Secrets | Secrets Manager or SSM Parameter Store |
| Logs/Metrics | CloudWatch |
| TLS | ACM certificate on ALB |

## No-Mock Production Rule

AWS production/staging must not use:

- SQLite
- in-memory graph storage
- deterministic mock LLM
- hash/deterministic embeddings
- local filesystem object storage
- local Redis substitutes

AWS production/staging must use:

- Amazon Neptune for graph database and graph traversal
- RDS PostgreSQL for relational data
- pgvector or another real vector backend for vector search
- a real LLM provider for answer generation
- a real embedding provider for embeddings
- ElastiCache Redis
- S3

## Required AWS Runtime Configuration

- `GRAPH_BACKEND=neptune`
- `NEPTUNE_ENDPOINT=<terraform neptune_endpoint output>`
- `NEPTUNE_PORT=8182`
- `NEPTUNE_USE_IAM_AUTH=true`
- `LLM_PROVIDER=anthropic`
- `EXTRACTION_PROVIDER=llm`
- `EMBEDDING_PROVIDER=bedrock` or `voyage`
- `DATABASE_URL` from Secrets Manager, pointing to RDS PostgreSQL
- `ANTHROPIC_API_KEY` from Secrets Manager
- `VOYAGE_API_KEY` from Secrets Manager only when Voyage is selected

## Infrastructure-As-Code

Use one of:

- Terraform in `infra/terraform`
- AWS CDK in `infra/aws-cdk`

Terraform is preferred for broad portability unless the implementation team
chooses CDK explicitly.

## Required Deployment Files

- `docker-compose.yml`
- `.env.example`
- service Dockerfiles
- `infra/terraform/README.md`
- `deploy/aws/README.md`
- CI workflow
- deploy workflow

## Deployment Stages

1. Build local Docker images.
2. Run local stack and seed demo data.
3. Run tests.
4. Create AWS infrastructure.
5. Push images to ECR.
6. Deploy ECS services.
7. Run database migrations.
8. Seed optional demo data in staging.
9. Run smoke tests.
10. Configure alarms and log retention.

## Required Smoke Tests

- API health endpoint returns OK.
- Frontend loads.
- Database connectivity works.
- Neptune connectivity works.
- Worker can process a small job.
- Demo question returns cited answer in staging when seed data exists.

## Security And Secrets

- Never commit real API keys.
- Store secrets in AWS Secrets Manager or SSM Parameter Store.
- Use least-privilege task roles.
- Keep RDS and Redis private.
- Use TLS for public endpoints.
- Restrict CORS to known frontend domains.

## Rollback

Rollback must include:

- Revert ECS task definition to previous version.
- Keep previous ECR image tags.
- Avoid destructive database migrations without backup.
- Document restore path for RDS snapshots.

## Cleanup

Non-production environments must include cleanup commands for:

- ECS services
- ECR images
- ALB
- RDS
- Redis
- S3 demo buckets
- CloudWatch log groups
