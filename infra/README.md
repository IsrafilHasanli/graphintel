# GraphIntel AWS Deployment

Infrastructure-as-code and CI/CD for running GraphIntel on AWS ECS Fargate
with Amazon Neptune as the production graph database.

> **Local development never requires AWS credentials.** Per the project
> constraint, these assets are implemented and documented but nothing here
> executes cloud changes unless you explicitly provide credentials and run
> `terraform apply` / configure the deploy workflow. Local development can run
> offline, but AWS staging/prod is intentionally real: RDS, Neptune,
> ElastiCache, S3, ECS, a real LLM provider, and real embeddings.

## Architecture

```
                    Internet
                       │  :80 (:443 w/ ACM)
                 ┌─────▼─────┐
                 │    ALB    │  (public subnets)
                 └─────┬─────┘
                       │  target group /health
             ┌─────────▼──────────┐
             │  ECS Fargate: api  │  (private subnets, N tasks)
             │  FastAPI :8000     │
             └───┬───────────┬────┘
        DATABASE_URL      REDIS_URL      NEPTUNE_ENDPOINT
        (Secrets Mgr)         │                │
             │                │                │
   ┌─────────▼──────┐  ┌──────▼───────┐  ┌─────▼──────┐   ┌──────────────┐
   │ RDS PostgreSQL │  │ ElastiCache  │  │  Neptune   │   │ S3 documents │
   │ 16 + pgvector  │  │ Redis (jobs) │  │ graph DB   │   │  (versioned) │
   └────────────────┘  └──────────────┘  └────────────┘   └──────────────┘

   Images: ECR (api, web)   Logs/metrics: CloudWatch + Container Insights
   Secrets: Secrets Manager (db password, DATABASE_URL, anthropic key)
```

Design notes:
- API tasks live in **private** subnets; only the ALB is public. RDS, Neptune, and Redis
  accept traffic **only** from the API security group.
- The DB password is **generated** by Terraform and stored in Secrets Manager —
  it never appears in variables or plaintext outputs. The API receives a
  ready-made `DATABASE_URL` DSN via the ECS `secrets` block.
- `GRAPH_BACKEND=neptune` is injected into ECS; AWS staging/prod must not use
  the local SQL graph fallback.
- `LLM_PROVIDER=anthropic`, `EXTRACTION_PROVIDER=llm`, and
  `EMBEDDING_PROVIDER=bedrock` are the AWS defaults. Use `voyage` instead of
  `bedrock` only when `TF_VAR_voyage_api_key` is configured.
- Do not deploy deterministic mock LLMs or hash embeddings to AWS staging/prod.

## Files

| File | Purpose |
| --- | --- |
| `terraform/network.tf` | VPC, public/private subnets, NAT, security groups |
| `terraform/ecr.tf` | Container registries (+ lifecycle policy) |
| `terraform/rds.tf` | PostgreSQL 16 (pgvector), encrypted, backups |
| `terraform/neptune.tf` | Amazon Neptune cluster and instances |
| `terraform/redis.tf` | ElastiCache Redis broker |
| `terraform/s3.tf` | Versioned, encrypted document bucket |
| `terraform/secrets.tf` | Generated DB password, DATABASE_URL, Anthropic key |
| `terraform/alb.tf` | ALB, target group, HTTP listener (HTTPS commented) |
| `terraform/ecs.tf` | Cluster, task definition, service (circuit-breaker rollback) |
| `terraform/iam.tf` | Task execution + task roles (least privilege) |
| `terraform/logs.tf` | CloudWatch log group |
| `smoke_test.sh` | Post-deploy critical-path check |
| `../.github/workflows/ci.yml` | Lint, test, data-validate, docker build, tf validate |
| `../.github/workflows/deploy.yml` | Build → push ECR → roll out ECS → smoke test |

## Prerequisites (only when you actually deploy)

- Terraform >= 1.5, AWS CLI v2.
- An AWS account and credentials (`aws configure` or an assumed role).
- For CI deploys: a GitHub OIDC IAM role and repository variables listed in
  `deploy.yml`.

## Validate offline (no credentials needed)

```bash
cd infra/terraform
terraform init -backend=false
terraform fmt -check -recursive
terraform validate
```

This is exactly what CI runs. It checks syntax and provider schemas without
touching AWS.

