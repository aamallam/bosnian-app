import pytest

from langex.languages.domain.matching import MatchLevel, compare_answer
from langex.languages.domain.profile import LanguageProfile
from langex.languages.profiles.arabic import PROFILE as ARABIC
from langex.languages.profiles.bosnian import PROFILE as BOSNIAN
from langex.languages.profiles.english import PROFILE as ENGLISH
from langex.shared_kernel.language import LanguageCode


@pytest.mark.parametrize(
    ("expected", "given", "level"),
    [
        ("Dobar dan.", "dobar dan", MatchLevel.EXACT),
        ("Dobar   dan!", "Dobar dan", MatchLevel.EXACT),
        ("Добар дан.", "Dobar dan", MatchLevel.EXACT),  # Cyrillic vs Latin
        ("Kako si?", "Како си", MatchLevel.EXACT),
        ("Laku noć", "laku noc", MatchLevel.CLOSE),
        ("Đak", "dak", MatchLevel.CLOSE),  # đ has no Unicode decomposition
        ("Ćevapi", "Ћевапи", MatchLevel.EXACT),
        ("Dobar dan", "Dobro jutro", MatchLevel.WRONG),
    ],
)
def test_bosnian_matching(expected: str, given: str, level: MatchLevel) -> None:
    assert compare_answer(BOSNIAN, expected, given) is level


@pytest.mark.parametrize(
    ("expected", "given", "level"),
    [
        ("مرحبا", "مرحبا", MatchLevel.EXACT),
        ("مرحـــبا", "مرحبا", MatchLevel.EXACT),  # tatweel ignored
        ("كيف حالك؟", "كيف حالك", MatchLevel.EXACT),  # Arabic question mark
        ("مَرْحَبًا", "مرحبا", MatchLevel.CLOSE),  # harakat
        ("أنا", "انا", MatchLevel.CLOSE),  # hamza on alef
        ("مدرسة", "مدرسه", MatchLevel.CLOSE),  # taa marbuta
        ("شكرا", "مرحبا", MatchLevel.WRONG),
    ],
)
def test_arabic_matching(expected: str, given: str, level: MatchLevel) -> None:
    assert compare_answer(ARABIC, expected, given) is level


def test_english_uses_base_rules() -> None:
    assert compare_answer(ENGLISH, "Café", "cafe") is MatchLevel.CLOSE
    assert compare_answer(ENGLISH, "Hello, world!", "hello world") is MatchLevel.EXACT


def test_generic_profile_still_matches() -> None:
    turkish = LanguageProfile.generic(LanguageCode("tr"))
    assert compare_answer(turkish, "Günaydın", "gunaydın") is MatchLevel.CLOSE
