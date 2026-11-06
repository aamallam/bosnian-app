# Engineering plan

Status: draft for review · Last updated: 2026-11-05

## 1. Product in one paragraph

A mobile app where two people teach each other their native languages.
Each day both partners add a few real sentences, with their own voice
recordings and notes on when the sentence is used. The app turns what the
partner taught into spaced-repetition practice, lets learners write their
own sentences for the partner to correct, and adds material from
dictionaries, websites and public social-media teaching accounts.
It is built on proven methods: comprehensible input, retrieval practice,
spaced repetition (FSRS), output with feedback, and CEFR can-do goals.

First launch: **public on the App Store and Google Play**.
First language pair: **Bosnian ⇄ Arabic**. Any other pair must work without core code changes.

## 2. Decisions so far

| Area | Decision | Record |
|---|---|---|
| Architecture | Modular monolith, bounded contexts, hexagonal layers inside each | [ADR 0002](adr/0002-modular-monolith-with-bounded-contexts.md) |
| Languages | Language profiles as plugins (entry points); generic fallback for any ISO code | [ADR 0003](adr/0003-languages-as-plugins.md) |
| Backend | Python 3.12, FastAPI, PostgreSQL, SQLAlchemy + Alembic | [ADR 0004](adr/0004-fastapi-postgres-backend.md) |
| Mobile | Flutter, feature-first clean architecture, offline-first | [ADR 0005](adr/0005-flutter-mobile-client.md) |
| External content | Automated collection from public accounts and pages, **with guardrails** | [ADR 0006](adr/0006-external-content-ingestion.md) |
| Auth | Sign in with Apple / Google (OIDC) + email passkey; no own password store | [ADR 0007](adr/0007-authentication.md) |
| Spaced repetition | FSRS through the reference library (py-fsrs), behind a `Scheduler` port | [ADR 0008](adr/0008-fsrs-via-reference-library.md) |
| Pairing | Hashed single-use invitations, contributions, corrections, shared streak with cover | [ADR 0009](adr/0009-pairing-model.md) |
| API and persistence | `/v1` REST API, SQLAlchemy Core per context, one transaction per request, guarded single-use updates | [ADR 0011](adr/0011-http-api-and-persistence.md) |
| Mobile MVP | Online app first (offline sync in part 2); hand-written API client checked by contract tests against the OpenAPI document | [ADR 0012](adr/0012-mobile-mvp-client.md) |
| Hosting (for now) | $0: Render (API container), Neon (Postgres), Cloudflare R2 (audio); Cloud Run as next step | [ADR 0010](adr/0010-free-tier-hosting.md) |

## 3. Repository layout

```
bosnian-app/                  (rename to the product name later)
├─ backend/                   Python service + workers
│  ├─ src/langex/
│  │  ├─ shared_kernel/       LanguageCode, DomainEvent - tiny, depends on nothing
│  │  ├─ languages/           language profiles, answer matching, plugin discovery
│  │  ├─ content/             sentences, translations, audio, sources, ingestion
│  │  ├─ pairing/             pairs, invitations, daily contributions, corrections
│  │  ├─ learning/            FSRS scheduling, reviews, progress, CEFR goals
│  │  ├─ identity/            accounts, sign-in, tokens; later consent, export & deletion
│  │  ├─ platform/            technical helpers shared by adapters (SQL types)
│  │  ├─ api/                 HTTP adapter: FastAPI routes, schemas, middleware
│  │  └─ bootstrap/           composition root: settings, DI wiring, all tables
│  ├─ migrations/             Alembic (one history for all contexts)
│  └─ tests/                  mirrors contexts + architecture tests
├─ mobile/                    Flutter app: lib/{app,core,features/*,l10n}, contract tests
├─ infra/                     docker-compose for local dev (render.yaml at the root)
├─ docs/  adr/  security/  PLAN.md
└─ .github/                   CI, Dependabot
```

Each context has `domain/` (pure rules), `application/` (use cases, ports),
`adapters/` (database, HTTP, external APIs). **import-linter** enforces in CI that:

- dependencies point inward (adapters → application → domain);
- contexts never import each other; they talk through **domain events**
  (e.g. `pairing` emits `ContributionAdded`, `learning` reacts by creating review cards);
- only `bootstrap` wires things together.

This is what keeps the app open for new features: a new feature is usually
a new context or a new adapter, not edits spread across the codebase. A context
can later be split out into its own service if load demands it, because its
boundary already exists.

