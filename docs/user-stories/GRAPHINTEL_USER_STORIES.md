# GraphIntel User Stories

## Epic 1: Data Ingestion

| ID | User Story | Acceptance Criteria |
| --- | --- | --- |
| US-001 | As a Platform Admin, I want to upload support ticket CSV files so the system can ingest historical customer issues. | CSV upload accepts valid files; invalid rows are reported; documents and chunks are created; ingestion job status is visible. |
| US-002 | As a Platform Admin, I want to import incident JSON files so incident history can be linked to tickets and services. | JSON incidents create Incident and IncidentUpdate records; timestamps and impact are preserved; malformed records are reported. |
| US-003 | As a Platform Admin, I want to upload Markdown postmortems so root causes and mitigations can be extracted. | Markdown files become Document and Chunk records; extracted incidents/root causes preserve source references. |
| US-004 | As a Platform Admin, I want to upload SLA documents so customer risk can be reasoned over. | SLA documents create SLAContract and SLAClause candidates; clauses include source citations and confidence. |
| US-005 | As a Platform Admin, I want ingestion jobs to show progress and errors so I can fix broken imports. | Job states include queued, parsing, chunking, extracting, indexing, completed, failed, and partial; errors include file, row/chunk, and reason. |

## Epic 2: Entity And Relation Extraction

| ID | User Story | Acceptance Criteria |
| --- | --- | --- |
| US-006 | As a Platform Admin, I want entities extracted from source data so the system can build a knowledge graph. | Extracts customers, tickets, incidents, services, teams, SLA clauses, errors, root causes, runbooks, documents, and chunks. |
| US-007 | As a Platform Admin, I want relationships extracted with confidence so low-quality graph edges can be reviewed. | Relations include type, source ID, confidence, created timestamp, and extraction method. |
| US-008 | As a Platform Admin, I want duplicate entities detected so names like "Acme" and "Acme Corp" can be merged. | Entity aliases are stored; merge preserves all source links; future retrieval uses canonical entity. |
| US-009 | As a Platform Admin, I want to reject wrong relations so the graph stays trustworthy. | Relation deletion creates audit record; deleted relation no longer appears in retrieval paths. |
| US-010 | As a Platform Admin, I want manual corrections to affect future answers so review work improves the system. | Edited entities and relations are used by graph retrieval and visible in answer reasoning paths. |

## Epic 3: Knowledge Graph

| ID | User Story | Acceptance Criteria |
| --- | --- | --- |
| US-011 | As an SRE, I want incidents linked to affected services so I can understand blast radius. | Incident-to-service paths are queryable and visible in graph explorer. |
| US-012 | As a Support Manager, I want customers linked to tickets and incidents so I can identify impacted accounts. | Customer-to-ticket-to-incident traversal returns expected demo data. |
| US-013 | As a Support Manager, I want SLA clauses linked to customers and services so SLA risk can be detected. | Customer-to-SLA-to-service-to-incident paths are stored and retrievable. |
| US-014 | As an SRE, I want services linked to owning teams so ownership is visible during incidents. | Service ownership appears in graph and answers. |
| US-015 | As an SRE, I want runbooks linked to error signatures so recommended actions are operationally useful. | Error-to-runbook relations are retrievable and cited. |

## Epic 4: Hybrid Graph RAG Ask

| ID | User Story | Acceptance Criteria |
| --- | --- | --- |
| US-016 | As a Support Manager, I want to ask which customers were affected by an incident so I can prioritize outreach. | Answer lists customers, citations, reasoning path, confidence, and limitations. |
| US-017 | As a CSM, I want to ask whether a customer is at SLA risk so I can prepare communication. | Answer uses tickets, incidents, SLA clauses, and service data; unsupported risk is clearly qualified. |
| US-018 | As an SRE, I want to ask for likely root cause of recurring errors so I can find related incidents and postmortems. | Retrieval includes graph-related incidents and semantically similar chunks; citations identify postmortems/tickets. |
| US-019 | As a user, I want every answer to include citations so I can verify the claim. | `/ask` never returns a final answer with empty citations unless it explicitly says evidence is insufficient. |
| US-020 | As a user, I want to see the reasoning path so I understand how graph relationships informed the answer. | Response includes ordered graph edges and UI renders them. |

