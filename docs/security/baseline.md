# Security baseline

Standards we follow:
- **OWASP ASVS 4 Level 2** for the backend API
- **OWASP API Security Top 10** checks for every endpoint
- **OWASP MASVS** (L1, plus resilience basics) for the Flutter app
- **GDPR** principles: data minimisation, purpose limitation, the right to export and delete

## Rules for every change

1. **Validate at the edge, enforce in the domain.** Pydantic validates input
   shape; domain objects enforce invariants (see `Sentence`, `LanguageCode`).
2. **Authorise every object access** in the use case, not just in the route.
3. **No secrets in code or git.** Environment variables locally, a secret
   manager in staging and prod. gitleaks runs in pre-commit and CI.
4. **Parameterised queries only** (SQLAlchemy); no string-built SQL.
5. **Least privilege**: database roles per service, read-only CI token,
   private buckets, egress-restricted worker.
6. **Log events, not people**: IDs and actions, never message text, audio, emails or tokens.
7. **Dependencies are a liability**: justify each new one in the PR; keep them locked and audited.
8. **Crypto**: TLS 1.2+ everywhere, HSTS, encryption at rest (managed DB and
   storage), no home-made crypto.
9. **Errors**: generic messages to clients, details only in server logs.
10. **Security tests sit beside features**: an authorisation test for every
    new endpoint, an abuse case for every new user-to-user feature.

## Data handling

| Data | Where | Retention |
|---|---|---|
| Account (provider subject ID, email, display name, birth year) | Postgres `identity` | Until deletion |
| Sentences, corrections, notes | Postgres `content`/`pairing` | Until deletion; partner keeps an anonymised copy of what they learned only if both agreed |
| Voice recordings | Private object storage | Until deletion |
| Review history | Postgres `learning` | Until deletion |
| Logs | Log store | 30 days, no personal content |
| Backups | Encrypted, separate account | 30 days, restore tested every quarter |

## Launch checklist

- [ ] Independent MASVS/ASVS review or pen test of staging; all high findings fixed
- [ ] Authorisation tests cover 100% of endpoints
- [ ] Privacy policy and terms published; data processing records written
- [ ] In-app account deletion and data export working
- [ ] Age gate and minor protections in place
- [ ] Report/block and moderation queue staffed
- [ ] Legal sign-off on ADR 0006 sources, or automated collection kept switched off
- [ ] Incident response runbook and on-call contact
- [ ] Backup restore drill done
- [ ] Load test at 10× expected launch traffic
- [ ] Store review notes prepared (Sign in with Apple, content rights, account deletion)
