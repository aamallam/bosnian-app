from dataclasses import FrozenInstanceError

import pytest

from langex.domain.language import LanguageCode


@pytest.mark.parametrize("code", ["bs", "en", "ar", "bos"])
def test_accepts_valid_iso_codes(code: str) -> None:
    assert LanguageCode(code).value == code


@pytest.mark.parametrize("code", ["", "b", "BS", "bosn", "b1", " en","e n"])
def test_rejects_invalid_codes(code: str) -> None:
    with pytest.raises(ValueError):
        LanguageCode(code)


def test_codes_with_same_value_are_equal() -> None:
    assert LanguageCode("bs") == LanguageCode("bs")


def test_is_immutable() -> None:
    code = LanguageCode("bs")
    with pytest.raises(FrozenInstanceError):
        code.value = "en"  # type: ignore[misc]