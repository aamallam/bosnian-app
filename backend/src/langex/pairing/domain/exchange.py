"""What partners exchange: contributions (teaching) and attempts (practising)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from langex.pairing.domain.errors import AttemptNotFoundError, PairingError
from langex.shared_kernel.language import LanguageCode

MAX_TEXT_LENGTH = 500
MAX_NOTE_LENGTH = 1000


def clean_text(text: str, field: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        raise ValueError(f"{field} must not be empty")
    if len(cleaned) > max_length:
        raise ValueError(f"{field} must be at most {max_length} characters")
    return cleaned


def clean_optional(text: str | None, field: str, max_length: int) -> str | None:
    if text is None or not text.strip():
        return None
    return clean_text(text, field, max_length)


@dataclass(frozen=True, slots=True, kw_only=True)
class Contribution:
    """A sentence a native speaker adds for their partner to learn.

    `gloss` is the meaning in a bridge language both can read (often English);
    `note` says when and how the sentence is used (register, dialect, culture).
    """

    id: UUID
    pair_id: UUID
    author_id: UUID
    learner_id: UUID
    language: LanguageCode
    text: str
    created_at: datetime
    gloss: str | None = None
    gloss_language: LanguageCode | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if self.author_id == self.learner_id:
            raise ValueError("The author teaches someone else")
        if (self.gloss is None) != (self.gloss_language is None):
            raise ValueError("A gloss needs its language, and only a gloss has one")
        if self.gloss_language == self.language:
            raise ValueError("A gloss must be in a different language")


@dataclass(frozen=True, slots=True)
class Correction:
    corrected_text: str
    comment: str | None
    corrected_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class Attempt:
    """A learner's own sentence in the language they learn, for their native
    partner to correct. The corrected version becomes a review card."""

    id: UUID
    pair_id: UUID
    learner_id: UUID
    reviewer_id: UUID
    language: LanguageCode
    text: str
    created_at: datetime
    correction: Correction | None = None

    def __post_init__(self) -> None:
        if self.learner_id == self.reviewer_id:
            raise ValueError("Attempts are corrected by the partner")

    @property
    def is_correct_as_written(self) -> bool:
        return self.correction is not None and self.correction.corrected_text == self.text

    def visible_to(self, user_id: UUID) -> bool:
        return user_id in (self.learner_id, self.reviewer_id)

    def corrected(
        self, by: UUID, corrected_text: str, comment: str | None, now: datetime
    ) -> Attempt:
        if by != self.reviewer_id:
            raise AttemptNotFoundError(self.id)
        if self.correction is not None:
            raise PairingError("This attempt has already been corrected")
        correction = Correction(
            corrected_text=clean_text(corrected_text, "Correction"),
            comment=clean_optional(comment, "Comment", MAX_NOTE_LENGTH),
            corrected_at=now,
        )
        return replace(self, correction=correction)