## 4. Core domain model (pair learning)

```
Learner ── speaks ──▶ native languages      Pair (2 learners, or a Circle of N later)
        └─ learns ──▶ target languages        ├─ Invitation (single-use code / link, expires)
                                              ├─ DailyGoal (n sentences each, timezone-aware)
Contribution (by teacher, for partner)        └─ Streak (shared, with "cover for partner")
  ├─ Sentence (teacher's native language)
  ├─ Gloss (bridge language, optional)       Attempt (learner writes in target language)
  ├─ Audio (native recording)                  └─ Correction (by native partner, inline diff)
  ├─ Note (register, dialect, context)
  └─ Source (manual / web / social / ...)    ReviewCard (FSRS state per learner per item)
                                               └─ ReviewLog (each answer, MatchLevel)
```

Points to settle while building `pairing`:

- **Bridge language.** Your friend may not read Arabic well, and you may not
  read Bosnian, so each sentence needs a meaning both can read. Default: an
  optional gloss in a shared language (English), plus pictures for beginners.
- **Variants.** Bosnian vs Serbian/Croatian forms; Arabic MSA vs dialect
  (Levantine, Gulf, Egyptian...). Modelled as a `variant` tag on the sentence, not as separate languages.
- **Translations as links**, not nested objects: the current `Sentence.translations`
  tuple will become a `TranslationLink` between sentences so one sentence can
  serve many pairs.

## 5. Roadmap

Sizes are relative (S ≈ days, M ≈ 1–2 weeks, L ≈ 3–4 weeks) for one developer;
I will refine them once you tell me how many hours a week you can put in.

