from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DocumentProcessingStatus, ValidationStatus
from app.repositories import DocumentRepository, UserRepository
from app.schemas import (
    DocumentConfirmResponse,
    DocumentExtractedFields,
    DocumentProcessResponse,
    DocumentResultsResponse,
    DocumentRetryResponse,
    DocumentUploadResponse,
)
from app.services import AuditService, ComparisonService, OCRService, ParsingService, StorageService
from app.utils import evaluate_image_quality, validate_country_document_type, validate_upload_file

router = APIRouter(prefix="/documents", tags=["documents"])

user_repository = UserRepository()
document_repository = DocumentRepository()
audit_service = AuditService()
comparison_service = ComparisonService()
parsing_service = ParsingService()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user_id: int = Form(...),
    country: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    from app.models import CountryCode, DocumentType

    try:
        country_enum = CountryCode(country)
        document_type_enum = DocumentType(document_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="País o tipo documental inválido.") from exc

    validate_country_document_type(country_enum, document_type_enum)
    image_bytes = await validate_upload_file(file)
    quality = evaluate_image_quality(image_bytes)

    storage_service = StorageService()
    source_image_gcs_path = storage_service.upload_document_image(
        image_bytes=image_bytes,
        content_type=file.content_type or "image/jpeg",
        country=country_enum,
        document_type=document_type_enum,
    )

    try:
        document = document_repository.create(
            db,
            user_id=user_id,
            country=country_enum,
            document_type=document_type_enum,
            source_image_gcs_path=source_image_gcs_path,
            capture_quality_score=quality["quality_score"],
            validation_status=(
                ValidationStatus.NEEDS_REVIEW if quality["recapture_recommended"] else ValidationStatus.PENDING
            ),
            status=DocumentProcessingStatus.UPLOADED,
        )
        audit_service.log_document_action(
            db=db,
            document=document,
            action="document_uploaded",
            details={
                "user_id": user_id,
                "country": country_enum.value,
                "document_type": document_type_enum.value,
                "capture_quality_score": quality["quality_score"],
                "recapture_recommended": quality["recapture_recommended"],
            },
        )
        db.commit()
        db.refresh(document)
        return DocumentUploadResponse.model_validate(document)
    except Exception:
        db.rollback()
        raise


