# GraphIntel Dataset Plan

## Goal

GraphIntel must ship with a reproducible local demo dataset. The dataset should
prove graph reasoning across customers, tickets, incidents, services, teams,
SLA clauses, postmortems, and runbooks.

## Data Sources

Use this priority order:

1. Public support ticket datasets where licensing allows.
2. Public status page incident feeds or exported incident JSON where available.
3. Public postmortems and outage writeups where licensing allows.
4. Synthetic fallback data for anything private or unavailable.

## Required Scripts

Create these scripts in the implementation project:

- `scripts/download_datasets.py`
- `scripts/generate_synthetic_demo_data.py`
- `scripts/prepare_demo_data.py`
- `scripts/validate_demo_data.py`

## Required Folders

- `data/raw`
- `data/synthetic`
- `data/processed`
- `data/fixtures`

## Minimum Dataset

| Type | Count |
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

Synthetic data must include stable IDs and explicit source labels:

- `synthetic: true`
- `source_rule`
- `created_by_script`

Synthetic examples:

- `CUST-acme`
- `SUP-0884`
- `INC-0247`
- `SVC-payment-api`
- `TEAM-backend-payments`
- `SLA-acme-enterprise`
- `CLAUSE-acme-availability-99-9`

## Golden Questions

The dataset must support these questions:

1. Which customers were affected by Payment API incidents in the last 30 days?
2. Is Acme Corp at SLA risk because of checkout or payment incidents?
3. Which engineering team owns the service involved in INC-247?
4. What is the likely root cause of recurring checkout timeout tickets?
5. Which runbook should be used for payment gateway timeout errors?

## Failure Behavior

If public downloads fail, scripts must:

1. Log the failed URL or dataset name.
2. Continue with synthetic fallback data.
3. Produce a complete local demo dataset.
4. Print a clear summary of which sources were real and which were synthetic.

