"""Registry of known language profiles."""

from __future__ import annotations

from collections.abc import Iterable

from langex.languages.domain.profile import LanguageProfile
from langex.shared_kernel.language import LanguageCode


class LanguageRegistry:
    """Looks up profiles by code; unknown languages get a generic profile."""

    def __init__(self, profiles: Iterable[LanguageProfile] = ()) -> None:
        self._profiles: dict[LanguageCode, LanguageProfile] = {}
        for profile in profiles:
            self.register(profile)

    def register(self, profile: LanguageProfile) -> None:
        if profile.code in self._profiles:
            raise ValueError(f"Language {profile.code} is already registered")
        self._profiles[profile.code] = profile

    def get(self, code: LanguageCode) -> LanguageProfile:
        return self._profiles.get(code) or LanguageProfile.generic(code)

    def is_supported(self, code: LanguageCode) -> bool:
        return code in self._profiles

    def all(self) -> tuple[LanguageProfile, ...]:
        return tuple(sorted(self._profiles.values(), key=lambda p: p.english_name))
