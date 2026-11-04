# 4. FastAPI + PostgreSQL backend

Date: 2026-11-04
Status: Proposed

## Context
The domain is already in Python. The API must serve a Flutter client,
support offline sync, store audio and keep full control over security and data.

## Decision
- **FastAPI** for the HTTP API, with Pydantic models at the boundary only
  (domain objects stay plain dataclasses).
- **OpenAPI-first contract**: the Dart client is generated from the spec;
  contract tests stop drift.
- **PostgreSQL** (managed) with SQLAlchemy 2 and Alembic migrations; one
  schema per bounded context; row-level ownership checks in every repository query.
- **Object storage** (S3-compatible) for audio and images, private buckets,
  short-lived signed URLs.
- **Background worker** process (same codebase, separate entry point in `bootstrap`)
  for ingestion, transcoding and event handling; transactional outbox for reliable events.
- Local development via `infra/docker-compose.yml` (Postgres, MinIO).
- Dependencies locked (uv or pip-tools) and audited in CI.

## Consequences
- One language across domain, API and workers.
- We own auth integration and operations; managed Postgres and a PaaS
  (e.g. Fly.io, Render or a cloud provider's container service) keep that small.
- The hosting provider is still open (see PLAN open questions).
