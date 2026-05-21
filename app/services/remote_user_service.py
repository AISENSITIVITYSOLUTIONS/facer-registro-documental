"""Service to fetch user data from the biometria-api service.

Instead of querying a local ``users`` table, this service calls the
biometria-api REST endpoint to validate that a user exists and retrieve
their name fields for INE comparison.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)

# Timeout for the HTTP call to biometria-api (seconds).
_REQUEST_TIMEOUT = 10.0


@dataclass
class RemoteUser:
    """Lightweight representation of a user fetched from biometria-api.

    Maps biometria-api's ``usuarios`` table fields to a structure compatible
    with the rest of facer-registro-documental (which expects first_name / last_name).
    """

    id: int
    uid: str | None
    first_name: str  # mapped from ``nombre``
    last_name: str   # mapped from ``a_paterno`` + ``a_materno``
    nombre: str
    a_paterno: str
    a_materno: str

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "RemoteUser":
        """Build a RemoteUser from the biometria-api JSON response."""
        nombre = data.get("nombre") or ""
        a_paterno = data.get("a_paterno") or ""
        a_materno = data.get("a_materno") or ""
        return cls(
            id=data["id"],
            uid=data.get("uid"),
            first_name=nombre,
            last_name=f"{a_paterno} {a_materno}".strip(),
            nombre=nombre,
            a_paterno=a_paterno,
            a_materno=a_materno,
        )


class RemoteUserService:
    """Fetches and validates users from the biometria-api service."""

    def __init__(self) -> None:
        self.base_url = settings.biometria_api_url.rstrip("/")

    def get_by_id(self, user_id: int) -> RemoteUser:
        """Fetch a user by ID from biometria-api.

        Raises HTTPException 404 if the user doesn't exist, or 502 if the
        remote service is unreachable.
        """
        url = f"{self.base_url}/api/usuarios/{user_id}"
        try:
            with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
                response = client.get(url)
        except httpx.RequestError as exc:
            logger.error("Failed to reach biometria-api at %s: %s", url, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No se pudo conectar al servicio de usuarios. Intenta de nuevo.",
            ) from exc

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado.",
            )

        if response.status_code != 200:
            logger.error(
                "biometria-api returned %d for user_id=%d: %s",
                response.status_code,
                user_id,
                response.text[:200],
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Error al consultar el servicio de usuarios.",
            )

        try:
            data = response.json()
        except Exception as exc:
            logger.error("Invalid JSON from biometria-api: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Respuesta inválida del servicio de usuarios.",
            ) from exc

        return RemoteUser.from_api_response(data)