## Epic 5: Frontend Workflows

| ID | User Story | Acceptance Criteria |
| --- | --- | --- |
| US-021 | As a Platform Admin, I want a dashboard so I can see ingestion health and graph coverage. | Dashboard shows document counts, job status, entity counts, relation counts, and eval status. |
| US-022 | As a Platform Admin, I want an upload page so I can import datasets and documents. | Upload supports supported file types, progress, errors, retry, and completed state. |
| US-023 | As a Support Manager, I want an Ask page so I can query support and incident knowledge. | Ask page shows answer, citations, confidence, reasoning path, recommended actions, and limitations. |
| US-024 | As an SRE, I want a graph explorer so I can inspect incident-service-customer relationships. | Explorer supports search, filtering, node details, edge details, zoom, pan, and path highlighting. |
| US-025 | As a Platform Admin, I want an entity review page so I can merge duplicates and correct relations. | Admin can edit entity labels, merge entities, delete relations, and see audit messages. |
| US-026 | As a QA user, I want an evaluation page so I can run golden question tests. | Eval page starts runs, shows metrics, lists failed questions, and exposes expected vs actual citations. |

## Epic 6: Evaluation And Quality

| ID | User Story | Acceptance Criteria |
| --- | --- | --- |
| US-027 | As a QA Engineer, I want golden questions so Graph RAG quality can be regression-tested. | At least five golden questions exist with expected answer themes and evidence IDs. |
| US-028 | As a QA Engineer, I want citation coverage metrics so unsupported answers can be detected. | Eval run reports percentage of claims with citations and flags zero-citation answers. |
| US-029 | As a QA Engineer, I want reasoning path validation so graph paths are not fabricated. | Every reasoning edge is checked against stored graph relations. |
| US-030 | As a QA Engineer, I want retrieval metrics so graph/vector retrieval quality can be improved. | Eval reports expected evidence recall and precision at k. |
| US-031 | As a Product Owner, I want release gates so MVP readiness is explicit. | Release gate returns PASS, CONDITIONAL PASS, or FAIL with blockers. |

## Epic 7: DevOps And AWS Deployment

| ID | User Story | Acceptance Criteria |
| --- | --- | --- |
| US-032 | As a Developer, I want Docker Compose so I can run GraphIntel locally with one command. | Compose starts API, web, worker, PostgreSQL, Redis, and optional graph service; README documents startup and shutdown. |
| US-033 | As a DevOps Engineer, I want deployable service images so GraphIntel can run in AWS. | Backend, frontend, and worker Docker images build successfully and expose health checks. |
| US-034 | As a DevOps Engineer, I want AWS infrastructure-as-code so environments are reproducible. | IaC provisions or documents VPC, ECS, ALB, RDS, Redis, S3, ECR, secrets, and logs. |
| US-035 | As a DevOps Engineer, I want CI/CD so changes can be tested and deployed safely. | CI runs lint/tests/build; deploy workflow builds/pushes images and updates AWS services when credentials are configured. |
| US-036 | As an Operator, I want secrets and environment variables documented so deployment is secure. | `.env.example` exists; real secrets are not committed; AWS Secrets Manager or SSM usage is documented. |
| US-037 | As an Operator, I want smoke tests and rollback docs so production issues can be handled. | Deployed health checks, frontend smoke test, rollback steps, backup/restore notes, and cleanup commands are documented. |
| US-038 | As a Platform Owner, I want AWS production to use Amazon Neptune so GraphIntel has a managed graph database. | AWS deployment provisions/configures Neptune; `GRAPH_BACKEND=neptune`; smoke tests verify graph connectivity and traversal. |
| US-039 | As a Platform Owner, I want no mock services in AWS production so demos and production are real. | AWS production/staging does not use SQLite, in-memory graph storage, deterministic mock LLM, hash embeddings, or local filesystem object storage. |

## MVP Golden Questions

1. Which customers were affected by Payment API incidents in the last 30 days?
2. Is Acme Corp at SLA risk because of checkout or payment incidents?
3. Which engineering team owns the service involved in INC-247?
4. What is the likely root cause of recurring checkout timeout tickets?
5. Which runbook should be used for payment gateway timeout errors?
