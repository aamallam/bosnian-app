from datetime import date, timedelta
from uuid import uuid4

import pytest

from langex.pairing.domain.errors import AttemptNotFoundError, InvitationError, PairingError
from langex.pairing.domain.exchange import Attempt, Contribution, clean_text
from langex.pairing.domain.invitation import Invitation, hash_code
from langex.pairing.domain.pair import Membership, Pair
from langex.pairing.domain.streak import DailyGoal, DayStatus, current_streak
from tests.pairing.conftest import ARABIC, BOSNIAN, ENGLISH, START

# ---------------------------------------------------------------- pair


def test_pair_must_be_reciprocal() -> None:
    a, b = uuid4(), uuid4()
    with pytest.raises(ValueError, match="learn what the other teaches"):
        Pair(
            id=uuid4(),
            members=(Membership(a, ARABIC, BOSNIAN), Membership(b, ENGLISH, ARABIC)),
            created_at=START,
        )


def test_pair_needs_two_people() -> None:
    a = uuid4()
    with pytest.raises(ValueError, match="two different"):
        Pair(
            id=uuid4(),
            members=(Membership(a, ARABIC, BOSNIAN), Membership(a, BOSNIAN, ARABIC)),
            created_at=START,
        )


def test_member_cannot_teach_and_learn_same_language() -> None:
    with pytest.raises(ValueError, match="different languages"):
        Membership(uuid4(), ARABIC, ARABIC)


# ---------------------------------------------------------- invitation


def test_invitation_stores_only_a_hash_of_the_code() -> None:
    invitation, code = Invitation.issue(uuid4(), ARABIC, BOSNIAN, START)

    assert code not in invitation.code_hash
    assert invitation.code_hash == hash_code(code)
    assert len(code) >= 20


def test_codes_are_unique() -> None:
    codes = {Invitation.issue(uuid4(), ARABIC, BOSNIAN, START)[1] for _ in range(200)}
    assert len(codes) == 200


def test_redeeming_builds_the_mirror_membership() -> None:
    inviter, invitee = uuid4(), uuid4()
    invitation, _ = Invitation.issue(inviter, ARABIC, BOSNIAN, START)

    used, pair = invitation.redeem(invitee, START)

    assert used.redeemed_by == invitee
    assert pair.membership_of(invitee) == Membership(invitee, BOSNIAN, ARABIC)


@pytest.mark.parametrize(
    ("who", "when", "message"),
    [
        ("inviter", START, "own invitation"),
        ("other", START + timedelta(days=7), "expired"),
    ],
)
def test_invitation_rules(who: str, when: object, message: str) -> None:
    inviter = uuid4()
    invitation, _ = Invitation.issue(inviter, ARABIC, BOSNIAN, START)
    user = inviter if who == "inviter" else uuid4()
    with pytest.raises(InvitationError, match=message):
        invitation.redeem(user, when)  # type: ignore[arg-type]


def test_invitation_is_single_use() -> None:
    invitation, _ = Invitation.issue(uuid4(), ARABIC, BOSNIAN, START)
    used, _ = invitation.redeem(uuid4(), START)
    with pytest.raises(InvitationError, match="already been used"):
        used.redeem(uuid4(), START)


def test_invitation_languages_must_differ() -> None:
    with pytest.raises(ValueError, match="differ"):
        Invitation.issue(uuid4(), ARABIC, ARABIC, START)


def test_invitation_must_expire_after_creation() -> None:
    invitation, _ = Invitation.issue(uuid4(), ARABIC, BOSNIAN, START)
    with pytest.raises(ValueError, match="expire"):
        Invitation(
            id=invitation.id,
            inviter_id=invitation.inviter_id,
            inviter_teaches=ARABIC,
            inviter_learns=BOSNIAN,
            code_hash=invitation.code_hash,
            created_at=START,
            expires_at=START,
        )


# ------------------------------------------------------------ exchange


@pytest.mark.parametrize("text", ["", "   ", "x" * 501])
def test_text_must_be_present_and_short(text: str) -> None:
    with pytest.raises(ValueError):
        clean_text(text, "Sentence")


