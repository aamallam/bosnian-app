import pytest

from langex.languages.adapters.entry_points import discover_profiles
from langex.languages.application.registry import LanguageRegistry
from langex.languages.domain.profile import LanguageProfile, TextDirection
from langex.languages.profiles.arabic import PROFILE as ARABIC
from langex.languages.profiles.bosnian import PROFILE as BOSNIAN
from langex.shared_kernel.language import LanguageCode


def test_returns_registered_profile() -> None:
    registry = LanguageRegistry([BOSNIAN, ARABIC])
    assert registry.get(LanguageCode("ar")) is ARABIC
    assert registry.get(LanguageCode("ar")).direction is TextDirection.RTL


def test_unknown_language_gets_generic_profile() -> None:
    registry = LanguageRegistry([BOSNIAN])
    profile = registry.get(LanguageCode("tr"))

    assert profile.code == LanguageCode("tr")
    assert not registry.is_supported(LanguageCode("tr"))


def test_rejects_duplicate_registration() -> None:
    registry = LanguageRegistry([BOSNIAN])
    with pytest.raises(ValueError, match="already registered"):
        registry.register(BOSNIAN)


def test_lists_profiles_sorted_by_name() -> None:
    registry = LanguageRegistry([BOSNIAN, ARABIC])
    assert [p.english_name for p in registry.all()] == ["Arabic", "Bosnian"]


def test_profile_requires_names_and_scripts() -> None:
    with pytest.raises(ValueError, match="names"):
        LanguageProfile(LanguageCode("xx"), " ", "x", TextDirection.LTR, ("Latn",))
    with pytest.raises(ValueError, match="script"):
        LanguageProfile(LanguageCode("xx"), "X", "x", TextDirection.LTR, ())


def test_built_in_profiles_are_discovered_as_plugins() -> None:
    codes = {str(p.code) for p in discover_profiles()}
    assert {"bs", "ar", "en"} <= codes
