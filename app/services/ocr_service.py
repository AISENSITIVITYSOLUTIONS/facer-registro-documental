from __future__ import annotations

import base64
import os
import tempfile
from collections.abc import Iterable
from io import BytesIO
from typing import Any

from fastapi import HTTPException, status
from PIL import Image

from app.config import settings
from app.services.image_preprocessing_service import ImagePreprocessingService

try:
    import pytesseract
    from pytesseract import Output as TesseractOutput
except ImportError:  # pragma: no cover - depende del entorno
    pytesseract = None
    TesseractOutput = None

try:
    from google.cloud import vision
except ImportError:  # pragma: no cover - depende del entorno
    vision = None


class OCRService:
    def __init__(self) -> None:
        self.engine = settings.normalized_ocr_engine
        self.preprocessor = ImagePreprocessingService()
        self._google_client = None

    def extract_text(self, image_bytes: bytes) -> dict[str, Any]:
        variants = self._build_variants(image_bytes)

        if self.engine == "google_vision":
            preferred_variant = self.preprocessor.select_preferred_variant(variants)
            result = self._extract_with_google_vision(preferred_variant["bytes"])
            result["preprocessing_variant"] = preferred_variant["name"]
            return result

        if self.engine == "tesseract":
            return self._extract_with_tesseract(variants)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El motor OCR configurado no es válido.",
        )

    def _build_variants(self, image_bytes: bytes) -> list[dict[str, Any]]:
        if not settings.enable_image_preprocessing:
            return [{"name": "original", "bytes": image_bytes}]
        return self.preprocessor.build_variants(image_bytes)

    @staticmethod
    def _create_vision_client():
        """Create Vision client using base64 credentials or ADC."""
        creds_b64 = settings.google_credentials_base64
        if creds_b64:
            creds_json = base64.b64decode(creds_b64)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="wb")
            tmp.write(creds_json)
            tmp.close()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name

        return vision.ImageAnnotatorClient()

    def _extract_with_google_vision(self, image_bytes: bytes) -> dict[str, Any]:
        if vision is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="La dependencia de Google Vision no está disponible en este entorno.",
            )

        if self._google_client is None:
            self._google_client = self._create_vision_client()

        image = vision.Image(content=image_bytes)

        if settings.vision_feature_type == "TEXT_DETECTION":
            response = self._google_client.text_detection(image=image)
        else:
            response = self._google_client.document_text_detection(image=image)

        if response.error.message:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"No fue posible procesar OCR con Google Vision: {response.error.message}",
            )

        full_text = response.full_text_annotation.text or ""
        text_annotations = response.text_annotations or []
        average_confidence = self._compute_average_confidence(response.full_text_annotation.pages)

        return {
            "text": full_text or (text_annotations[0].description if text_annotations else ""),
            "confidence": average_confidence,
            "engine": "google_vision",
        }

    def _extract_with_tesseract(self, variants: list[dict[str, Any]]) -> dict[str, Any]:
        if pytesseract is None or TesseractOutput is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Tesseract OCR no está disponible. Instale pytesseract y el binario tesseract.",
            )

        best_result: dict[str, Any] | None = None
        best_rank: tuple[float, int] | None = None
        config = f"--oem 3 --psm {settings.tesseract_page_segmentation_mode}"

        for variant in variants:
            image = Image.open(BytesIO(variant["bytes"]))
            try:
                data = pytesseract.image_to_data(
                    image,
                    lang=settings.tesseract_languages,
                    config=config,
                    output_type=TesseractOutput.DICT,
                )
                text = pytesseract.image_to_string(
                    image,
                    lang=settings.tesseract_languages,
                    config=config,
                )
            except pytesseract.TesseractError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"No fue posible procesar OCR local con Tesseract: {exc}",
                ) from exc
            except pytesseract.TesseractNotFoundError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="El binario de Tesseract no está instalado en el sistema.",
                ) from exc

            confidence = self._compute_tesseract_confidence(data)
            normalized_text = text.strip()
            rank = (confidence if confidence is not None else -1.0, len(normalized_text))
            current_result = {
                "text": normalized_text,
                "confidence": confidence,
                "engine": "tesseract",
                "preprocessing_variant": variant["name"],
            }
            if best_result is None or best_rank is None or rank > best_rank:
                best_result = current_result
                best_rank = rank

        return best_result or {
            "text": "",
            "confidence": None,
            "engine": "tesseract",
            "preprocessing_variant": "original",
        }

    @staticmethod
    def _compute_average_confidence(pages: Iterable) -> float | None:
        confidences: list[float] = []
        for page in pages or []:
            for block in page.blocks:
                if block.confidence is not None:
                    confidences.append(float(block.confidence))
        if not confidences:
            return None
        return round(sum(confidences) / len(confidences), 4)

    @staticmethod
    def _compute_tesseract_confidence(data: dict[str, list[Any]]) -> float | None:
        raw_values = data.get("conf", [])
        confidences: list[float] = []
        for value in raw_values:
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if numeric >= 0:
                confidences.append(numeric / 100.0)
        if not confidences:
            return None
        return round(sum(confidences) / len(confidences), 4)
