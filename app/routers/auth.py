"""
Simple authentication router for FaceR Registro Documental.

Provides a hardcoded login for demo purposes.
In production, this would connect to a proper auth system.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

# Demo credentials - in production these would be in a database
DEMO_USERS = {
    "Felipe": {
        "password": "deAlba",
        "user_id": 1,
        "full_name": "Felipe de Alba Murrieta",
        "role": "admin",
    },
    "admin": {
        "password": "FaceR2026",
        "user_id": 1,
        "full_name": "Administrador",
        "role": "admin",
    },
}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    user_id: int
    full_name: str
    role: str
    message: str


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    """Authenticate user with username and password."""
    user = DEMO_USERS.get(request.username)
    if user is None or user["password"] != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas. Verifica tu usuario y contraseña.",
        )

    return LoginResponse(
        success=True,
        user_id=user["user_id"],
        full_name=user["full_name"],
        role=user["role"],
        message=f"Bienvenido, {user['full_name']}",
    )
