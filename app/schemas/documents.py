from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import ComparisonStatus, CountryCode, DocumentProcessingStatus, DocumentType, ValidationStatus


class DocumentExtractedFields(BaseModel):
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    address: str | None = None
    birth_date: date | None = None
    sex: str | None = None
    national_id: str | None = None
    document_number: str | None = None
    curp: str | None = None
    nationality: str | None = None
    issue_date: date | None = None
    expiration_date: date | None = None


class DocumentUploadResponse(BaseModel):
    id: int
    uuid: str
    user_id: int
    country: CountryCode
    document_type: DocumentType
    source_image_gcs_path: str
    capture_quality_score: float | None = None
    status: DocumentProcessingStatus
    validation_status: ValidationStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentProcessResponse(BaseModel):
    id: int
    uuid: str
    status: DocumentProcessingStatus
    validation_status: ValidationStatus
    comparison_status: ComparisonStatus | None = None
    comparison_score: float | None = None
    extraction_confidence: float | None = None
    capture_quality_score: float | None = None
    extracted_fields: dict[str, Any] = Field(default_factory=dict)


class DocumentResultsResponse(BaseModel):
    id: int
    uuid: str
    user_id: int
    country: CountryCode
    document_type: DocumentType
    status: DocumentProcessingStatus
    validation_status: ValidationStatus
    comparison_status: ComparisonStatus | None = None
    comparison_score: float | None = None
    extraction_confidence: float | None = None
    capture_quality_score: float | None = None
    ocr_engine: str | None = None
    extracted_fields: DocumentExtractedFields | None = None
    created_at: datetime
    updated_at: datetime


class DocumentConfirmResponse(BaseModel):
    id: int
    uuid: str
    status: DocumentProcessingStatus
    validation_status: ValidationStatus
    comparison_status: ComparisonStatus | None = None
    comparison_score: float | None = None
    confirmed: bool = True


class DocumentRetryResponse(BaseModel):
    id: int
    uuid: str
    status: DocumentProcessingStatus
    source_image_gcs_path: str
    capture_quality_score: float | None = None
    retry_count: int


class AuditEventResponse(BaseModel):
    id: int
    action: str
    details: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
