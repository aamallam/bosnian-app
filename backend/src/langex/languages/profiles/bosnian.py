"""Bosnian: written in both Latin and Cyrillic; answers in either script count."""

from __future__ import annotations

from langex.languages.domain.normalization import BaseNormalizer
from langex.languages.domain.profile import LanguageProfile, TextDirection
from langex.shared_kernel.language import LanguageCode

_CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ђ": "đ", "е": "e",
    "ж": "ž", "з": "z", "и": "i", "ј": "j", "к": "k", "л": "l", "љ": "lj",
    "м": "m", "н": "n", "њ": "nj", "о": "o", "п": "p", "р": "r", "с": "s",
    "т": "t", "ћ": "ć", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "č",
    "џ": "dž", "ш": "š",
}  # fmt: skip
_CYRILLIC_TABLE = str.maketrans(_CYRILLIC_TO_LATIN)

# 'đ' has no Unicode decomposition, so generic diacritic stripping misses it.
_LENIENT_TABLE = str.maketrans({"đ": "d"})


def to_latin(text: str) -> str:
    """Transliterate Bosnian Cyrillic to Latin (expects lower case input)."""
    return text.translate(_CYRILLIC_TABLE)


class BosnianNormalizer(BaseNormalizer):
    def strict(self, text: str) -> str:
        return to_latin(super().strict(text))

    def lenient(self, text: str) -> str:
        return super().lenient(text).translate(_LENIENT_TABLE)


PROFILE = LanguageProfile(
    code=LanguageCode("bs"),
    english_name="Bosnian",
    native_name="bosanski",
    direction=TextDirection.LTR,
    scripts=("Latn", "Cyrl"),
    normalizer=BosnianNormalizer(),
)
