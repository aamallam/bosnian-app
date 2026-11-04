# 8. Spaced repetition with FSRS, via the reference library

Date: 2026-11-04
Status: Proposed

## Context
Spaced repetition is the heart of the learning context. FSRS (Free Spaced
Repetition Scheduler) is the current state of the art: it is used by Anki,
it models stability, difficulty and retrievability per item, and it can be
tuned to each learner from their review history. Its maths changes between
versions (FSRS-4.5, 5, 6), and errors in a home-made version would quietly
damage learning.

## Decision
- The domain owns the data: `ReviewCard`, `MemoryState`, `Rating`, `ReviewLog`.
  Phases are LEARNING, REVIEW and RELEARNING.
- The algorithm sits behind the `Scheduler` port. The production adapter
  `FsrsScheduler` wraps **py-fsrs** (`fsrs`, MIT, maintained by
  Open Spaced Repetition). Only `learning/adapters/fsrs_scheduler.py` imports it.
- Defaults: desired retention 0.9 (allowed range 0.7–0.97), interval fuzzing
  on in production and off in tests, maximum interval 100 years.
- Typed answers map to ratings: EXACT → GOOD, CLOSE → HARD, WRONG → AGAIN.
  The learner may upgrade to EASY.
- Review logs are kept so per-learner parameters can be optimised later
  with py-fsrs's optimiser.
- Property-based tests (Hypothesis) check the invariants: due date never
  before the review, stability positive, difficulty between 1 and 10, and
  better ratings never giving shorter intervals.

## Consequences
- Correct maths for free; upgrades are a version bump plus re-running the tests.
- The Flutter app needs the same algorithm offline. The Dart FSRS port from
  the same project can be used, checked against shared JSON test vectors
  produced by this adapter.
- One runtime dependency, pinned to a major version (`fsrs>=6.3,<7`).
