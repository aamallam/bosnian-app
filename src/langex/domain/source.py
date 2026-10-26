"""Where a sentence came from."""

from enum import StrEnum


class SourceType(StrEnum):
    """Origin of a sentence. Each value matches one adapter."""

    TATOEBA = "tatoeba"
    MANUAL = "manual"
    COMMUNITY = "community"
    WEB = "web"
    AI = "ai"