from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import ComparisonStatus, DocumentProcessingStatus, DocumentType, ValidationStatus


class UserResponse(BaseModel):
    id: int
    uuid: str
    first_name: str
    last_name: str
    institutional_id: str
    institution_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDocumentStatusResponse(BaseModel):
    user_id: int
    has_document: bool
    latest_document_id: int | None = None
    latest_document_uuid: str | None = None
    latest_document_type: DocumentType | None = None
    latest_status: DocumentProcessingStatus | None = None
    validation_status: ValidationStatus | None = None
    comparison_status: ComparisonStatus | None = None
    comparison_score: float | None = None
    confirmed: bool
    updated_at: datetime | None = None
