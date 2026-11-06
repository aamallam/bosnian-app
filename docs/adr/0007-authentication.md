# 7. Authentication and sessions

Date: 2026-11-04
Status: Proposed. Apple/Google sign-in and tokens implemented in ADR 0011;
email sign-in, device list, deletion and export still to do.

## Context
Public app. Storing passwords means taking on breach risk, reset flows and
credential stuffing. Apple requires Sign in with Apple when other social sign-in is offered.

## Decision
- Sign-in with **Apple** and **Google** (OpenID Connect, PKCE), plus **email
  magic link or passkey**. No password storage of our own.
- The backend validates provider ID tokens (issuer, audience, signature, expiry, nonce: server-issued and single-use, see ADR 0012)
  and issues its own **short-lived access token** (≤ 15 min) and a **rotating
  refresh token** with reuse detection; refresh tokens are stored hashed and
  bound to a device record that the user can revoke.
- Tokens on the device live in Keychain / Keystore only.
- **Authorisation is object-level**: every use case checks that the caller
  belongs to the pair or owns the item. This is tested for every endpoint
  (BOLA is the #1 OWASP API risk).
- Rate limits on sign-in, invite redemption and content creation.
- In-app **account deletion** and **data export** (Apple and GDPR requirements).

## Consequences
- No password database to leak.
- Relies on third-party identity providers; email login covers users without Apple/Google.
