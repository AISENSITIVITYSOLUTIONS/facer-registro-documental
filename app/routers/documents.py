from __future__ import annotations
from difflib import SequenceMatcher

import logging
import traceback
import unicodedata
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import ComparisonStatus, DocumentProcessingStatus, DocumentType, ValidationStatus
from app.repositories import DocumentRepository, INERepository
from app.schemas import (
    DocumentCaptureAnalysisResponse,
    DocumentConfirmResponse,
    DocumentExtractedFields,
    DocumentProcessResponse,
    DocumentResultsResponse,
    DocumentRetryResponse,
    DocumentUploadResponse,
)
from app.services import AuditService, ComparisonService, INEParsingService, OCRService, ParsingService, RemoteUserService, StorageService
from app.utils import evaluate_image_quality, validate_country_document_type, validate_upload_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

remote_user_service = RemoteUserService()
document_repository = DocumentRepository()
ine_repository = INERepository()
audit_service = AuditService()
comparison_service = ComparisonService()
parsing_service = ParsingService()
ine_parsing_service = INEParsingService()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _sanitize_for_json(data: dict[str, Any]) -> dict[str, Any]:
    """Convert all non-JSON-serializable values (date, datetime, enum, etc.) to strings.

    This is critical because ``extracted_fields_json`` is a JSON column in the DB
    and Python ``date`` / ``datetime`` objects are **not** JSON serializable.
    """
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            sanitized[key] = value.isoformat()
        elif isinstance(value, date):
            sanitized[key] = value.isoformat()  # "YYYY-MM-DD"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_for_json(value)
        elif isinstance(value, (list, tuple)):
            sanitized[key] = [
                _sanitize_for_json(item)
                if isinstance(item, dict)
                else item.isoformat()
                if isinstance(item, (date, datetime))
                else item
                for item in value
            ]
        elif hasattr(value, "value"):
            # Handle enums
            sanitized[key] = value.value
        else:
            sanitized[key] = value
    return sanitized


def _safe_date(value: Any) -> date | None:
    """Safely convert a value to a ``date`` object for SQL Date columns."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    return None


def _safe_str(value: Any) -> str | None:
    """Return *value* as a string or ``None``."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _normalize_name(name: str) -> str:
    """Normalize a name for comparison: uppercase, strip accents, collapse whitespace."""
    name = name.upper().strip()
    # Remove accents (NFD decomposition + strip combining marks)
    name = unicodedata.normalize("NFD", name)
    name = "".join(ch for ch in name if unicodedata.category(ch) != "Mn")
    # Collapse multiple spaces
    name = " ".join(name.split())
    return name


def nombres_coinciden(nombre_ine: str, nombre_db: str, umbral: float = 0.75) -> bool:
    """Compare the name extracted from the INE against the name registered in the DB.

    Returns True if the similarity ratio is >= *umbral* (75% by default).
    Uses SequenceMatcher after normalizing both names (uppercase, no accents).
    """
    nombre_ine_norm = _normalize_name(nombre_ine)
    nombre_db_norm = _normalize_name(nombre_db)
    similitud = SequenceMatcher(None, nombre_ine_norm, nombre_db_norm).ratio()
    logger.info(
        "nombres_coinciden: INE=%r, DB=%r, similitud=%.4f, umbral=%.2f",
        nombre_ine_norm, nombre_db_norm, similitud, umbral,
    )
    return similitud >= umbral