| Phase | Goal | Size | Done when |
|---|---|---|---|
| **0. Foundations** ✅ done (branch protection still to switch on) | Repo hygiene, monorepo layout, lint/type/test/security tooling, CI, ADRs | S | CI green on `main`, branch protection on, actions pinned to SHAs |
| **1. Learning core** ✅ in review | FSRS scheduler, `ReviewCard`, `ReviewLog`, review session use case, in-memory adapters | M | A simulated learner can review 100 cards with correct due dates; property-based tests |
| **2. Pairing core** ✅ in review | Pair, Invitation, Contribution, Attempt, Correction, DailyGoal, Streak; domain events | M | Two simulated users can exchange sentences for a "week" in tests |
| **3. API + persistence** ✅ in review (staging deploy: your Neon/Render accounts, see [deploy.md](deploy.md)) | FastAPI, Postgres, Alembic, OIDC sign-in, authorisation, rate limits, OpenAPI, staging deploy | L | Staging passes OWASP API Top 10 checks; contract tests green |
| **4. Mobile MVP** 🚧 part 1 (online loop) and Google/Apple sign-in in review; next: offline sync, audio | Flutter: onboarding, invite partner, add sentence + audio, daily review, corrections, offline sync | L | You and your friend use it daily for 2 weeks (dogfood) |
| **5. Content sources** | Tatoeba import, Wiktionary lookup, share-sheet capture, URL capture, then the collection worker | M–L | Each source runs as an isolated adapter with its guardrails (ADR 0006) |
| **6. Launch hardening** | MASVS review/pen test, privacy policy, in-app account deletion, report/block, moderation queue, load test, backup restore drill, store review | M | Every item in [launch checklist](security/baseline.md#launch-checklist) ticked |
| **7. Launch + iterate** | Privacy-respecting analytics, the features in section 7, more languages | ongoing | |

The order is deliberate: domain first (cheap to change, fully testable),
then the API, then the UI. Pair learning ships before external content
because it is what makes the app different.

## 6. Engineering practices

- **Trunk-based development**: short-lived branches, small PRs, squash merge, branch protection, at least CI + one review (or a self-review checklist when solo).
- **ADRs** for every decision that is costly to reverse (`docs/adr/`).
- **Test pyramid**: fast domain unit tests (TDD), property-based tests for the scheduler and matching (Hypothesis), contract tests between API and the Flutter client generated from OpenAPI, a thin layer of end-to-end tests.
- **Quality gates in CI**: ruff, mypy `--strict`, import-linter, pytest with ≥ 90% branch coverage on domain/application, bandit, pip-audit, gitleaks.
- **12-factor config**: settings from environment variables, secrets from a secret manager, never in git. Separate dev / staging / prod.
- **Observability**: structured JSON logs without personal data, OpenTelemetry traces, error tracking (Sentry or similar) with data scrubbing.
- **Feature flags** for anything risky (e.g. each external source has a kill switch).
- **Definition of done**: tests, types, docs/ADR if needed, security checklist questions answered in the PR template, works offline on the client if user-facing.

## 7. Feature ideas

Ranked by how much they help learning per unit of effort. ★ = candidate for MVP.

**Pair learning**
1. ★ **Daily exchange.** Each partner adds 3 sentences a day with their own voice recording and a "when do you say this?" note (formal/informal, dialect, slang). The partner gets them as practice the same day.
2. ★ **Correct my sentence.** You write a sentence in Bosnian; your friend corrects it with an inline diff and a voice note. The corrected version becomes your review card, so your own mistakes become your lessons.
3. ★ **Shared streak with "cover for me".** The streak belongs to the pair. If one partner misses a day, the other can save it by adding a bonus sentence. This builds cooperation, not competition.
4. **Teach-back.** Record yourself saying your partner's sentence; they rate your pronunciation with one tap. Speech scoring can pre-grade it later.
5. **Co-written dialogues.** Partners build a short dialogue line by line, each in their own language, then role-play it in a voice call.
6. **Weekly call with a ready agenda.** Schedule a 15-minute call; the app prepares a conversation plan from that week's sentences and corrections (the Preply-style lesson, free between friends).
7. **Circles.** One native speaker teaching several learners, or a family group, using the same model as pairs.

**Real-life input**
8. ★ **Capture from anywhere.** Share a post, reel, video timestamp or web page into the app; it saves the sentence, a link and the creator's name. Photo OCR for signs and menus.
9. **Follow teaching creators.** Follow public teaching accounts; new posts show up as suggested snippets to save (needs the collection worker, ADR 0006).
10. **Picture-first cards for beginners.** The teacher attaches a photo instead of a translation, so meaning comes from context.

**Smart practice**
11. ★ **Kind answer checking.** Already built: accepts Latin or Cyrillic for Bosnian, ignores harakat and letter variants for Arabic, and marks "almost right" answers as CLOSE with a hint.
12. **Mistake fingerprint.** Tracks your recurring errors (ć/č, noun cases, Arabic gender agreement) and generates targeted drills.
13. **Grammar lenses.** Tap a Bosnian noun to see its case table; tap an Arabic word to see its root family (ك ت ب → كتاب، مكتب، كاتب).
14. **AI helper, clearly labelled.** Explains the grammar of your partner's sentence and suggests variations. The partner approves before anything becomes a card, so the human stays the authority.
15. **Hands-free commute mode.** Audio-only listen-and-repeat sessions that work offline.
16. **Can-do map.** Progress shown as CEFR can-do statements ("I can introduce my family") instead of points.

**Motivation**
17. **Partner's sentence of the day** in a home-screen widget.
18. **Teaching counts.** Teaching earns progress too, because explaining your own language deepens your understanding of it.

## 8. About plugins for social media

No Claude plugin is needed or would help here. Plugins extend my tools
while I work; they do not run inside your app. At run time the app needs its
**own adapters** (ADR 0006). In order of preference:

1. **oEmbed / embeds** (YouTube, TikTok, Instagram via Meta's oEmbed with app review): show the original post inside the app with attribution instead of copying it. This is the safest legally.
2. **Official APIs**: YouTube Data API (search channels, captions where permitted), RSS feeds, Wiktionary/Wikidata, Tatoeba exports (CC-BY).
3. **HTML collection** of public pages as the last resort, under the guardrails in ADR 0006.

## 9. Open questions for you

1. How many hours a week can you put in, and is anyone else coding?
2. Arabic: Modern Standard Arabic, a dialect, or both (which one do you speak)?
3. Minimum user age (13+ or 16+)? This drives consent rules (COPPA, GDPR).
4. Which countries first? EU users mean GDPR applies in full.
5. Money: free, freemium, or subscription? This affects store setup and the data model.
6. ~~Hosting budget~~ Decided: free tiers for now (ADR 0010). Budget needed later for the Apple Developer Program ($99/year) and Google Play ($25 once).
7. Is the app name decided? `langex` is a placeholder.
8. Which social accounts and sites do you want first? We can ask those creators for permission, which removes most of the legal risk.
