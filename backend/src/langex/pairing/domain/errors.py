"""Errors raised by the pairing context."""


class PairingError(Exception):
    """Base class for pairing rule violations."""


class InvitationError(PairingError):
    """The invitation cannot be used (unknown, expired, used, or your own)."""


class PairNotFoundError(PairingError, LookupError):
    """Missing pair *or* a pair the caller does not belong to: one error for
    both, so outsiders cannot tell which pair IDs exist."""


class AttemptNotFoundError(PairingError, LookupError):
    """Missing attempt, or one the caller may not see."""


class DailyLimitReachedError(PairingError):
    """Anti-spam quota per person per day."""