def _update_document_with_extraction(
    db: Session,
    document: Any,
    extracted_fields: dict[str, Any],
    ocr_result: dict[str, Any],
    comparison_result: dict[str, Any],
    validation_status: ValidationStatus,
) -> Any:
    """Persist OCR results into the ``identity_documents`` row.

    All date values are sanitised before being stored in the JSON column.
    """
    sanitized_fields = _sanitize_for_json(extracted_fields)

    return document_repository.update(
        db,
        document,
        full_name=_safe_str(extracted_fields.get("full_name") or extracted_fields.get("nombre_completo")),
        first_name=_safe_str(extracted_fields.get("first_name") or extracted_fields.get("nombre")),
        last_name=_safe_str(extracted_fields.get("last_name") or extracted_fields.get("apellido_paterno")),
        birth_date=_safe_date(extracted_fields.get("birth_date") or extracted_fields.get("fecha_nacimiento")),
        sex=_safe_str(extracted_fields.get("sex") or extracted_fields.get("sexo")),
        national_id=_safe_str(extracted_fields.get("national_id") or extracted_fields.get("clave_elector")),
        document_number=_safe_str(extracted_fields.get("document_number")),
        curp=_safe_str(extracted_fields.get("curp")),
        nationality=_safe_str(extracted_fields.get("nationality") or extracted_fields.get("nacionalidad")),
        issue_date=_safe_date(extracted_fields.get("issue_date")),
        expiration_date=_safe_date(extracted_fields.get("expiration_date")),
        extracted_text_raw=ocr_result["text"],
        extracted_fields_json=sanitized_fields,
        extraction_confidence=ocr_result.get("confidence"),
        ocr_engine=ocr_result.get("engine"),
        comparison_status=comparison_result["comparison_status"],
        comparison_score=comparison_result["comparison_score"],
        validation_status=validation_status,
        status=DocumentProcessingStatus.PROCESSED,
    )


def _determine_validation_status(
    document_type: DocumentType,
    extracted_fields: dict[str, Any],
    comparison_result: dict[str, Any],
    parsing_result: dict[str, Any] | None,
    capture_quality_score: float | None,
) -> ValidationStatus:
    """Compute the validation status based on extraction quality and comparison."""
    if document_type == DocumentType.INE:
        has_name = bool(extracted_fields.get("nombre_completo"))
        has_curp = bool(extracted_fields.get("curp"))
        if has_name and has_curp:
            validation_status = ValidationStatus.VALID
        elif has_name or has_curp:
            validation_status = ValidationStatus.NEEDS_REVIEW
        else:
            validation_status = ValidationStatus.INVALID
    else:
        validation_status = ValidationStatus(parsing_result["validation_status"]) if parsing_result else ValidationStatus.PENDING

    # Override based on comparison
    comparison_status = comparison_result["comparison_status"]
    if comparison_status == ComparisonStatus.MISMATCH.value:
        validation_status = ValidationStatus.INVALID
    elif comparison_status == ComparisonStatus.LOW_MATCH.value:
        validation_status = ValidationStatus.NEEDS_REVIEW

    return validation_status


# ── INE Required Fields Validation ────────────────────────────────────────────

# Campos que DEBEN estar presentes para considerar el OCR del INE como exitoso.
_INE_REQUIRED_FIELDS: list[str] = [
    "nombre",
    "apellido_paterno",
    "nombre_completo",
    "curp",
    "domicilio",
]

# Variantes de imagen a intentar en orden durante reintentos de OCR.
# La primera (high_contrast_sharpened) ya se usa por defecto,
# así que los reintentos prueban las demás.
_OCR_RETRY_VARIANTS: list[str] = [
    "grayscale_autocontrast",
    "original",
    "binary_document",
]


def _validate_ine_required_fields(ine_fields: dict[str, Any]) -> list[str]:
    """Return a list of missing required field names.

    If the list is empty, all required fields are present.
    """
    missing: list[str] = []
    for field in _INE_REQUIRED_FIELDS:
        value = ine_fields.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


