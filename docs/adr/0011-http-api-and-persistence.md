# 11. HTTP API, persistence and request transactions

Date: 2026-11-05
Status: Proposed
Implements: ADR 0004 (FastAPI + Postgres), most of ADR 0007 (authentication)

## Context
The domain (learning, pairing) is done and tested in memory. The mobile app
needs an API, the data needs a real database, and both must keep the module
boundaries from ADR 0002.

## Decision
**Layering**
- `langex.api` is a *driving adapter*: routes turn HTTP into use-case calls.
  It never imports a context's adapters (import-linter enforces it).
  `langex.bootstrap` builds everything and is the only place that knows the
  concrete adapters.
- Each context owns its tables (`identity_*`, `pairing_*`, `learning_*`) and
  its own SQLAlchemy `MetaData`, written with **SQLAlchemy Core**, so domain
  objects stay plain frozen dataclasses. There are **no foreign keys between
  contexts**, so a context can move to its own database later.
- `langex.platform.sql` holds technical helpers only (UTC datetime type,
  constraint naming).

**Transactions**
- One transaction per request (`UnitOfWork`). The use case *and* the event
  handlers it triggers (pairing → learning) commit or roll back together, so
  a sentence never exists without its partner's review card.
- Errors roll back, with one deliberate exception: when a replayed refresh
  token triggers revocation of its family, the revocation is committed
  before the 401 is returned.
- Single-use rules hold under concurrency: invitation redemption, attempt
  correction and refresh-token use are **guarded updates**
  (`UPDATE … WHERE redeemed_by IS NULL`); the loser of a race gets an error.

**Migrations**
- One Alembic history for all contexts. Migrations never import application
  code. A test checks that migrations produce exactly the schema the code
  expects and that downgrade works.
- On Render's free plan the container runs `alembic upgrade head` before
  starting (no pre-deploy hook); move this to a release job before running
  more than one instance.

**Authentication (ADR 0007)**
- Apple and Google ID tokens are verified against the providers' JWKS:
  RS256 only, issuer, audience = our client IDs, expiry, issued-at and a
  **required nonce**. Only the provider's opaque subject is stored: no
  email, no name.
- Our access token: HS256 JWT, 15 minutes, algorithm pinned on verify.
- Refresh token: 256-bit random, stored as SHA-256, rotated on every use,
  30 days, with **reuse detection** that revokes the whole family.
- A `dev` provider (`dev:<name>`) exists for local work and tests; settings
  refuse it in staging and production.
- Not yet done: email magic link or passkey, device list, account deletion
  and data export (Phase 6, before launch).

**API conventions**
- Versioned under `/v1`. Errors are RFC 9457 `application/problem+json`.
- Missing and foreign objects both return **404** (no IDOR oracle).
- Inputs forbid unknown fields (no mass assignment) and cap every string;
  validation errors never echo input back.
- Limits: 64 KB request bodies; per-IP sliding-window rate limits (10/min
  for auth, 120/min otherwise) on top of the domain's 50 sentences a day.
  The limiter is in memory, which is right for one instance; use Redis
  before scaling out.
- Security headers on every response (HSTS, nosniff, `default-src 'none'`,
  no-store, no `Server` header). Docs and OpenAPI only outside staging and production.
- JSON access logs with method, route template, status and timing; never
  bodies, tokens or IP addresses.

**Testing**
- SQL tests run on SQLite in memory locally and on PostgreSQL in CI
  (`TEST_DATABASE_URL`). Repository contract tests run the same scenarios on
  the in-memory and SQL adapters.
- CI builds the Docker image and smoke-tests it (starts, migrates, answers,
  runs as a non-root user).

## Consequences
- The whole loop (sign in → pair → teach → review → practise → correct)
  works over HTTP and is covered by tests.
- Reviews return `item_id`; the client shows the matching contribution or
  correction it already has (offline-first). A server-side endpoint for
  typed answers comes with the content read model.
- Sync endpoints run in FastAPI's thread pool. That is plenty for the free
  tier; switch to async drivers only if profiling says so.
