# 12. Mobile MVP: online client first, contract-tested API calls

Date: 2026-11-05
Status: Proposed
Amends: ADR 0005 (Flutter mobile client)

## Context
Phase 4 builds the app we will use every day for two weeks. ADR 0005 asks
for an offline-first app with a client generated from the OpenAPI document.
Two practical points push us to deliver it in two steps:
- Generating a Dart client needs the Java-based OpenAPI Generator in every
  developer setup and in CI, for an API of 16 operations.
- Offline sync (a local database plus an outbox) is the largest and riskiest
  part. It is easier to get right once the screens and flows are settled.

## Decision
**Part 1 (this change): an online app with the full loop.** Sign-in, invite
or join a partner, teach sentences with their meaning, practise, correct
your partner, and a daily review with ratings.

**API client: hand-written, checked against the contract.**
- Small typed API classes per feature (`features/*/data`), with strict JSON
  readers that fail on missing or mistyped fields.
- The backend writes its OpenAPI document to
  `mobile/test/contract/openapi.json`, and a backend test fails when that
  copy is out of date.
- The mobile contract test runs every API call against a fake server built
  only from that document. The fake server refuses unknown routes and
  query parameters, request fields the API does not accept and missing
  required fields. It answers with data generated from the response
  schemas, which the parsers must read. The test also fails when the API
  gains an operation the app neither uses nor deliberately skips.
- This gives the same protection as generated code, without the Java
  toolchain. We can switch to generation later without changing the screens.

**Session and security (OWASP MASVS)**
- Tokens live only in the Keychain or Keystore (`flutter_secure_storage`).
  On iOS they are marked `first_unlock_this_device`, so they never move to
  another device. On Android, backup and device transfer are turned off.
- The access token is refreshed 60 seconds before it expires and once after
  a 401. Parallel requests share a single refresh, because the server treats
  a refresh token used twice as theft. A refused refresh signs the device
  out. A network error during refresh keeps the session.
- Requests never follow redirects, so a token is never sent to another host.
- HTTPS is required. Plain HTTP works only to a local development server
  (10.0.2.2, localhost), and only in debug builds, through Android's network
  security configuration and iOS `NSAllowsLocalNetworking`.
- Screens show their own messages based on the type of error, never text
  from the server.
- Riverpod retries a failed load only for network errors (three times, with
  back-off), never for 4xx answers.

**Text direction and languages.** The interface is translated into English,
Bosnian and Arabic (ARB files), with Arabic right-to-left. Every sentence
is shown in the direction of its own language, so Arabic stays
right-to-left inside a Bosnian screen and the other way round. Widget tests
check RTL layout, Arabic dual plurals and Bosnian few/other plurals.
Golden-image tests come once there is a design.

**Backend support added:** `GET /v1/pairs/{id}/attempts` returns the
caller's own attempts with corrections, with an index on
`(pair_id, learner_id, created_at)`. The app needs it to show corrections
and the corrected-sentence review cards.

## Not yet (Part 2 and later)
- **Offline-first:** Drift (SQLite) as the source of truth on the device, an
  outbox for sentences, attempts and reviews, and FSRS on the device with
  test vectors shared with Python (ADR 0005). This needs the API to accept a
  client-side `reviewed_at` and idempotency keys.
- **Sign in with Apple and Google** (a nonce in each request; native setup
  with the client IDs from docs/deploy.md). Until then only the development
  server can be used, with `DEV_SIGN_IN`.
- Audio recording and playback, share links and QR codes for invitations,
  push reminders.

## Consequences
- Dogfooding against staging needs Part 2's Google sign-in. Until then we
  can use the app against a local server.
- If the backend and the app disagree about the API, CI fails on both sides
  before a release.
