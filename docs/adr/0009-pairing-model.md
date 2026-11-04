# 9. Pairing model: invitations, exchange and the shared streak

Date: 2026-11-05
Status: Proposed

## Context
Pair learning is the main feature: two people each teach their native
language and learn the other's. It needs safe pairing, a way to teach
(sentences) and a way to practise with feedback (corrections). It also needs
a habit loop that rewards cooperation rather than competition.

## Decision
- **Pair**: two memberships that mirror each other (A teaches what B learns,
  and the other way round). It is checked when built and stored as a tuple
  of members, so circles of more than two people can extend it later.
- **Invitation**: a 128-bit random code from `secrets`, valid for 7 days
  and usable once. Only its SHA-256 hash is stored, so a leaked database row
  cannot be used to join a pair. A user cannot accept their own invitation.
- **Contribution** (teaching): text in the author's teaching language, an
  optional gloss in a bridge language, and an optional usage note. It
  publishes `ContributionAdded`.
- **Attempt → Correction** (practising): the learner writes in their
  target language. Only the native partner can correct it, and only once.
  This publishes `AttemptCorrected`.
- **Cross-context flow**: the composition root subscribes learning to both
  events, so taught and corrected items become review cards. `start_learning`
  is idempotent, so a duplicated event is harmless.
- **Shared streak**: a day counts when both partners reach the goal (default
  3 sentences). One partner can cover a missed day by adding twice the goal,
  but not two days in a row. Today never breaks the streak while it is still open.
- **Access control**: every use case takes the acting user first. Missing
  and foreign pairs or attempts raise the same error (no IDOR oracle).
  There is a ceiling of 50 contributions per person per rolling day against spam.

## Consequences
- The main loop (teach → learn → practise → correct → learn) works end to end
  in memory and is covered by tests through the composition root.
- Days are UTC for now; a pair timezone is needed before launch.
- Audio, reporting and blocking come with storage and moderation (Phases 3 and 6).
