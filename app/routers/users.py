from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories import DocumentRepository, UserRepository
from app.schemas import UserDocumentStatusResponse, UserResponse
from app.security import RequestContext, get_request_context

router = APIRouter(tags=["users"])

user_repository = UserRepository()
document_repository = DocumentRepository()


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    request_context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> UserResponse:
    user = user_repository.get_by_id_and_institution_id(db, user_id, request_context.institution_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}/document-status", response_model=UserDocumentStatusResponse)
def get_user_document_status(
    user_id: int,
    request_context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> UserDocumentStatusResponse:
    user = user_repository.get_by_id_and_institution_id(db, user_id, request_context.institution_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    document = document_repository.get_latest_by_user_id_and_institution_id(
        db,
        user_id,
        request_context.institution_id,
    )
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
