"""Discover language profiles installed as plugins.

Any installed package can add a language by declaring, in its pyproject:

    [project.entry-points."langex.languages"]
    tr = "langex_turkish:PROFILE"
"""

from __future__ import annotations

from importlib.metadata import entry_points

from langex.languages.domain.profile import LanguageProfile

ENTRY_POINT_GROUP = "langex.languages"


def discover_profiles() -> list[LanguageProfile]:
    profiles: list[LanguageProfile] = []
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        profile = entry_point.load()
        if not isinstance(profile, LanguageProfile):
            raise TypeError(f"Entry point {entry_point.name!r} is not a LanguageProfile")
        if str(profile.code) != entry_point.name:
            raise ValueError(f"Entry point {entry_point.name!r} points to profile {profile.code!r}")
        profiles.append(profile)
    return profiles
