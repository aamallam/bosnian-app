from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from langex.api.dependencies import Uow
from langex.api.schemas import LanguageOut

router = APIRouter()


@router.get("/healthz", tags=["meta"], include_in_schema=False)
def healthz() -> dict[str, str]:
    """Liveness: the process is up. Does not touch the database, so the
    host's health check does not keep a scale-to-zero database awake."""
    return {"status": "ok"}


@router.get("/readyz", tags=["meta"], include_in_schema=False)
def readyz(uow: Uow) -> dict[str, str]:
    with uow.engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}


@router.get("/v1/languages", tags=["languages"])
def languages(uow: Uow) -> list[LanguageOut]:
    with uow.begin() as c:
        return [LanguageOut.of(p) for p in c.languages.all()]
