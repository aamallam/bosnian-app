# 2. Modular monolith with bounded contexts

Date: 2026-11-04
Status: Proposed

## Context
The app will grow in features (pair learning, spaced repetition, external
content, AI help, calls, circles) and in languages. One flat
`domain/application/adapters` package (ADR 0001) would turn into a single
tangled domain. Microservices from day one would cost a small team far more
in operations than they return.

## Decision
One deployable backend, split into bounded contexts under `src/langex/`:
`shared_kernel`, `languages`, `content`, `pairing`, `learning`, `identity`,
plus `bootstrap` as the composition root. Each context keeps hexagonal
layers inside it.

Rules, enforced by import-linter in CI and in the test suite:
- contexts do not import each other; they communicate through domain events
  (in process at first, an outbox table + queue later) or through
  application-level interfaces wired in `bootstrap`;
- inside a context, adapters → application → domain only;
- `shared_kernel` stays tiny and depends on nothing.

Each context will own its own database tables (its own schema in Postgres);
no context reads another's tables.

## Consequences
- New features land as a new context or adapter with little impact on existing code.
- Any context can later become a separate service, because its boundary and
  data are already separate.
- Some duplication between contexts (e.g. each has its own view of a "user") is accepted on purpose.
- Contributors must learn the rules; CI explains a broken contract by name.
