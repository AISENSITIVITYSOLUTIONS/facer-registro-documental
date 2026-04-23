from __future__ import annotations

from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.config import settings


class ImagePreprocessingService:
    def preprocess_document(self, image_bytes: bytes) -> dict:
        original_bgr = self._decode_image(image_bytes)
        working_bgr = original_bgr.copy()

        cropped = False
        if settings.document_auto_crop:
            cropped_bgr = self._crop_document(working_bgr)
            if cropped_bgr is not None:
                working_bgr = cropped_bgr
                cropped = True

        enhanced_bgr = self._enhance_for_ocr(working_bgr)
        detail_bgr = self._build_detail_image(working_bgr)

        return {
            "original_bgr": original_bgr,
            "working_bgr": working_bgr,
            "processed_bgr": enhanced_bgr,
            "detail_bgr": detail_bgr,
            "metadata": {
                "original_shape": list(original_bgr.shape),
                "working_shape": list(working_bgr.shape),
                "processed_shape": list(enhanced_bgr.shape),
                "detail_shape": list(detail_bgr.shape),
                "document_cropped": cropped,
            },
        }

    @staticmethod
    def _decode_image(image_bytes: bytes) -> np.ndarray:
        pil_image = Image.open(BytesIO(image_bytes))
        pil_image = ImageOps.exif_transpose(pil_image).convert("RGB")
        rgb_array = np.array(pil_image)
        return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)

    def _crop_document(self, image_bgr: np.ndarray) -> np.ndarray | None:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 75, 200)

        contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        image_area = image_bgr.shape[0] * image_bgr.shape[1]

        for contour in sorted(contours, key=cv2.contourArea, reverse=True):
            area = cv2.contourArea(contour)
            if area < image_area * 0.18:
                continue

            perimeter = cv2.arcLength(contour, True)
            approximation = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            if len(approximation) != 4:
                continue

            points = approximation.reshape(4, 2).astype("float32")
            ordered = self._order_points(points)
            return self._perspective_transform(image_bgr, ordered)

        return None

    @staticmethod
    def _order_points(points: np.ndarray) -> np.ndarray:
        rect = np.zeros((4, 2), dtype="float32")
        sums = points.sum(axis=1)
        rect[0] = points[np.argmin(sums)]
        rect[2] = points[np.argmax(sums)]

        diffs = np.diff(points, axis=1)
        rect[1] = points[np.argmin(diffs)]
        rect[3] = points[np.argmax(diffs)]
        return rect

    @staticmethod
    def _perspective_transform(image_bgr: np.ndarray, points: np.ndarray) -> np.ndarray:
        top_left, top_right, bottom_right, bottom_left = points

        width_top = np.linalg.norm(top_right - top_left)
        width_bottom = np.linalg.norm(bottom_right - bottom_left)
        max_width = max(int(width_top), int(width_bottom))

        height_right = np.linalg.norm(top_right - bottom_right)
        height_left = np.linalg.norm(top_left - bottom_left)
        max_height = max(int(height_right), int(height_left))

        destination = np.array(
            [
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1],
            ],
            dtype="float32",
        )

        matrix = cv2.getPerspectiveTransform(points, destination)
        return cv2.warpPerspective(image_bgr, matrix, (max_width, max_height))

    def _enhance_for_ocr(self, image_bgr: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(
            clipLimit=settings.preprocess_clahe_clip_limit,
            tileGridSize=(8, 8),
        )
        contrast = clahe.apply(gray)

        block_size = settings.preprocess_adaptive_block_size
        if block_size % 2 == 0:
            block_size += 1

        thresholded = cv2.adaptiveThreshold(
            contrast,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            settings.preprocess_adaptive_c,
        )

        denoised = cv2.medianBlur(thresholded, 3)
        sharpened = cv2.addWeighted(
            denoised,
            settings.preprocess_sharpen_strength,
            cv2.GaussianBlur(denoised, (0, 0), 3),
            -(settings.preprocess_sharpen_strength - 1.0),
            0,
        )

        return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)

    @staticmethod
    def _build_detail_image(image_bgr: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        upscaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        denoised = cv2.bilateralFilter(upscaled, 7, 50, 50)
        contrast = cv2.equalizeHist(denoised)
        return cv2.cvtColor(contrast, cv2.COLOR_GRAY2BGR)
