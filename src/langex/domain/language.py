"""Language value object for the domain layer."""

from __future__ import annotations

import re
from dataclasses import dataclass

_ISO_639_PATTERN = re.compile(r"[a-z]{2,3}")


@dataclass(frozen=True, slots=True)
class LanguageCode:
    """An ISO 639 language code such as 'bs', 'en' or 'ar'.

    Languages are data, not code: any valid code is accepted,
    so adding a new language never requires changing this class.
    """

    value: str

    def __post_init__(self) -> None:
        if not _ISO_639_PATTERN.fullmatch(self.value):
            raise ValueError(f"Invalid ISO 639 language code: {self.value!r}")

    def __str__(self) -> str:
        return self.value