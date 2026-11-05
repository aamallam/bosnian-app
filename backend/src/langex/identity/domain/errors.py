"""Errors raised by the identity context."""


class AuthenticationError(Exception):
    """Any sign-in or token failure. The public message never says which
    check failed, so attackers learn nothing from it; `reason` is for logs."""

    def __init__(self, reason: str) -> None:
        super().__init__("Authentication failed")
        self.reason = reason
