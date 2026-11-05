"""The mobile client's contract tests read a copy of the OpenAPI document.
This fails when the API changes and that copy was not refreshed."""

from __future__ import annotations

from pathlib import Path

import pytest

from langex.api.openapi import SNAPSHOT_COMMAND, render

SNAPSHOT = Path(__file__).resolve().parents[3] / "mobile" / "test" / "contract" / "openapi.json"


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="mobile/ is not checked out")
def test_mobile_openapi_snapshot_is_current() -> None:
    assert SNAPSHOT.read_text(encoding="utf-8") == render(), (
        f"The API changed. Refresh the mobile copy (from backend/): {SNAPSHOT_COMMAND}"
    )
