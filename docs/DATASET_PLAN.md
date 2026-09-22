# Dataset Plan

GraphIntel ships with a reproducible demo corpus that exercises graph-based
support and incident reasoning without exposing private customer data.

## Goals

- Provide enough data to demonstrate ingestion, extraction, graph traversal,
  vector retrieval, cited answers, and evaluation.
- Keep generated data reproducible from scripts.
- Track only stable fixtures in Git; keep downloaded and generated corpora out
  of the repository.
- Avoid confidential, personal, credential, or customer-private data.

## Data Pipeline

| Script | Purpose |
| --- | --- |
| `scripts/download_datasets.py` | Attempts public-source downloads where licensing permits |
| `scripts/generate_synthetic_demo_data.py` | Creates deterministic synthetic support and incident data |
| `scripts/prepare_demo_data.py` | Orchestrates download, fallback generation, processing, and fixtures |
| `scripts/validate_demo_data.py` | Validates counts, schema expectations, and golden-question support |

## Directory Policy

| Directory | Git policy | Contents |
| --- | --- | --- |
| `data/fixtures` | tracked | Small stable fixtures used by tests and evaluation |
| `data/raw` | ignored except `.gitkeep` | Downloaded public source material |
| `data/synthetic` | ignored except `.gitkeep` | Generated synthetic source records |
| `data/processed` | ignored except `.gitkeep` | Processed import corpus |

## Minimum Corpus

| Entity or document type | Minimum count |
| --- | ---: |
| Customers | 5 |
| Support tickets | 50 |
| Incidents | 10 |
| Incident updates | 20 |
| Postmortems | 5 |
| Services | 8 |
| Teams | 4 |
| SLA contracts | 5 |
| SLA clauses | 15 |
| Runbooks | 5 |
| Explicit graph relations | 20+ |

## Synthetic Data Requirements

Synthetic records should use stable IDs and explicit provenance fields, for
example:

- `synthetic: true`
- `source_rule`
- `created_by_script`

Representative IDs:

- `CUST-acme`
- `SUP-0884`
- `INC-0247`
- `SVC-payment-api`
- `TEAM-backend-payments`
- `SLA-acme-enterprise`
- `CLAUSE-acme-availability-99-9`

## Golden Questions

The demo corpus must support these regression questions:

1. Which customers were affected by Payment API incidents in the last 30 days?
2. Is Acme Corp at SLA risk because of checkout or payment incidents?
3. Which engineering team owns the service involved in INC-247?
4. What is the likely root cause of recurring checkout timeout tickets?
5. Which runbook should be used for payment gateway timeout errors?

## Failure Behavior

If a public download fails, the pipeline should:

1. Log the failed source.
2. Continue with deterministic synthetic fallback data.
3. Produce a complete local demo corpus.
4. Print a summary of real versus synthetic sources.

## Validation

Run:

```bash
python scripts/prepare_demo_data.py
python scripts/validate_demo_data.py
```

The validation script should fail when required counts, fixture files, or
golden-question expectations are missing.
