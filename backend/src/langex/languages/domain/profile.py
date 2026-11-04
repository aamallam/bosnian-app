"""Language profile: everything the app needs to know about one language."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from langex.languages.domain.normalization import BaseNormalizer, TextNormalizer
from langex.shared_kernel.language import LanguageCode


class TextDirection(StrEnum):
    """Writing direction, used by clients to lay out text."""

    LTR = "ltr"
    RTL = "rtl"


@dataclass(frozen=True, slots=True)
class LanguageProfile:
    """Data describing a language, plus its text-matching rules.

    Scripts use ISO 15924 codes (e.g. "Latn", "Cyrl", "Arab").
    """

    code: LanguageCode
    english_name: str
    native_name: str
    direction: TextDirection
    scripts: tuple[str, ...]
    normalizer: TextNormalizer = field(default_factory=BaseNormalizer)

    def __post_init__(self) -> None:
        if not self.english_name.strip() or not self.native_name.strip():
            raise ValueError("Language names must not be empty")
        if not self.scripts:
            raise ValueError("A language needs at least one script")

    @classmethod
    def generic(cls, code: LanguageCode) -> LanguageProfile:
        """Fallback for a language that has no profile yet.

        Lets users start a pair in any language on day one; a richer
        profile can be added later without migrating data.
        """
        return cls(
            code=code,
            english_name=str(code),
            native_name=str(code),
            direction=TextDirection.LTR,
            scripts=("Zyyy",),  # ISO 15924 "undetermined"
        )
