"""Access tokens as short-lived signed JWTs.

HS256 is enough while one service both issues and checks the tokens; move
to an asymmetric key (EdDSA) if another service ever needs to verify them.
Times are checked against the injected clock rather than the wall clock so
the rules are testable.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import jwt

from langex.identity.domain.errors import AuthenticationError

MIN_SECRET_BYTES = 32
_ALGORITHM = "HS256"
_LEEWAY = timedelta(seconds=30)  # tolerated clock skew


class JwtAccessTokens:
    def __init__(
        self,
        secret: str,
        *,
        issuer: str = "langex",
        audience: str = "langex-api",
        ttl: timedelta = timedelta(minutes=15),
    ) -> None:
        if len(secret.encode("utf-8")) < MIN_SECRET_BYTES:
            raise ValueError(f"The signing secret needs at least {MIN_SECRET_BYTES} bytes")
        self._secret = secret
        self._issuer = issuer
        self._audience = audience
        self._ttl = ttl

    def issue(self, account_id: UUID, now: datetime) -> str:
        claims = {
            "sub": str(account_id),
            "iss": self._issuer,
            "aud": self._audience,
            "iat": int(now.timestamp()),
            "exp": int((now + self._ttl).timestamp()),
            "jti": uuid4().hex,
        }
        return jwt.encode(claims, self._secret, algorithm=_ALGORITHM)

    def verify(self, token: str, now: datetime) -> UUID:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[_ALGORITHM],  # pinned: never trust the token's own "alg"
                audience=self._audience,
                issuer=self._issuer,
                options={
                    "require": ["sub", "iss", "aud", "iat", "exp"],
                    "verify_exp": False,
                    "verify_iat": False,
                    "verify_nbf": False,
                },
            )
            account_id = UUID(claims["sub"])
        except (jwt.PyJWTError, ValueError) as error:
            raise AuthenticationError(f"invalid access token: {error}") from error
        timestamp = now.timestamp()
        if claims["exp"] <= timestamp - _LEEWAY.total_seconds():
            raise AuthenticationError("access token expired")
        if claims["iat"] > timestamp + _LEEWAY.total_seconds():
            raise AuthenticationError("access token issued in the future")
        return account_id
