from __future__ import annotations

from functools import lru_cache
import os

from fastapi import HTTPException, status

from app.config import settings
from app.services.image_preprocessing_service import ImagePreprocessingService

settings.paddle_home_path.mkdir(parents=True, exist_ok=True)
settings.paddleocr_home_path.mkdir(parents=True, exist_ok=True)
os.environ["PADDLE_HOME"] = str(settings.paddle_home_path)
os.environ["XDG_CACHE_HOME"] = str(settings.paddle_home_path)
os.environ["HUB_HOME"] = str(settings.paddle_home_path / "hub")
os.environ["PPOCR_HOME"] = str(settings.paddleocr_home_path)
os.environ["PADDLEOCR_HOME"] = str(settings.paddleocr_home_path)

from paddleocr import PaddleOCR


@lru_cache(maxsize=1)
def get_paddleocr_engine() -> PaddleOCR:
    return PaddleOCR(
        use_angle_cls=settings.paddleocr_use_angle_cls,
        lang=settings.paddleocr_lang,
        use_gpu=settings.paddleocr_use_gpu,
        show_log=settings.paddleocr_show_log,
        det_limit_side_len=settings.paddleocr_det_limit_side_len,
        drop_score=settings.paddleocr_drop_score,
        det_db_box_thresh=settings.paddleocr_det_db_box_thresh,
        det_db_thresh=settings.paddleocr_det_db_thresh,
    )


class OCRService:
    def __init__(self) -> None:
        self.engine = settings.default_ocr_engine.lower()
        self.preprocessor = ImagePreprocessingService()
        self.ocr = get_paddleocr_engine()

    def extract_text(self, image_bytes: bytes) -> dict:
        if self.engine != "paddleocr":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El motor OCR configurado no esta soportado en esta version.",
            )

        try:
            prepared = self.preprocessor.preprocess_document(image_bytes)
            raw_result = self.ocr.ocr(prepared["processed_bgr"], cls=settings.paddleocr_use_angle_cls)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No fue posible procesar OCR con PaddleOCR.",
            ) from exc

        lines = self._normalize_result(raw_result)
        text = "\n".join(line["text"] for line in lines if line["text"]).strip()
        confidence = self._compute_average_confidence(lines)

        return {
            "text": text,
            "confidence": confidence,
            "engine": "paddleocr",
            "lines": lines,
            "preprocessing": prepared["metadata"],
        }

    @staticmethod
    def _normalize_result(raw_result: list | None) -> list[dict]:
        if not raw_result:
            return []

        if isinstance(raw_result, list) and raw_result and raw_result[0] is None:
            return []

        page_lines: list = []
        if isinstance(raw_result, list) and raw_result:
            first = raw_result[0]
            if (
                isinstance(first, list)
                and first
                and isinstance(first[0], (list, tuple))
                and len(first[0]) >= 2
                and isinstance(first[0][1], (list, tuple))
            ):
                page_lines = first
            elif (
                isinstance(first, (list, tuple))
                and len(first) >= 2
                and isinstance(first[1], (list, tuple))
            ):
                page_lines = [first]

        normalized: list[dict] = []
        for line in page_lines:
            if not isinstance(line, (list, tuple)) or len(line) < 2:
                continue
            box = line[0]
            payload = line[1]
            if not isinstance(payload, (tuple, list)) or len(payload) < 2:
                continue
            normalized.append(
                {
                    "box": box,
                    "text": str(payload[0]).strip(),
                    "confidence": float(payload[1]),
                }
            )
        return normalized

    @staticmethod
    def _compute_average_confidence(lines: list[dict]) -> float | None:
        confidences = [line["confidence"] for line in lines if isinstance(line.get("confidence"), float)]
        if not confidences:
            return None
        return round(sum(confidences) / len(confidences), 4)
