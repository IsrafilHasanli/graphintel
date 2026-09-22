# Security Policy

## Supported Version

GraphIntel is currently pre-1.0. Security fixes are applied to the `main`
branch.

## Reporting a Vulnerability

Do not open a public issue for suspected secrets, credential exposure, or
security vulnerabilities. Contact the repository owner privately with:

- a concise description of the issue
- affected files, endpoints, or infrastructure components
- reproduction steps when available
- expected impact

## Secret Handling

The repository must not contain production credentials. The following are
intentionally ignored:

- `.env` and `.env.local`
- Terraform state and local variable files
- local database files
- dependency folders and build outputs
- archived local AI-development material

Use `.env.example` as a template only. Store production credentials in AWS
Secrets Manager or an equivalent secret-management system.

## Production Safety

Managed environments should reject unsafe defaults:

- SQLite
- SQL-only graph backend
- deterministic LLM or embedding providers
- wildcard CORS
- placeholder API keys
- missing Amazon Neptune configuration

Review `backend/app/config.py` before changing production settings behavior.
