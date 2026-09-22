# GraphIntel Architecture

## Overview

GraphIntel is a Graph RAG platform for support and incident intelligence. It
combines a knowledge graph, vector retrieval, source-grounded answer generation,
and human review workflows.

## Services

| Service | Responsibility |
| --- | --- |
| API Service | HTTP endpoints, auth boundary, request validation |
| Ingestion Service | Parse files, normalize records, create chunks |
| Extraction Service | Extract entities and relations from chunks |
| Graph Service | Upsert graph nodes and relations |
| Vector Service | Embed and search chunks/entities |
| Retrieval Service | Query analysis, entity linking, graph expansion, reranking |
| Answer Service | Generate cited answers and limitations |
| Evaluation Service | Run golden question sets and metrics |
| Frontend App | Dashboard, upload, ask, graph explorer, review, evals |

## Storage

| Store | Data |
| --- | --- |
| PostgreSQL | Users, documents, chunks, jobs, answers, audits, eval runs |
| Amazon Neptune | Entities and relations in staging/production |
| SQL graph mirror | Offline/local entity-relation traversal |
| pgvector | Chunk embeddings and optional entity embeddings |
| Object storage | Raw uploads and parsed artifacts |

## Retrieval Sequence

1. User submits a question.
2. Query analyzer extracts intent, entities, time range, and evidence needs.
3. Entity linker maps query mentions to graph nodes.
4. Graph retriever expands relevant neighborhoods.
5. Vector retriever searches chunks linked to graph candidates and the global corpus.
6. Reranker selects evidence.
7. Context builder packages snippets, citations, and graph paths.
8. Answer service generates the final response.
9. Validator checks citation coverage and unsupported claims.
10. Answer and metrics are stored.

## Ingestion Sequence

1. Upload file or import dataset.
2. Create ingestion job.
3. Parse into normalized document records.
4. Chunk text with metadata.
5. Extract entities and relations.
6. Canonicalize and deduplicate entities.
7. Upsert graph nodes and edges.
8. Embed chunks.
9. Update job status and errors.

## MVP Deployment

Use Docker Compose locally:

- `api`
- `postgres`
- `redis`
- `web`

Production can split the same boundaries into separate services later.

