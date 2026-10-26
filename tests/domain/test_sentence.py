from dataclasses import FrozenInstanceError

import pytest

from langex.domain.language import LanguageCode
from langex.domain.sentence import MAX_TEXT_LENGTH, Sentence
from langex.domain.source import SourceType

BOSNIAN = LanguageCode("bs")
ENGLISH = LanguageCode("en")


def test_creates_valid_sentence() -> None:
    sentence = Sentence("Dobar dan.", BOSNIAN, SourceType.MANUAL)

    assert sentence.text == "Dobar dan."
    assert sentence.language == BOSNIAN
    assert sentence.source is SourceType.MANUAL


@pytest.mark.parametrize("text", ["", "   "])
def test_rejects_empty_text(text: str) -> None:
    with pytest.raises(ValueError):
        Sentence(text, BOSNIAN, SourceType.MANUAL)


@pytest.mark.parametrize("text", [" Dobar dan.", "Dobar dan. "])
def test_rejects_surrounding_whitespace(text: str) -> None:
    with pytest.raises(ValueError):
        Sentence(text, BOSNIAN, SourceType.MANUAL)


def test_is_immutable() -> None:
    sentence = Sentence("Dobar dan.", BOSNIAN, SourceType.MANUAL)
    with pytest.raises(FrozenInstanceError):
        sentence.text = "Laku noć."  # type: ignore[misc]


def test_rejects_text_longer_than_limit() -> None:
    too_long = "a" * (MAX_TEXT_LENGTH + 1)
    with pytest.raises(ValueError):
        Sentence(too_long, BOSNIAN, SourceType.MANUAL)


def test_accepts_text_at_limit() -> None:
    text = "a" * MAX_TEXT_LENGTH
    sentence = Sentence(text, BOSNIAN, SourceType.MANUAL)
    assert len(sentence.text) == MAX_TEXT_LENGTH


def test_has_no_translations_by_default() -> None:
    sentence = Sentence("Dobar dan.", BOSNIAN, SourceType.MANUAL)
    assert sentence.translations == ()


def test_finds_translation_by_language() -> None:
    english = Sentence("Good day.", ENGLISH, SourceType.MANUAL)
    sentence = Sentence("Dobar dan.", BOSNIAN, SourceType.MANUAL, (english,))

    assert sentence.translation_in(ENGLISH) == english


def test_returns_none_when_translation_missing() -> None:
    sentence = Sentence("Dobar dan.", BOSNIAN, SourceType.MANUAL)
    assert sentence.translation_in(ENGLISH) is None


def test_rejects_translation_in_same_language() -> None:
    other_bosnian = Sentence("Zdravo.", BOSNIAN, SourceType.MANUAL)
    with pytest.raises(ValueError):
        Sentence("Dobar dan.", BOSNIAN, SourceType.MANUAL, (other_bosnian,))