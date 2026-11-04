"""Scheduler port backed by the reference FSRS implementation (py-fsrs, MIT).

We use the maintained library instead of re-implementing the maths. Only this
module imports it, so swapping or upgrading the algorithm touches one file.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import fsrs

from langex.learning.domain.card import MemoryState, Phase, Rating, ReviewCard

_TO_FSRS_STATE = {
    Phase.LEARNING: fsrs.State.Learning,
    Phase.REVIEW: fsrs.State.Review,
    Phase.RELEARNING: fsrs.State.Relearning,
}
_FROM_FSRS_STATE = {value: key for key, value in _TO_FSRS_STATE.items()}


class FsrsScheduler:
    def __init__(
        self,
        desired_retention: float = 0.9,
        parameters: Sequence[float] | None = None,
        enable_fuzzing: bool = True,
        maximum_interval_days: int = 36500,
    ) -> None:
        if not 0.7 <= desired_retention <= 0.97:
            raise ValueError("Desired retention must be between 0.7 and 0.97")
        kwargs: dict[str, object] = {}
        if parameters is not None:  # per-learner optimised weights, later
            kwargs["parameters"] = tuple(parameters)
        self._scheduler = fsrs.Scheduler(
            desired_retention=desired_retention,
            enable_fuzzing=enable_fuzzing,
            maximum_interval=maximum_interval_days,
            **kwargs,  # type: ignore[arg-type]
        )

    def schedule(self, card: ReviewCard, rating: Rating, reviewed_at: datetime) -> ReviewCard:
        updated, _ = self._scheduler.review_card(
            _to_fsrs(card), fsrs.Rating(int(rating)), review_datetime=reviewed_at
        )
        memory = MemoryState(
            phase=_FROM_FSRS_STATE[updated.state],
            step=updated.step,
            stability=updated.stability,
            difficulty=updated.difficulty,
        )
        return card.rescheduled(memory=memory, due=updated.due, reviewed_at=reviewed_at)

    def retrievability(self, card: ReviewCard, at: datetime) -> float:
        return float(self._scheduler.get_card_retrievability(_to_fsrs(card), current_datetime=at))


def _to_fsrs(card: ReviewCard) -> fsrs.Card:
    return fsrs.Card(
        state=_TO_FSRS_STATE[card.memory.phase],
        step=card.memory.step,
        stability=card.memory.stability,
        difficulty=card.memory.difficulty,
        due=card.due,
        last_review=card.last_review,
    )
