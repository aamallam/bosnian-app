"""langex: pair-learning language exchange backend.

Modular monolith. Each top-level package is a bounded context with its own
hexagonal layers (domain / application / adapters):

- shared_kernel: tiny value objects every context may use (LanguageCode, events)
- languages:     language profiles - script, direction, answer matching (pluggable)
- content:       sentences, sources, ingestion of external material
- pairing:       learner pairs, invitations, daily contributions, corrections
- learning:      spaced repetition, reviews, progress
- identity:      accounts, consent, age gate, deletion
- bootstrap:     composition root - the only place that wires contexts together

Boundaries are enforced by import-linter (see pyproject.toml).
"""