def test_text_whitespace_is_normalised() -> None:
    assert clean_text("  Dobar \n dan  ", "Sentence") == "Dobar dan"


def _contribution(**changes: object) -> Contribution:
    values: dict[str, object] = {
        "id": uuid4(),
        "pair_id": uuid4(),
        "author_id": uuid4(),
        "learner_id": uuid4(),
        "language": ARABIC,
        "text": "مرحبا",
        "created_at": START,
    }
    values.update(changes)
    return Contribution(**values)  # type: ignore[arg-type]


def test_gloss_and_its_language_go_together() -> None:
    with pytest.raises(ValueError, match="gloss needs its language"):
        _contribution(gloss="Hello")
    with pytest.raises(ValueError, match="different language"):
        _contribution(gloss="مرحبا", gloss_language=ARABIC)


def test_author_cannot_teach_themselves() -> None:
    same = uuid4()
    with pytest.raises(ValueError, match="someone else"):
        _contribution(author_id=same, learner_id=same)


def _attempt() -> Attempt:
    return Attempt(
        id=uuid4(),
        pair_id=uuid4(),
        learner_id=uuid4(),
        reviewer_id=uuid4(),
        language=BOSNIAN,
        text="Ja sam dobro",
        created_at=START,
    )


def test_only_the_reviewer_can_correct() -> None:
    attempt = _attempt()
    with pytest.raises(AttemptNotFoundError):
        attempt.corrected(attempt.learner_id, "Dobro sam", None, START)


def test_attempt_is_corrected_once() -> None:
    attempt = _attempt()
    corrected = attempt.corrected(attempt.reviewer_id, "Dobro sam.", "Word order", START)

    assert corrected.correction is not None
    assert corrected.correction.comment == "Word order"
    assert not corrected.is_correct_as_written
    with pytest.raises(PairingError, match="already"):
        corrected.corrected(attempt.reviewer_id, "Dobro sam", None, START)


def test_attempt_needs_a_partner() -> None:
    same = uuid4()
    with pytest.raises(ValueError, match="partner"):
        Attempt(
            id=uuid4(),
            pair_id=uuid4(),
            learner_id=same,
            reviewer_id=same,
            language=BOSNIAN,
            text="Zdravo",
            created_at=START,
        )


# -------------------------------------------------------------- streak

A, B = uuid4(), uuid4()
GOAL = DailyGoal(sentences_per_day=2)
TODAY = date(2026, 11, 10)


def _days(*statuses: str) -> dict[date, dict[object, int]]:
    """Build counts ending today; 'M' met, 'C' covered by A, '-' missed, '?' open."""
    counts = {"M": {A: 2, B: 2}, "C": {A: 4, B: 0}, "-": {A: 1}, "?": {A: 1}}
    return {
        TODAY - timedelta(days=offset): counts[s] for offset, s in enumerate(reversed(statuses))
    }


@pytest.mark.parametrize(
    ("history", "expected"),
    [
        (("M", "M", "M"), 3),
        (("M", "M", "?"), 2),  # today still open
        (("M", "-", "M", "M"), 2),
        (("M", "C", "M"), 3),
        (("M", "C", "C", "M"), 2),  # a second cover in a row breaks the streak
        (("C", "M", "C", "M"), 4),
        (("-",), 0),
        ((), 0),
    ],
)
def test_streak(history: tuple[str, ...], expected: int) -> None:
    assert current_streak(GOAL, [A, B], _days(*history), TODAY) == expected  # type: ignore[arg-type]


def test_day_status() -> None:
    assert GOAL.day_status({A: 2, B: 3}, [A, B]) is DayStatus.MET
    assert GOAL.day_status({A: 4}, [A, B]) is DayStatus.COVERED
    assert GOAL.day_status({A: 3, B: 1}, [A, B]) is DayStatus.MISSED


@pytest.mark.parametrize("value", [0, 21])
def test_goal_bounds(value: int) -> None:
    with pytest.raises(ValueError, match="between"):
        DailyGoal(sentences_per_day=value)
