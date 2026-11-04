"""Text normalization used to compare a learner's answer with the expected one.

Two levels:
- strict:  ignores case, spacing and punctuation only
- lenient: also ignores accents and diacritics

Languages override these to add their own rules (scripts, letter variants).
"""

from __future__ import annotations

import unicodedata
from typing import Protocol


class TextNormalizer(Protocol):
    def strict(self, text: str) -> str: ...

    def lenient(self, text: str) -> str: ...


def _strip_punctuation(text: str) -> str:
    return "".join(ch for ch in text if not unicodedata.category(ch).startswith("P"))


def _collapse_spaces(text: str) -> str:
    return " ".join(text.split())


def strip_combining_marks(text: str) -> str:
    """Remove accents and diacritics, e.g. 'č' -> 'c', 'أ' -> 'ا'."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return unicodedata.normalize("NFC", stripped)


class BaseNormalizer:
    """Rules that hold for every language."""

    def strict(self, text: str) -> str:
        text = unicodedata.normalize("NFC", text).casefold()
        return _collapse_spaces(_strip_punctuation(text))

    def lenient(self, text: str) -> str:
        return strip_combining_marks(self.strict(text))