## Deploy

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # edit sizing/region

terraform init                                  # configure the S3 backend first for teams
terraform plan  -out tf.plan
terraform apply tf.plan

# Push the first API image (Terraform created the ECR repo):
REPO=$(terraform output -raw ecr_api_repository_url)
aws ecr get-login-password | docker login --username AWS --password-stdin "${REPO%/*}"
docker build -f ../../backend/Dockerfile -t "$REPO:latest" ../..
docker push "$REPO:latest"

# Force the service to pick up the image, then smoke test:
aws ecs update-service --cluster "$(terraform output -raw ecs_cluster_name)" \
  --service "$(terraform output -raw ecs_api_service_name)" --force-new-deployment
BASE="$(terraform output -raw api_url)" bash ../smoke_test.sh
```

Configure real providers without writing keys to disk:

```bash
export TF_VAR_anthropic_api_key="sk-ant-..."
export TF_VAR_llm_provider="anthropic"
export TF_VAR_extraction_provider="llm"
export TF_VAR_embedding_provider="bedrock"
terraform apply
```

If using Voyage embeddings instead of Bedrock:

```bash
export TF_VAR_embedding_provider="voyage"
export TF_VAR_voyage_api_key="..."
terraform apply
```

## CI/CD

- **CI** (`ci.yml`) runs on every push/PR, fully offline: ruff, the pytest
  suite, demo-data build+validate, a Docker image build, `terraform validate`,
  and frontend unit tests.
- **Deploy** (`deploy.yml`) is a **no-op until configured**. Its `preflight`
  job checks for `vars.AWS_DEPLOY_ROLE_ARN`; if unset it logs a notice and
  skips all cloud steps. When set, it assumes the role via OIDC, builds+pushes
  the image, renders a new task definition, rolls it out with
  `wait-for-service-stability`, and runs the smoke test.

## Operations runbook

### Roll back a bad release
The ECS service has a **deployment circuit breaker with rollback enabled**, so a
deploy that fails health checks auto-reverts. To roll back manually to a known
task-definition revision:

```bash
CLUSTER=$(terraform output -raw ecs_cluster_name)
SERVICE=$(terraform output -raw ecs_api_service_name)
# List revisions, pick the last-good one:
aws ecs list-task-definitions --family-prefix graphintel-staging-api --sort DESC
aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" \
  --task-definition graphintel-staging-api:<GOOD_REVISION> --force-new-deployment
aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE"
```

### Back up the database
Automated backups run daily (7-day retention, 03:00–04:00 UTC window). Take an
on-demand snapshot before risky changes:

```bash
aws rds create-db-snapshot \
  --db-instance-identifier graphintel-staging-pg \
  --db-snapshot-identifier graphintel-manual-$(date +%Y%m%d%H%M)
```

### Restore the database
Restores create a **new** instance from a snapshot; repoint `DATABASE_URL` after:

```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier graphintel-staging-pg-restore \
  --db-snapshot-identifier <SNAPSHOT_ID>
# Then update the Secrets Manager DATABASE_URL host and redeploy the service.
```

### Back up Neptune
Neptune automated backups are enabled with 7-day retention. Before risky graph
schema changes, create a manual cluster snapshot:

```bash
aws neptune create-db-cluster-snapshot \
  --db-cluster-identifier graphintel-staging-graph \
  --db-cluster-snapshot-identifier graphintel-graph-manual-$(date +%Y%m%d%H%M)
```

### Rotate the DB password
Generate a new value, update RDS and the secret, then force a new deployment so
tasks pick it up. (For hands-off rotation, attach a Secrets Manager rotation
Lambda — left out here to avoid account-specific wiring.)

### Tail logs
```bash
aws logs tail /ecs/graphintel-staging/api --follow
```

### Tear down (avoid surprise costs)
```bash
cd infra/terraform
terraform destroy
```
`force_destroy`/`skip_final_snapshot` are enabled for non-prod so teardown is
clean; prod keeps deletion protection and a final snapshot.

## Cost note
Defaults are intentionally small (t4g.micro RDS/Redis, single NAT, 2 Fargate
tasks, one t4g.medium Neptune instance for staging). Neptune, the NAT gateway,
and the ALB are the main always-on costs; scale `az_count`/instance classes up
for production HA.