@router.post("/{document_id}/process", response_model=DocumentProcessResponse)
def process_document(document_id: int, db: Session = Depends(get_db)) -> DocumentProcessResponse:
    document = document_repository.get_by_id(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")
    if document.status == DocumentProcessingStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El documento ya fue confirmado.")

    user = user_repository.get_by_id(db, document.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    document_repository.update(db, document, status=DocumentProcessingStatus.PROCESSING)
    audit_service.log_document_action(db=db, document=document, action="document_processing_started", details=None)
    db.commit()

    storage_service = StorageService()
    ocr_service = OCRService()

    try:
        image_bytes = storage_service.download_document_image(document.source_image_gcs_path)
        ocr_result = ocr_service.extract_text(image_bytes)
        parsing_result = parsing_service.parse_document(
            document_type=document.document_type,
            raw_text=ocr_result["text"],
            ocr_lines=ocr_result.get("lines"),
            ocr_hints=ocr_result.get("field_hints"),
        )
        extracted_fields: dict[str, Any] = parsing_result["fields"]
        extracted_fields_json = jsonable_encoder(extracted_fields)
        comparison_result = comparison_service.compare_user_against_document(
            user=user,
            extracted_fields=extracted_fields,
        )

        validation_status = ValidationStatus(parsing_result["validation_status"])
        comparison_status = comparison_result["comparison_status"]
        if comparison_status == "mismatch":
            validation_status = ValidationStatus.INVALID
        elif comparison_status == "low_match" or document.capture_quality_score is None:
            validation_status = ValidationStatus.NEEDS_REVIEW
        elif document.capture_quality_score < 0.45:
            validation_status = ValidationStatus.NEEDS_REVIEW
        elif validation_status == ValidationStatus.PENDING:
            validation_status = ValidationStatus.PENDING

        document = document_repository.update(
            db,
            document,
            full_name=extracted_fields.get("full_name"),
            first_name=extracted_fields.get("first_name"),
            last_name=extracted_fields.get("last_name"),
            birth_date=extracted_fields.get("birth_date"),
            sex=extracted_fields.get("sex"),
            national_id=extracted_fields.get("national_id"),
            document_number=extracted_fields.get("document_number"),
            curp=extracted_fields.get("curp"),
            nationality=extracted_fields.get("nationality"),
            issue_date=extracted_fields.get("issue_date"),
            expiration_date=extracted_fields.get("expiration_date"),
            extracted_text_raw=ocr_result["text"],
            extracted_fields_json=extracted_fields_json,
            extraction_confidence=ocr_result.get("confidence"),
            ocr_engine=ocr_result.get("engine"),
            comparison_status=comparison_result["comparison_status"],
            comparison_score=comparison_result["comparison_score"],
            validation_status=validation_status,
            status=DocumentProcessingStatus.PROCESSED,
        )
        audit_service.log_document_action(
            db=db,
            document=document,
            action="document_processed",
            details={
                "comparison_status": comparison_result["comparison_status"],
                "comparison_score": comparison_result["comparison_score"],
                "validation_status": validation_status.value,
            },
        )
        db.commit()
        db.refresh(document)
        return DocumentProcessResponse(
            id=document.id,
            uuid=document.uuid,
            status=document.status,
            validation_status=document.validation_status,
            comparison_status=document.comparison_status,
            comparison_score=document.comparison_score,
            extraction_confidence=document.extraction_confidence,
            capture_quality_score=document.capture_quality_score,
            extracted_fields=document.extracted_fields_json or {},
        )
    except Exception:
        db.rollback()
        document = document_repository.update(db, document, status=DocumentProcessingStatus.FAILED)
        audit_service.log_document_action(
            db=db,
            document=document,
            action="document_processing_failed",
            details={"document_id": document_id},
        )
        db.commit()
        raise


@router.get("/{document_id}/results", response_model=DocumentResultsResponse)
def get_document_results(document_id: int, db: Session = Depends(get_db)) -> DocumentResultsResponse:
    document = document_repository.get_by_id(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")

    extracted_fields = None
    if document.extracted_fields_json:
        extracted_fields = DocumentExtractedFields.model_validate(document.extracted_fields_json)

    return DocumentResultsResponse(
        id=document.id,
        uuid=document.uuid,
        user_id=document.user_id,
        country=document.country,
        document_type=document.document_type,
        status=document.status,
        validation_status=document.validation_status,
        comparison_status=document.comparison_status,
        comparison_score=document.comparison_score,
        extraction_confidence=document.extraction_confidence,
        capture_quality_score=document.capture_quality_score,
        ocr_engine=document.ocr_engine,
        extracted_fields=extracted_fields,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.post("/{document_id}/confirm", response_model=DocumentConfirmResponse)
def confirm_document(document_id: int, db: Session = Depends(get_db)) -> DocumentConfirmResponse:
    document = document_repository.get_by_id(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")
    if document.status != DocumentProcessingStatus.PROCESSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El documento debe estar procesado antes de confirmarse.",
        )
    if not document.extracted_fields_json:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No hay datos extraídos para confirmar.")

    if document.validation_status == ValidationStatus.INVALID:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El documento no puede confirmarse por inconsistencia documental.",
        )

    next_validation_status = ValidationStatus.NEEDS_REVIEW
    if document.comparison_status in {"exact_match", "high_match", "medium_match"}:
        next_validation_status = ValidationStatus.VALID

    try:
        document = document_repository.update(
            db,
            document,
            status=DocumentProcessingStatus.CONFIRMED,
            validation_status=next_validation_status,
        )
        audit_service.log_document_action(
            db=db,
            document=document,
            action="document_confirmed",
            details={
                "final_validation_status": next_validation_status.value,
                "comparison_status": document.comparison_status.value if document.comparison_status else None,
            },
        )
        db.commit()
        db.refresh(document)
        return DocumentConfirmResponse(
            id=document.id,
            uuid=document.uuid,
            status=document.status,
            validation_status=document.validation_status,
            comparison_status=document.comparison_status,
            comparison_score=document.comparison_score,
            confirmed=True,
        )
    except Exception:
        db.rollback()
        raise


@router.post("/{document_id}/retry", response_model=DocumentRetryResponse)
async def retry_document(
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentRetryResponse:
    document = document_repository.get_by_id(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")
    if document.status == DocumentProcessingStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El documento ya fue confirmado.")

    retry_count = document_repository.count_audit_events(db, document_id, "document_retry")
    from app.config import settings

    if retry_count >= settings.max_retry_count:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Se alcanzó el máximo de reintentos permitido.")

    image_bytes = await validate_upload_file(file)
    quality = evaluate_image_quality(image_bytes)
    storage_service = StorageService()
    source_image_gcs_path = storage_service.upload_document_image(
        image_bytes=image_bytes,
        content_type=file.content_type or "image/jpeg",
        country=document.country,
        document_type=document.document_type,
    )

    try:
        document = document_repository.update(
            db,
            document,
            source_image_gcs_path=source_image_gcs_path,
            capture_quality_score=quality["quality_score"],
            extracted_text_raw=None,
            extracted_fields_json=None,
            extraction_confidence=None,
            validation_status=(
                ValidationStatus.NEEDS_REVIEW if quality["recapture_recommended"] else ValidationStatus.PENDING
            ),
            comparison_status=None,
            comparison_score=None,
            ocr_engine=None,
            status=DocumentProcessingStatus.UPLOADED,
        )
        audit_service.log_document_action(
            db=db,
            document=document,
            action="document_retry",
            details={
                "retry_number": retry_count + 1,
                "capture_quality_score": quality["quality_score"],
                "recapture_recommended": quality["recapture_recommended"],
            },
        )
        db.commit()
        db.refresh(document)
        return DocumentRetryResponse(
            id=document.id,
            uuid=document.uuid,
            status=document.status,
            source_image_gcs_path=document.source_image_gcs_path,
            capture_quality_score=document.capture_quality_score,
            retry_count=retry_count + 1,
        )
    except Exception:
        db.rollback()
        raise
