from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from io import BytesIO
from typing import Any

import numpy as np
from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.models import CountryCode, DocumentType

_ALLOWED_DOCUMENTS: dict[CountryCode, set[DocumentType]] = {
    CountryCode.MX: {DocumentType.INE, DocumentType.PASSPORT_MX},
    CountryCode.CO: {DocumentType.CEDULA_CO, DocumentType.PASSPORT_CO},
}

_CURP_REGEX = re.compile(r"^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    compact = re.sub(r"\s+", " ", without_accents).strip().upper()
    return compact


def split_full_name(full_name: str | None) -> tuple[str | None, str | None]:
    normalized = re.sub(r"\s+", " ", (full_name or "").strip())
    if not normalized:
        return None, None
    parts = normalized.split(" ")
    if len(parts) == 1:
        return parts[0], None
    midpoint = max(1, len(parts) // 2)
    return " ".join(parts[:midpoint]), " ".join(parts[midpoint:])


async def validate_upload_file(upload_file: UploadFile) -> bytes:
    if upload_file.content_type is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo no tiene MIME type.")

    content_type = upload_file.content_type.lower()
    if content_type not in settings.allowed_mime_types_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de archivo no permitido. Solo se aceptan imágenes JPG y PNG.",
        )

    content = await upload_file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío.")

    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo excede el tamaño máximo permitido.")

    return content



def _compute_sharpness(gray_array: np.ndarray) -> float:
    diff_x = np.diff(gray_array, axis=1)
    diff_y = np.diff(gray_array, axis=0)
    sharpness = float(np.mean(np.abs(diff_x)) + np.mean(np.abs(diff_y))) / 2.0
    return min(sharpness / 32.0, 1.0)



def evaluate_image_quality(image_bytes: bytes) -> dict[str, Any]:
    try:
        image = Image.open(BytesIO(image_bytes))
        image.verify()
        image = Image.open(BytesIO(image_bytes))
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La imagen es inválida o está corrupta.") from exc

    width, height = image.size
    if width < settings.min_image_width or height < settings.min_image_height:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen no cumple la resolución mínima requerida.",
        )

    rgb_image = image.convert("RGB")
    gray_image = rgb_image.convert("L")
    gray_array = np.asarray(gray_image, dtype=np.float32)

    brightness = float(np.mean(gray_array) / 255.0)
    contrast = float(np.std(gray_array) / 64.0)
    sharpness = _compute_sharpness(gray_array)

    brightness_score = 1.0 - min(abs(brightness - 0.55) / 0.55, 1.0)
    contrast_score = min(contrast, 1.0)
    glare_penalty = float(np.mean(gray_array > 245))
    glare_score = 1.0 - min(glare_penalty * 8.0, 1.0)
    resolution_score = min((width * height) / (1600 * 1200), 1.0)

    quality_score = round(
        (brightness_score * 0.20)
        + (contrast_score * 0.20)
        + (sharpness * 0.30)
        + (glare_score * 0.15)
        + (resolution_score * 0.15),
        4,
    )

    return {
        "width": width,
        "height": height,
        "brightness": round(brightness, 4),
        "contrast": round(contrast_score, 4),
        "sharpness": round(sharpness, 4),
        "glare_score": round(glare_score, 4),
        "quality_score": quality_score,
        "meets_minimum": quality_score >= settings.min_capture_quality_score,
        "recapture_recommended": quality_score < settings.min_capture_quality_score,
    }



def validate_country_document_type(country: CountryCode, document_type: DocumentType) -> None:
    allowed = _ALLOWED_DOCUMENTS.get(country, set())
    if document_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de documento no corresponde al país seleccionado.",
        )



def parse_date_safe(value: str | None, *, allow_future: bool = False) -> date | None:
    if not value:
        return None

    cleaned = value.strip().replace(".", "/").replace("-", "/")
    formats = ("%d/%m/%Y", "%Y/%m/%d", "%d/%m/%y", "%Y%m%d")
    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
            if parsed.year < 1900:
                return None
            if not allow_future and parsed > date.today():
                return None
            return parsed
        except ValueError:
            continue
    return None



def is_valid_curp(value: str | None) -> bool:
    if not value:
        return False
    return bool(_CURP_REGEX.fullmatch(normalize_text(value)))



def normalize_document_value(value: str | None) -> str | None:
    normalized = normalize_text(value)
    normalized = normalized.replace(" ", "")
    return normalized or None
