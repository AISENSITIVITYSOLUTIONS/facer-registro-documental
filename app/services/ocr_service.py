from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException, status
from google.cloud import vision

from app.config import settings


class OCRService:
    def __init__(self) -> None:
        self.client = vision.ImageAnnotatorClient()

    def extract_text(self, image_bytes: bytes) -> dict:
        image = vision.Image(content=image_bytes)

        if settings.vision_feature_type == "TEXT_DETECTION":
            response = self.client.text_detection(image=image)
        else:
            response = self.client.document_text_detection(image=image)

        if response.error.message:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No fue posible procesar OCR con Google Vision.",
            )

        full_text = response.full_text_annotation.text or ""
        text_annotations = response.text_annotations or []
        average_confidence = self._compute_average_confidence(response.full_text_annotation.pages)

        return {
            "text": full_text or (text_annotations[0].description if text_annotations else ""),
            "confidence": average_confidence,
            "engine": settings.default_ocr_engine,
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
