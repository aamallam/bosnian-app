"""Grade a typed answer against the expected text."""

from __future__ import annotations

from enum import StrEnum

from langex.languages.domain.profile import LanguageProfile


class MatchLevel(StrEnum):
    EXACT = "exact"  # same apart from case, spacing, punctuation
    CLOSE = "close"  # right word, wrong or missing diacritics: accept, but point it out
    WRONG = "wrong"


def compare_answer(profile: LanguageProfile, expected: str, given: str) -> MatchLevel:
    normalizer = profile.normalizer
    if normalizer.strict(expected) == normalizer.strict(given):
        return MatchLevel.EXACT
    if normalizer.lenient(expected) == normalizer.lenient(given):
        return MatchLevel.CLOSE
    return MatchLevel.WRONG
