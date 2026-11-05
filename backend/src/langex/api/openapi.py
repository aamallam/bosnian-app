"""Print the API's OpenAPI document. The mobile app keeps a copy
(`mobile/test/contract/openapi.json`) and its contract tests check the
client against it; a backend test fails when that copy is out of date.

    python -m langex.api.openapi > ../mobile/test/contract/openapi.json
"""

from __future__ import annotations

import json
import secrets
import sys
from typing import Any

from pydantic import SecretStr

from langex.api.app import create_app
from langex.bootstrap.settings import Environment, Settings

SNAPSHOT_COMMAND = "python -m langex.api.openapi > ../mobile/test/contract/openapi.json"


def document() -> dict[str, Any]:
    settings = Settings(
        env=Environment.DEVELOPMENT,
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret=SecretStr(secrets.token_urlsafe(48)),
        allow_dev_sign_in=True,
    )
    spec: dict[str, Any] = create_app(settings).openapi()
    return spec


def render() -> str:
    return json.dumps(document(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


if __name__ == "__main__":  # pragma: no cover
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.stdout.write(render())
