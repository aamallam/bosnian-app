# 5. Flutter mobile client

Date: 2026-11-04
Status: Proposed

## Context
Public launch on iOS and Android with a small team. The app needs audio
recording and playback, right-to-left Arabic layout, Cyrillic and Latin
input, and must work offline (daily practice on the commute).

## Decision
- **Flutter** (one Dart codebase), placed in `mobile/`.
- **Feature-first clean architecture**: `lib/features/<feature>/{data,domain,presentation}`
  mirroring the backend contexts, with `lib/core/` for shared pieces.
- State management with **Riverpod**; navigation with **go_router**.
- **Offline-first**: local database (Drift/SQLite) is the source of truth on
  the device; a sync queue sends changes when online. Spaced-repetition
  scheduling also runs on the device so reviews never wait for the network.
- API client **generated from the backend OpenAPI** spec.
- Localisation with ARB files from the start (`flutter_localizations`), RTL tested in CI with golden tests.
- Tokens in Keychain / Keystore (`flutter_secure_storage`), never in shared preferences.
- Security checks against OWASP MASVS (see `docs/security/baseline.md`).

## Consequences
- One UI codebase; native code only for rare platform features.
- FSRS logic exists in Python and Dart; a shared set of test vectors (JSON)
  keeps both implementations identical.
