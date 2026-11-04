# 10. Free-tier hosting for development and dogfooding

Date: 2026-11-05
Status: Proposed

## Context
Until the app has real users, hosting should cost nothing. It must still run
the FastAPI service, PostgreSQL and private audio storage, and moving to
paid hosting later must be easy. Free tiers change often (in 2026 Fly.io
dropped its free tier for new accounts, and Koyeb's became unclear), so we
must not depend on any single provider's extras.

## Decision
| Need | Service (free tier, checked Nov 2026) | Why | Main limits |
|---|---|---|---|
| API (FastAPI container) | **Render** free web service | No card needed; deploys from GitHub; runs our Dockerfile | Sleeps after 15 min idle (about 1 min cold start); low bandwidth allowance |
| PostgreSQL | **Neon** free | Real Postgres; scales to zero; database branches for staging and PR previews | 1 GB storage and 100 compute-hours a month per project |
| Audio and images | **Cloudflare R2** free | S3-compatible; free egress; 10 GB a month | Billed above the allowance (no hard cap): set a billing alert |
| CI | **GitHub Actions** | Already in use | Minute limits on private repositories |
| Error tracking | **Sentry** free developer plan | Error reports with scrubbing of personal data | One user, limited events |

The plan if we outgrow this: **Google Cloud Run**. It is also a container,
has a larger free allowance and starts quickly from zero, but needs a
billing account. Move there when cold starts start to hurt.

Portability rules, so switching provider is a configuration change only:
- the API ships as one **Docker image**, configured only through environment variables (12-factor);
- the database is reached through a standard `DATABASE_URL`, with no provider-specific features;
- storage goes through the S3 API behind a `BlobStorage` port, so R2, S3 or MinIO (local) all work;
- secrets live in each provider's secret settings, never in the repository.

## Consequences
- $0 a month for hosting while you and your friend dogfood the app.
- Cold starts mean the first request after a quiet spell is slow. The
  offline-first mobile app (ADR 0005) hides most of this, because reviews
  run on the device.
- Not free regardless of hosting: the **Apple Developer Program**
  ($99 a year, needed for TestFlight, the App Store and Sign in with Apple)
  and **Google Play** (a one-time $25 registration). Android testing can
  start for free with sideloaded builds.
- Free tiers can change without notice; re-check the limits each quarter.
