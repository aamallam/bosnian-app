# Threat model (STRIDE)

Status: v0.1, 2026-11-04. Revisit at the start of every phase and whenever a new external integration is added.

## System and trust boundaries

```
[Mobile app] ──TLS──▶ [API (FastAPI)] ──▶ [Postgres]
     │                     │  └──────────▶ [Object storage: audio, images]
     │                     ▼
     │               [Outbox / queue] ──▶ [Worker: ingestion, transcoding]
     │                                          │
     └── Apple / Google sign-in                 └──▶ [Internet: sites, social, APIs]
```

Boundaries: device ↔ API; API ↔ identity providers; worker ↔ internet (fully untrusted);
users ↔ each other (partners are not trusted with each other's data beyond the pair).

## Assets

Accounts and tokens; voice recordings (biometric-adjacent); messages and corrections
between partners; age and consent records; the content collection itself; signing keys and cloud credentials.

## Threats and controls

| STRIDE | Threat | Control |
|---|---|---|
| Spoofing | Stolen refresh token reused | Rotation with reuse detection, device binding, revoke-all |
| Spoofing | Forged provider ID token | Verify signature against provider JWKS, `iss`, `aud`, `exp`, `nonce` |
| Tampering | User edits a partner's contribution or another pair's data (BOLA/IDOR) | Ownership check in every use case; random UUIDs; authorisation tests per endpoint |
| Tampering | Malicious uploaded audio/image | Size and type limits, re-encode server-side, strip metadata (EXIF GPS), private bucket |
| Repudiation | "I never sent that" in harassment cases | Append-only audit log of moderation-relevant actions |
| Info disclosure | Personal data in logs or error tracking | Structured logging with allowlisted fields; scrubbing in error tracker |
| Info disclosure | Public guessable media URLs | Short-lived signed URLs only |
| Info disclosure | Sensitive data on a lost phone | Tokens in Keychain/Keystore; encrypted local DB for messages; no data in screenshots of the app switcher for sensitive screens |
| DoS | Invite-code brute force, spam sentences | Rate limits per user/IP, long random invite codes, expiry, quotas |
| DoS | Worker fetches huge or slow pages | Timeouts, size caps, per-host concurrency limits |
| Elevation | SSRF via user-submitted URL reaching cloud metadata or internal services | HTTPS only, DNS resolution with private-range block re-checked after redirects, egress firewall for the worker |
| Elevation | Stored XSS from scraped HTML shown in the app | Store plain text excerpts; sanitise any rich text; the app never renders remote HTML in a privileged webview |
| Elevation | Compromised dependency (supply chain) | Locked and hashed dependencies, pip-audit, Dependabot, minimal dependencies, CI with read-only token, actions pinned to SHA |
| Abuse | Adults contacting minors through public pairing | Age gate; minors limited to invite-only pairs; report/block; moderation queue |
| Abuse | Harassment or explicit content in sentences or audio | Report/block, automated text screening, human review queue, ban tooling |