# ── Combined Upload + Process ──────────────────────────────────────────────────


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
    the file might not be available for a subsequent ``/process`` call.
    """
    # ── Validate user (remote: biometria-api) ─────────────────────────────
    user = remote_user_service.get_by_id(user_id)

    from app.models import CountryCode, DocumentType as DT

    try:
        logger.warning("country=%r document_type=%r", country, document_type)
        country_enum = CountryCode(country.strip().upper())
        document_type_enum = DT(document_type.strip().upper())

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="País o tipo documental inválido.",
        ) from exc

    validate_country_document_type(country_enum, document_type_enum)

    # ── Read & validate file ───────────────────────────────────────────────
    image_bytes = await validate_upload_file(file)
    quality = evaluate_image_quality(image_bytes)

    # ── Store image ────────────────────────────────────────────────────────
    storage_service = StorageService()
    source_image_gcs_path = storage_service.upload_document_image(
        image_bytes=image_bytes,
        content_type=file.content_type or "image/jpeg",
        country=country_enum,
        document_type=document_type_enum,
    )

    # ── Create document record ─────────────────────────────────────────────
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
        logger.error("Error creating document record: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear el registro del documento. Intenta de nuevo.",
        )

    # ── OCR + Parse ────────────────────────────────────────────────────────
    document_repository.update(db, document, status=DocumentProcessingStatus.PROCESSING)
    audit_service.log_document_action(db=db, document=document, action="document_processing_started", details=None)
    db.commit()

    ocr_service = OCRService()
    parsing_result: dict[str, Any] | None = None

    try:
        # ── OCR + Parse with automatic retry for INE ─────────────────────
        ocr_result = ocr_service.extract_text(image_bytes)

        if document.document_type == DocumentType.INE:
            ine_fields = ine_parsing_service.parse(ocr_result["text"])
            missing_fields = _validate_ine_required_fields(ine_fields)

            # Retry OCR with different image variants if required fields are missing.
            # IMPORTANT: We MERGE results across retries — keep fields that were
            # already extracted correctly and only fill in the missing ones.
            # This prevents a worse OCR variant from overwriting good data.
            best_fields = dict(ine_fields)  # Start with the first attempt's results

            retry_idx = 0
            while missing_fields and retry_idx < len(_OCR_RETRY_VARIANTS):
                variant_name = _OCR_RETRY_VARIANTS[retry_idx]
                retry_idx += 1
                logger.warning(
                    "INE OCR retry %d/%d (variant=%s): missing fields %s",
                    retry_idx,
                    len(_OCR_RETRY_VARIANTS),
                    variant_name,
                    missing_fields,
                )
                audit_service.log_document_action(
                    db=db,
                    document=document,
                    action="ocr_retry",
                    details={
                        "retry_number": retry_idx,
                        "variant": variant_name,
                        "missing_fields": missing_fields,
                    },
                )
                db.commit()

                # Retry with a different image variant
                ocr_result = ocr_service.extract_text_with_variant(image_bytes, variant_name)
                retry_fields = ine_parsing_service.parse(ocr_result["text"])

                # Merge: only fill in fields that are currently missing/empty
                for field_name in list(missing_fields):
                    new_value = retry_fields.get(field_name)
                    if new_value and (isinstance(new_value, str) and new_value.strip()):
                        best_fields[field_name] = new_value

                # Rebuild nombre_completo if we got new name parts
                if any(f in ["nombre", "apellido_paterno", "apellido_materno"] for f in missing_fields):
                    rebuilt_name = " ".join(
                        p for p in [
                            best_fields.get("apellido_paterno"),
                            best_fields.get("apellido_materno"),
                            best_fields.get("nombre"),
                        ] if p
                    )
                    if rebuilt_name:
                        best_fields["nombre_completo"] = rebuilt_name
                        best_fields["full_name"] = rebuilt_name

                missing_fields = _validate_ine_required_fields(best_fields)

            # Use the merged best_fields as the final result
            ine_fields = best_fields

            # If still missing fields after all retries, log a warning but
            # do NOT block the user — proceed with whatever we have.
            # The validation_status will reflect the incomplete extraction.
            if missing_fields:
                logger.warning(
                    "INE OCR incomplete after %d retries. Still missing: %s. Proceeding with partial data.",
                    len(_OCR_RETRY_VARIANTS),
                    missing_fields,
                )

            extracted_fields: dict[str, Any] = ine_fields

            # ── Validate INE name against registered user ────────────────
            nombre_ine = ine_fields.get("nombre_completo") or ""
            nombre_usuario = " ".join(filter(None, [
                getattr(user, "first_name", "") or "",
                getattr(user, "last_name", "") or "",
            ]))
            if nombre_ine and nombre_usuario:
                if not nombres_coinciden(nombre_ine, nombre_usuario):
                    logger.warning(
                        "INE name mismatch for user_id=%s: INE=%r vs DB=%r",
                        user_id, nombre_ine, nombre_usuario,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "La validación no tuvo éxito: Verifica que el documento cargado sea el correcto."
                        ),
                    )

            # Save to documentos_ine_mexico table
            ine_repository.create(
                db,
                usuario_id=document.user_id,
                nombre=ine_fields.get("nombre"),
                apellido_paterno=ine_fields.get("apellido_paterno"),
                apellido_materno=ine_fields.get("apellido_materno"),
                nombre_completo=ine_fields.get("nombre_completo"),
                nacionalidad=ine_fields.get("nacionalidad"),
                fecha_nacimiento=_safe_date(ine_fields.get("fecha_nacimiento")),
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

        # ── Compare against user ─────────────────────────────────────────
        comparison_result = comparison_service.compare_user_against_document(
            user=user,
            extracted_fields=extracted_fields,
        )

        # ── Determine validation status ──────────────────────────────────
        validation_status = _determine_validation_status(
            document_type=document.document_type,
            extracted_fields=extracted_fields,
            comparison_result=comparison_result,
            parsing_result=parsing_result,
            capture_quality_score=document.capture_quality_score,
        )

        # ── Persist results (with sanitised JSON) ──────────────────────────
        document = _update_document_with_extraction(
            db=db,
            document=document,
            extracted_fields=extracted_fields,
            ocr_result=ocr_result,
            comparison_result=comparison_result,
            validation_status=validation_status,
        )

        audit_service.log_document_action(
            db=db,
            document=document,
            action="document_processed",
            details=_sanitize_for_json({
                "comparison_status": comparison_result["comparison_status"],
                "comparison_score": comparison_result["comparison_score"],
                "validation_status": validation_status.value,
                "ocr_engine": ocr_result.get("engine"),
                "combined_endpoint": True,
            }),
        )
        db.commit()
        db.refresh(document)

        # ── Only expose nombre_completo to the frontend (privacy) ───────────
        # All fields are stored in the DB, but the API response only
        # returns the full name for display purposes.
        sanitized_fields = _sanitize_for_json(extracted_fields)
        safe_fields_for_frontend: dict[str, Any] = {
            "nombre_completo": sanitized_fields.get("nombre_completo") or sanitized_fields.get("full_name"),
        }

        return DocumentProcessResponse(
            id=document.id,
            uuid=document.uuid,
            status=document.status,
            validation_status=document.validation_status,
            comparison_status=document.comparison_status,
            comparison_score=document.comparison_score,
            extraction_confidence=document.extraction_confidence,
            capture_quality_score=document.capture_quality_score,
            extracted_fields=safe_fields_for_frontend,
        )
    except HTTPException:
        db.rollback()
        document_repository.update(db, document, status=DocumentProcessingStatus.FAILED)
        db.commit()
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error processing document: %s", traceback.format_exc())
        document_repository.update(db, document, status=DocumentProcessingStatus.FAILED)
        audit_service.log_document_action(
            db=db,
            document=document,
            action="document_processing_failed",
            details={"error": str(e)[:200], "combined_endpoint": True},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al procesar el documento. Por favor, intenta de nuevo con una foto más clara.",
        )


# ── Analyze Capture ────────────────────────────────────────────────────────────


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


# ── Upload (standalone) ───────────────────────────────────────────────────────


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user_id: int = Form(...),
    country: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    # Validate user (remote: biometria-api)
    user = remote_user_service.get_by_id(user_id)

    from app.models import CountryCode, DocumentType as DT

    try:
        logger.warning("country=%r document_type=%r", country, document_type)
        country_enum = CountryCode(country.strip().upper())
        document_type_enum = DT(document_type.strip().upper())

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


# ── Process (standalone) ───────────────────────────────────────────────────────


@router.post("/{document_id}/process", response_model=DocumentProcessResponse)
def process_document(document_id: int, db: Session = Depends(get_db)) -> DocumentProcessResponse:
    document = document_repository.get_by_id(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")
    if document.status == DocumentProcessingStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El documento ya fue confirmado.")

    # Validate user (remote: biometria-api)
    user = remote_user_service.get_by_id(document.user_id)

    document_repository.update(db, document, status=DocumentProcessingStatus.PROCESSING)
    audit_service.log_document_action(db=db, document=document, action="document_processing_started", details=None)
    db.commit()

    storage_service = StorageService()
    ocr_service = OCRService()
    parsing_result: dict[str, Any] | None = None

    try:
        image_bytes = storage_service.download_document_image(document.source_image_gcs_path)
        ocr_result = ocr_service.extract_text(image_bytes)

        if document.document_type == DocumentType.INE:
            ine_fields = ine_parsing_service.parse(ocr_result["text"])
            extracted_fields: dict[str, Any] = ine_fields

            ine_repository.create(
                db,
                usuario_id=document.user_id,
                nombre=ine_fields.get("nombre"),
                apellido_paterno=ine_fields.get("apellido_paterno"),
                apellido_materno=ine_fields.get("apellido_materno"),
                nombre_completo=ine_fields.get("nombre_completo"),
                nacionalidad=ine_fields.get("nacionalidad"),
                fecha_nacimiento=_safe_date(ine_fields.get("fecha_nacimiento")),
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

        comparison_result = comparison_service.compare_user_against_document(
            user=user,
            extracted_fields=extracted_fields,
        )

        validation_status = _determine_validation_status(
            document_type=document.document_type,
            extracted_fields=extracted_fields,
            comparison_result=comparison_result,
            parsing_result=parsing_result,
            capture_quality_score=document.capture_quality_score,
        )

        document = _update_document_with_extraction(
            db=db,
            document=document,
            extracted_fields=extracted_fields,
            ocr_result=ocr_result,
            comparison_result=comparison_result,
            validation_status=validation_status,
        )

        audit_service.log_document_action(
            db=db,
            document=document,
            action="document_processed",
            details=_sanitize_for_json({
                "comparison_status": comparison_result["comparison_status"],
                "comparison_score": comparison_result["comparison_score"],
                "validation_status": validation_status.value,
                "ocr_engine": ocr_result.get("engine"),
            }),
        )
        db.commit()
        db.refresh(document)

        sanitized_fields = _sanitize_for_json(extracted_fields)
        return DocumentProcessResponse(
            id=document.id,
            uuid=document.uuid,
            status=document.status,
            validation_status=document.validation_status,
            comparison_status=document.comparison_status,
            comparison_score=document.comparison_score,
            extraction_confidence=document.extraction_confidence,
            capture_quality_score=document.capture_quality_score,
            extracted_fields=sanitized_fields,
        )
    except HTTPException:
        db.rollback()
        document_repository.update(db, document, status=DocumentProcessingStatus.FAILED)
        db.commit()
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error processing document %d: %s", document_id, traceback.format_exc())
        document_repository.update(db, document, status=DocumentProcessingStatus.FAILED)
        audit_service.log_document_action(
            db=db,
            document=document,
            action="document_processing_failed",
            details={"error": str(e)[:200], "document_id": document_id},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al procesar el documento. Por favor, intenta de nuevo con una foto más clara.",
        )


# ── Results ────────────────────────────────────────────────────────────────────


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


# ── Confirm ────────────────────────────────────────────────────────────────────


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


# ── Retry ──────────────────────────────────────────────────────────────────────


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
