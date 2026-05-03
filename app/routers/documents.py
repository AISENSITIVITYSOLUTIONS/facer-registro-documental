from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import ComparisonStatus, DocumentProcessingStatus, DocumentType, ValidationStatus
from app.repositories import DocumentRepository, INERepository, UserRepository
from app.schemas import (
    DocumentCaptureAnalysisResponse,
    DocumentConfirmResponse,
    DocumentExtractedFields,
    DocumentProcessResponse,
    DocumentResultsResponse,
    DocumentRetryResponse,
    DocumentUploadResponse,
)
from app.services import AuditService, ComparisonService, INEParsingService, OCRService, ParsingService, StorageService
from app.utils import evaluate_image_quality, validate_country_document_type, validate_upload_file

router = APIRouter(prefix="/documents", tags=["documents"])

user_repository = UserRepository()
document_repository = DocumentRepository()
ine_repository = INERepository()
audit_service = AuditService()
comparison_service = ComparisonService()
parsing_service = ParsingService()
ine_parsing_service = INEParsingService()


@router.post("/upload-and-process", response_model=DocumentProcessResponse)
async def upload_and_process_document(
    user_id: int = Form(...),
    country: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentProcessResponse:
    """Combined endpoint: upload + OCR + parse in a single request.
    
    This avoids the issue of ephemeral storage on Cloud Run where
    the file might not be available for a subsequent /process call.
    """
    import traceback
    import logging
    logger = logging.getLogger(__name__)

    # Validate user
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    from app.models import CountryCode, DocumentType as DT

    try:
        country_enum = CountryCode(country)
        document_type_enum = DT(document_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="País o tipo documental inválido.") from exc

    validate_country_document_type(country_enum, document_type_enum)

    # Read and validate file
    image_bytes = await validate_upload_file(file)
    quality = evaluate_image_quality(image_bytes)

    # Store image
    storage_service = StorageService()
    source_image_gcs_path = storage_service.upload_document_image(
        image_bytes=image_bytes,
        content_type=file.content_type or "image/jpeg",
        country=country_enum,
        document_type=document_type_enum,
    )

    # Create document record
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
                "combined_endpoint": True,
            },
        )
        db.commit()
        db.refresh(document)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating document record: {e}")
        raise HTTPException(status_code=500, detail=f"Error al crear registro: {str(e)}")

    # Now process OCR directly on the image_bytes (no need to re-read from storage)
    document_repository.update(db, document, status=DocumentProcessingStatus.PROCESSING)
    audit_service.log_document_action(db=db, document=document, action="document_processing_started", details=None)
    db.commit()

    ocr_service = OCRService()

    try:
        ocr_result = ocr_service.extract_text(image_bytes)

        # Use specialized INE parser for INE documents
        if document.document_type == DocumentType.INE:
            ine_fields = ine_parsing_service.parse(ocr_result["text"])
            extracted_fields: dict[str, Any] = ine_fields

            # Save to documentos_ine_mexico table
            ine_repository.create(
                db,
                usuario_id=document.user_id,
                nombre=ine_fields.get("nombre"),
                apellido_paterno=ine_fields.get("apellido_paterno"),
                apellido_materno=ine_fields.get("apellido_materno"),
                nombre_completo=ine_fields.get("nombre_completo"),
                nacionalidad=ine_fields.get("nacionalidad"),
                fecha_nacimiento=ine_fields.get("fecha_nacimiento"),
                curp=ine_fields.get("curp"),
                domicilio=ine_fields.get("domicilio"),
                ocr_texto_original=ocr_result["text"],
                ocr_confianza=ocr_result.get("confidence"),
                imagen_frontal_url=document.source_image_gcs_path,
                fecha_captura=datetime.utcnow(),
                creado_por=f"user_{document.user_id}",
            )
        else:
            parsing_result = parsing_service.parse_document(
                document_type=document.document_type,
                raw_text=ocr_result["text"],
            )
            extracted_fields = parsing_result["fields"]

        # Compare against user
        comparison_result = comparison_service.compare_user_against_document(
            user=user,
            extracted_fields=extracted_fields,
        )

        # Determine validation status
        if document.document_type == DocumentType.INE:
            has_name = bool(extracted_fields.get("nombre_completo"))
            has_curp = bool(extracted_fields.get("curp"))
            if has_name and has_curp:
                validation_status = ValidationStatus.VALID
            elif has_name or has_curp:
                validation_status = ValidationStatus.NEEDS_REVIEW
            else:
                validation_status = ValidationStatus.INVALID
        else:
            validation_status = ValidationStatus(parsing_result["validation_status"])

        comparison_status = comparison_result["comparison_status"]
        if comparison_status == ComparisonStatus.MISMATCH.value:
            validation_status = ValidationStatus.INVALID
        elif comparison_status == ComparisonStatus.LOW_MATCH.value:
            validation_status = ValidationStatus.NEEDS_REVIEW

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
            extracted_fields_json=extracted_fields,
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
                "ocr_engine": ocr_result.get("engine"),
                "combined_endpoint": True,
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
    except HTTPException:
        db.rollback()
        document_repository.update(db, document, status=DocumentProcessingStatus.FAILED)
        db.commit()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing document: {traceback.format_exc()}")
        document_repository.update(db, document, status=DocumentProcessingStatus.FAILED)
        audit_service.log_document_action(
            db=db,
            document=document,
            action="document_processing_failed",
            details={"error": str(e), "combined_endpoint": True},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al procesar OCR: {str(e)}",
        )


