"""Runs the import-linter contracts from pyproject.toml as part of the test suite,
so a boundary violation fails locally, not only in CI."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
_SEARCH_PATH = os.pathsep.join([str(Path(sys.executable).parent), os.environ.get("PATH", "")])
LINT_IMPORTS = shutil.which("lint-imports", path=_SEARCH_PATH)


@pytest.mark.skipif(LINT_IMPORTS is None, reason="import-linter not installed")
def test_architecture_contracts_hold() -> None:
    assert LINT_IMPORTS is not None
    result = subprocess.run(  # noqa: S603 - fixed command, no user input
        [LINT_IMPORTS],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
