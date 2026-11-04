# 3. Languages as plugins

Date: 2026-11-04
Status: Proposed

## Context
The first pair is Bosnian ⇄ Arabic, but any pair must work. Languages differ
in ways that matter to a learning app: script (Bosnian uses Latin and
Cyrillic), direction (Arabic is right-to-left), optional diacritics (Arabic
harakat), letter variants, and later tokenisation, plural rules,
transliteration and text-to-speech voices.

## Decision
- A language is identified by an ISO 639 `LanguageCode` and is otherwise **data**.
- A `LanguageProfile` holds names, direction, scripts (ISO 15924) and a
  `TextNormalizer` with `strict` and `lenient` levels. `compare_answer`
  grades answers as EXACT / CLOSE / WRONG using that normalizer.
- Profiles are discovered through the `langex.languages` entry-point group,
  so a new language can ship as its own package with no change to core code.
- Unknown codes get `LanguageProfile.generic`, so users can start any pair
  on day one and a richer profile can follow later without data migration.
- New per-language capabilities are added as optional fields on the
  profile with sensible defaults, never as `if language == "ar"` checks in other contexts.

## Consequences
- Adding Turkish is one file plus tests, or a separate package.
- Language rules are unit-tested in isolation (see `tests/languages/`).
- The profile interface must be designed with care, since plugins depend on it; it will be versioned once outside packages exist.
