from __future__ import annotations

import secrets
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Institution

API_KEY_HEADER = "X-API-Key"
INSTITUTION_CODE_HEADER = "X-Institution-Code"


@dataclass(frozen=True)
class RequestContext:
    institution_id: int
    institution_code: str


def get_request_context(
    x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER),
    x_institution_code: str | None = Header(default=None, alias=INSTITUTION_CODE_HEADER),
    db: Session = Depends(get_db),
) -> RequestContext:
    if not settings.auth_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La API no tiene AUTH_API_KEY configurada.",
        )

    if not x_api_key or not secrets.compare_digest(x_api_key, settings.auth_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key invalida o ausente.",
        )

    institution_code = (x_institution_code or "").strip()
    if not institution_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falta el header {INSTITUTION_CODE_HEADER}.",
        )

    institution = db.execute(
        select(Institution).where(Institution.code == institution_code)
    ).scalar_one_or_none()
    if institution is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La institucion solicitante no esta autorizada.",
        )

    return RequestContext(
        institution_id=int(institution.id),
        institution_code=institution.code,
    )
