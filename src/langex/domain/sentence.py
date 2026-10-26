"""Sentence entity for the domain layer."""

from __future__ import annotations

from dataclasses import dataclass

from langex.domain.language import LanguageCode
from langex.domain.source import SourceType

MAX_TEXT_LENGTH = 500


@dataclass(frozen=True, slots=True)
class Sentence:
    """A sentence in one language, with its origin and translations."""

    text: str
    language: LanguageCode
    source: SourceType
    translations: tuple[Sentence, ...] = ()

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Sentence text must not be empty")
        if self.text != self.text.strip():
            raise ValueError("Sentence text must not have leading or trailing spaces")
        if len(self.text) > MAX_TEXT_LENGTH:
            raise ValueError(f"Sentence text must be at most {MAX_TEXT_LENGTH} characters")
        for translation in self.translations:
            if translation.language == self.language:
                raise ValueError("A translation must be in a different language")

    def translation_in(self, language: LanguageCode) -> Sentence | None:
        """Return the first translation in the given language, or None."""
        for translation in self.translations:
            if translation.language == language:
                return translation
        return None