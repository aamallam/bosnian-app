"""Pairing use cases. Every method takes the acting user first and checks
that they may act on the pair or attempt before doing anything else."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from langex.pairing.application.ports import (
    AttemptRepository,
    ContributionRepository,
    InvitationRepository,
    PairRepository,
)
from langex.pairing.domain.errors import (
    AttemptNotFoundError,
    DailyLimitReachedError,
    InvitationError,
    PairNotFoundError,
)
from langex.pairing.domain.events import AttemptCorrected, ContributionAdded, PairFormed
from langex.pairing.domain.exchange import (
    MAX_NOTE_LENGTH,
    Attempt,
    Contribution,
    clean_optional,
    clean_text,
)
from langex.pairing.domain.invitation import Invitation, hash_code
from langex.pairing.domain.pair import Pair
from langex.pairing.domain.streak import DailyGoal, current_streak
from langex.shared_kernel.clock import Clock
from langex.shared_kernel.events import EventPublisher
from langex.shared_kernel.language import LanguageCode

MAX_CONTRIBUTIONS_PER_DAY = 50  # anti-spam ceiling, far above any learning goal
STREAK_LOOKBACK = timedelta(days=366)


class PairingService:
    def __init__(
        self,
        invitations: InvitationRepository,
        pairs: PairRepository,
        contributions: ContributionRepository,
        attempts: AttemptRepository,
        events: EventPublisher,
        clock: Clock,
        goal: DailyGoal | None = None,
    ) -> None:
        self._invitations = invitations
        self._pairs = pairs
        self._contributions = contributions
        self._attempts = attempts
        self._events = events
        self._clock = clock
        self._goal = goal or DailyGoal()

    # -------------------------------------------------------------- pairs
    def invite(self, user_id: UUID, teaches: LanguageCode, learns: LanguageCode) -> str:
        """Create an invitation and return its one-time code."""
        invitation, code = Invitation.issue(user_id, teaches, learns, self._clock.now())
        self._invitations.add(invitation)
        return code

    def accept(self, user_id: UUID, code: str) -> Pair:
        invitation = self._invitations.find_by_code_hash(hash_code(code))
        if invitation is None:
            raise InvitationError("This invitation is not valid")
        redeemed, pair = invitation.redeem(user_id, self._clock.now())
        self._invitations.save(redeemed)
        self._pairs.add(pair)
        first, second = pair.members
        self._events.publish(
            PairFormed(pair_id=pair.id, member_ids=(first.user_id, second.user_id))
        )
        return pair

    def pairs_of(self, user_id: UUID) -> list[Pair]:
        return self._pairs.for_member(user_id)

    def _pair_for(self, user_id: UUID, pair_id: UUID) -> Pair:
        pair = self._pairs.get(pair_id)
        if pair is None or not pair.is_member(user_id):
            raise PairNotFoundError(pair_id)
        return pair

    # ------------------------------------------------------- teaching
    def contribute(
        self,
        user_id: UUID,
        pair_id: UUID,
        text: str,
        gloss: str | None = None,
        gloss_language: LanguageCode | None = None,
        note: str | None = None,
    ) -> Contribution:
        pair = self._pair_for(user_id, pair_id)
        now = self._clock.now()
        if (
            self._contributions.count_by_author_since(user_id, now - timedelta(days=1))
            >= MAX_CONTRIBUTIONS_PER_DAY
        ):
            raise DailyLimitReachedError(MAX_CONTRIBUTIONS_PER_DAY)
        cleaned_gloss = clean_optional(gloss, "Gloss", 500)
        contribution = Contribution(
            id=uuid4(),
            pair_id=pair.id,
            author_id=user_id,
            learner_id=pair.partner_of(user_id).user_id,
            language=pair.membership_of(user_id).teaches,
            text=clean_text(text, "Sentence"),
            created_at=now,
            gloss=cleaned_gloss,
            gloss_language=gloss_language if cleaned_gloss is not None else None,
            note=clean_optional(note, "Note", MAX_NOTE_LENGTH),
        )
        self._contributions.add(contribution)
        self._events.publish(
            ContributionAdded(
                pair_id=pair.id,
                contribution_id=contribution.id,
                author_id=user_id,
                learner_id=contribution.learner_id,
                language=contribution.language,
            )
        )
        return contribution

    def contributions(self, user_id: UUID, pair_id: UUID, since: datetime) -> list[Contribution]:
        pair = self._pair_for(user_id, pair_id)
        return self._contributions.for_pair(pair.id, since)

    # ------------------------------------------------------ practising
    def submit_attempt(self, user_id: UUID, pair_id: UUID, text: str) -> Attempt:
        pair = self._pair_for(user_id, pair_id)
        attempt = Attempt(
            id=uuid4(),
            pair_id=pair.id,
            learner_id=user_id,
            reviewer_id=pair.partner_of(user_id).user_id,
            language=pair.membership_of(user_id).learns,
            text=clean_text(text, "Sentence"),
            created_at=self._clock.now(),
        )
        self._attempts.add(attempt)
        return attempt

    def my_attempts(self, user_id: UUID, pair_id: UUID) -> list[Attempt]:
        """This user's own attempts in a pair, with corrections once given."""
        pair = self._pair_for(user_id, pair_id)
        return self._attempts.by_learner(pair.id, user_id)

    def to_review(self, user_id: UUID) -> list[Attempt]:
        """Attempts waiting for this user's correction."""
        return self._attempts.awaiting_review_by(user_id)

    def correct(
        self, user_id: UUID, attempt_id: UUID, corrected_text: str, comment: str | None = None
    ) -> Attempt:
        attempt = self._attempts.get(attempt_id)
        if attempt is None or not attempt.visible_to(user_id):
            raise AttemptNotFoundError(attempt_id)
        corrected = attempt.corrected(user_id, corrected_text, comment, self._clock.now())
        self._attempts.save(corrected)
        self._events.publish(
            AttemptCorrected(
                pair_id=corrected.pair_id,
                attempt_id=corrected.id,
                learner_id=corrected.learner_id,
                language=corrected.language,
            )
        )
        return corrected

    # ---------------------------------------------------------- streak
    def streak(self, user_id: UUID, pair_id: UUID) -> int:
        pair = self._pair_for(user_id, pair_id)
        now = self._clock.now()
        counts: defaultdict[date, defaultdict[UUID, int]] = defaultdict(lambda: defaultdict(int))
        for contribution in self._contributions.for_pair(pair.id, now - STREAK_LOOKBACK):
            counts[contribution.created_at.date()][contribution.author_id] += 1
        members = [m.user_id for m in pair.members]
        return current_streak(self._goal, members, counts, now.date())
