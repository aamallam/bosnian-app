# Langex mobile app

A Flutter app for iOS and Android. ADR 0005 describes the structure and
ADR 0012 the decisions for the first version.

```
lib/
├─ main.dart            starts the app, restores the session
├─ app/                 composition root (providers.dart), router, theme
├─ core/                shared pieces: config, API client, session, UI helpers
├─ features/
│  ├─ auth/             sign-in and sign-out
│  ├─ languages/        the language list from the server
│  ├─ pairing/          partners: invite, join, teach, practise, correct
│  └─ learning/         daily review
└─ l10n/                app_en.arb, app_bs.arb, app_ar.arb
test/
├─ contract/            openapi.json (a copy from the backend) + contract tests
├─ core/  widgets/      unit and widget tests (Arabic RTL and Bosnian plurals too)
└─ support/fakes.dart   scripted fake API
```

Each feature is split into `data/` (API calls), `domain/` (models and rules),
`application/` (Riverpod providers) and `presentation/` (screens).

## Run against a local server

Start the backend first (see [docs/deploy.md](../docs/deploy.md#local-development)), then:

```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000 --dart-define=DEV_SIGN_IN=true
```

`10.0.2.2` is your computer as seen from the Android emulator; on the iOS
simulator use `http://localhost:8000`. Plain HTTP works only for these local
addresses and only in debug builds; everything else must use HTTPS.
`DEV_SIGN_IN` shows a name field that only a development server accepts.

## Checks (the same as CI)

```bash
flutter pub get
dart format --output=none --set-exit-if-changed lib test tool
flutter analyze --fatal-infos
flutter test --coverage
dart run tool/coverage_gate.dart 85
```

## When the API changes

The contract tests use a copy of the backend's OpenAPI document. Refresh it
from `backend/`:

```bash
python -m langex.api.openapi > ../mobile/test/contract/openapi.json
```

A backend test fails until the copy is current. The mobile contract test then
fails for every call the app makes that no longer matches.