@router.post("/analyze-capture", response_model=DocumentCaptureAnalysisResponse)
async def analyze_capture(
    file: UploadFile = File(...),
) -> DocumentCaptureAnalysisResponse:
    image_bytes = await validate_upload_file(file)
    quality = evaluate_image_quality(image_bytes)
    recommended_action = "continue"
    if quality["recapture_recommended"]:
        recommended_action = "recapture"

    return DocumentCaptureAnalysisResponse(
        file_size_bytes=len(image_bytes),
        width=quality["width"],
        height=quality["height"],
        brightness=quality["brightness"],
        contrast=quality["contrast"],
        sharpness=quality["sharpness"],
        glare_score=quality["glare_score"],
        quality_score=quality["quality_score"],
        meets_minimum=quality["meets_minimum"],
        recapture_recommended=quality["recapture_recommended"],
        recommended_action=recommended_action,
        preprocessing_enabled=settings.enable_image_preprocessing,
    )


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

    from app.models import CountryCode, DocumentType as DT

    try:
        country_enum = CountryCode(country)
        document_type_enum = DT(document_type)
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
                "storage_backend": settings.normalized_storage_backend,
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

        # Use specialized INE parser for INE documents
        if document.document_type == DocumentType.INE:
            ine_fields = ine_parsing_service.parse(ocr_result["text"])
            extracted_fields: dict[str, Any] = ine_fields

            # Also save to documentos_ine_mexico table
            ine_repository.create(
                db,
                usuario_id=document.user_id,
                nombre=ine_fields.get("nombre"),
                apellido_paterno=ine_fields.get("apellido_paterno"),
                apellido_materno=ine_fields.get("apellido_materno"),
                nombre_completo=ine_fields.get("nombre_completo"),
                nacionalidad=ine_fields.get("nacionalidad"),
                fecha_nacimiento=ine_fields.get("fecha_nacimiento"),
                curp=ine_fields.get("curp"),
                domicilio=ine_fields.get("domicilio"),
                ocr_texto_original=ocr_result["text"],
                ocr_confianza=ocr_result.get("confidence"),
                imagen_frontal_url=document.source_image_gcs_path,
                fecha_captura=datetime.utcnow(),
                creado_por=f"user_{document.user_id}",
            )

            # Determine validation status for INE
            has_name = bool(ine_fields.get("nombre_completo"))
            has_curp = bool(ine_fields.get("curp"))
            if has_name and has_curp:
                validation_status = ValidationStatus.VALID
            elif has_name or has_curp:
                validation_status = ValidationStatus.NEEDS_REVIEW
            else:
                validation_status = ValidationStatus.INVALID
        else:
            # Use generic parser for other document types
            parsing_result = parsing_service.parse_document(
                document_type=document.document_type,
                raw_text=ocr_result["text"],
            )
            extracted_fields = parsing_result["fields"]
            validation_status = ValidationStatus(parsing_result["validation_status"])

        # Compare against user
        comparison_result = comparison_service.compare_user_against_document(
            user=user,
            extracted_fields=extracted_fields,
        )

        comparison_status = comparison_result["comparison_status"]
        if comparison_status == ComparisonStatus.MISMATCH.value:
            validation_status = ValidationStatus.INVALID
        elif comparison_status == ComparisonStatus.LOW_MATCH.value or document.capture_quality_score is None:
            validation_status = ValidationStatus.NEEDS_REVIEW
        elif document.capture_quality_score < settings.min_capture_quality_score:
            validation_status = ValidationStatus.NEEDS_REVIEW

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
            extracted_fields_json=extracted_fields,
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
                "ocr_engine": ocr_result.get("engine"),
                "preprocessing_variant": ocr_result.get("preprocessing_variant"),
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay campos extraídos para confirmar.",
        )

    document = document_repository.update(
        db,
        document,
        status=DocumentProcessingStatus.CONFIRMED,
        validation_status=ValidationStatus.VALID,
    )
    audit_service.log_document_action(
        db=db,
        document=document,
        action="document_confirmed",
        details={"document_id": document_id},
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

    retry_count = audit_service.count_retries(db, document_id)
    if retry_count >= settings.max_retry_count:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Se alcanzó el número máximo de reintentos.",
        )

    image_bytes = await validate_upload_file(file)
    quality = evaluate_image_quality(image_bytes)

    storage_service = StorageService()
    new_path = storage_service.upload_document_image(
        image_bytes=image_bytes,
        content_type=file.content_type or "image/jpeg",
        country=document.country,
        document_type=document.document_type,
    )

    document = document_repository.update(
        db,
        document,
        source_image_gcs_path=new_path,
        capture_quality_score=quality["quality_score"],
        status=DocumentProcessingStatus.UPLOADED,
        validation_status=ValidationStatus.PENDING,
        extracted_text_raw=None,
        extracted_fields_json=None,
        extraction_confidence=None,
        comparison_status=None,
        comparison_score=None,
        full_name=None,
        first_name=None,
        last_name=None,
        birth_date=None,
        sex=None,
        national_id=None,
        document_number=None,
        curp=None,
    )
    audit_service.log_document_action(
        db=db,
        document=document,
        action="document_retry",
        details={"retry_count": retry_count + 1},
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
