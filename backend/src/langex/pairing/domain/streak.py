"""The shared streak: it belongs to the pair, not to one person.

A day counts when both partners reach the daily goal. If one partner misses,
the other can cover by adding twice the goal; covers cannot happen two days
in a row, so one person cannot carry the pair alone.

Days are UTC dates for now; they become the pair's agreed timezone later.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from uuid import UUID


class DayStatus(StrEnum):
    MET = "met"
    COVERED = "covered"
    MISSED = "missed"


@dataclass(frozen=True, slots=True)
class DailyGoal:
    sentences_per_day: int = 3

    def __post_init__(self) -> None:
        if not 1 <= self.sentences_per_day <= 20:
            raise ValueError("The daily goal must be between 1 and 20 sentences")

    def day_status(self, counts: Mapping[UUID, int], members: Collection[UUID]) -> DayStatus:
        goal = self.sentences_per_day
        reached = [counts.get(m, 0) >= goal for m in members]
        if all(reached):
            return DayStatus.MET
        if any(counts.get(m, 0) >= 2 * goal for m in members):
            return DayStatus.COVERED
        return DayStatus.MISSED


def current_streak(
    goal: DailyGoal,
    members: Collection[UUID],
    counts_by_day: Mapping[date, Mapping[UUID, int]],
    today: date,
) -> int:
    """Consecutive counted days ending today, or yesterday if today is still open."""
    statuses: list[DayStatus] = []
    day = today
    while True:
        status = goal.day_status(counts_by_day.get(day, {}), members)
        if day == today and status is DayStatus.MISSED:
            day -= timedelta(days=1)  # today is not over yet
            continue
        if status is DayStatus.MISSED:
            break
        if status is DayStatus.COVERED and statuses and statuses[-1] is DayStatus.COVERED:
            break  # second cover in a row: the streak breaks
        statuses.append(status)
        day -= timedelta(days=1)
    return len(statuses)
