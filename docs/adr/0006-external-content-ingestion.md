# 6. External content ingestion

Date: 2026-11-04
Status: Proposed. **Needs legal review before public launch.**

## Context
Learners should get material from dictionaries, web pages and public
social-media accounts that teach Bosnian or Arabic. The product owner chose
automated collection from public accounts.

Risks that come with that choice:
- **Platform terms.** Instagram, TikTok, Facebook and X forbid automated
  collection in their terms. Accounts, IP ranges or the app itself can be
  blocked, and Meta and X have sued scrapers.
- **Copyright.** Posts belong to their creators. Storing and re-showing them
  in a commercial app needs a licence or a narrow legal exception.
- **Personal data (GDPR).** Account names, faces and voices are personal data,
  even when public.
- **App-store review.** Apple and Google reject apps that redistribute
  content without rights.
- **Security.** Fetching URLs that users or third parties supply opens the
  door to SSRF, malicious HTML and oversized files.

## Decision
Each source is an adapter behind a `ContentSource` port in the `content`
context, run in a separate worker, never in the API process. Sources are
tried in this order, and an adapter is only built when the one before it cannot serve the need:

1. **Embeds / oEmbed** (YouTube, TikTok, Instagram): show the original post, with attribution, inside the app.
2. **Official APIs and open data**: YouTube Data API, RSS, Wiktionary/Wikidata, Tatoeba (CC-BY).
3. **User-initiated capture**: a user shares a post or URL; we store the user's own excerpt, the link and the creator's name.
4. **Automated collection of public pages**, under all of these guardrails:
   - an **allowlist** of accounts and sites, each with an owner, a reason and, where possible, the creator's written permission;
   - honour `robots.txt`; no log-in; no bypassing CAPTCHAs, paywalls or rate limits; no rotating proxies or fake user agents; identify our bot honestly;
   - strict per-host rate limits and backoff;
   - store only the short excerpt needed for learning, a link and attribution; no re-hosting of images, audio or video;
   - a **takedown** process (in-app and email) handled within 72 hours, and removal on request;
   - a **kill switch** feature flag per source, off by default in production until legal sign-off.

SSRF and parsing controls for every fetch: only `https`, resolve DNS and block
private, loopback and link-local ranges (re-checked after redirects), at most
3 redirects, 5 s timeout, 2 MB limit, allowed content types only, HTML
parsed without executing scripts and sanitised before storage.

## Consequences
- Lower legal and operational risk than unrestricted scraping, while still
  pulling in fresh real-life content.
- Asking creators for permission doubles as marketing and partnerships.
- Some platforms will offer only embeds; that is accepted.
