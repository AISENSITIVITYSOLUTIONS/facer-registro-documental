from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from pydantic import BaseModel

from app.db import get_db
from app.models import Institution, User
from app.repositories import DocumentRepository, UserRepository
from app.schemas import UserDocumentStatusResponse, UserResponse


class UserCreateRequest(BaseModel):
    first_name: str
    last_name: str
    institutional_id: str
    institution_id: int = 1

router = APIRouter(tags=["users"])

user_repository = UserRepository()
document_repository = DocumentRepository()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateRequest, db: Session = Depends(get_db)) -> UserResponse:
    """Create a new user for document validation."""
    inst = db.query(Institution).filter(Institution.id == payload.institution_id).first()
    if inst is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Institucion no encontrada.")
    existing = db.query(User).filter(User.institutional_id == payload.institutional_id).first()
    if existing is not None:
        return UserResponse.model_validate(existing)
    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        institutional_id=payload.institutional_id,
        institution_id=payload.institution_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserResponse:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}/document-status", response_model=UserDocumentStatusResponse)
def get_user_document_status(user_id: int, db: Session = Depends(get_db)) -> UserDocumentStatusResponse:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    document = document_repository.get_latest_by_user_id(db, user_id)
    if document is None:
        return UserDocumentStatusResponse(
            user_id=user_id,
            has_document=False,
            confirmed=False,
        )

    return UserDocumentStatusResponse(
        user_id=user_id,
        has_document=True,
        latest_document_id=document.id,
        latest_document_uuid=document.uuid,
        latest_document_type=document.document_type,
        latest_status=document.status,
        validation_status=document.validation_status,
        comparison_status=document.comparison_status,
        comparison_score=document.comparison_score,
        confirmed=document.status.value == "confirmed",
        updated_at=document.updated_at,
    )
