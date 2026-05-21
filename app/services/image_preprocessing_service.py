from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


# Maximum dimension for OCR processing. Larger images are resized down
# to speed up Tesseract without losing text readability.
_MAX_OCR_DIMENSION = 2000


class ImagePreprocessingService:
    def build_variants(self, image_bytes: bytes) -> list[dict[str, Any]]:
        image = Image.open(BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image).convert("RGB")

        # Resize large images to speed up OCR (phone cameras produce 4000x3000+)
        max_dim = max(image.size)
        if max_dim > _MAX_OCR_DIMENSION:
            scale = _MAX_OCR_DIMENSION / max_dim
            new_size = (int(image.width * scale), int(image.height * scale))
            image = image.resize(new_size, Image.LANCZOS)

        variants: list[dict[str, Any]] = [
            {"name": "original", "bytes": self._to_png_bytes(image)},
            {"name": "grayscale_autocontrast", "bytes": self._grayscale_autocontrast(image)},
            {"name": "high_contrast_sharpened", "bytes": self._high_contrast_sharpened(image)},
            {"name": "binary_document", "bytes": self._binary_document(image)},
        ]
        return variants

    @staticmethod
    def select_preferred_variant(variants: list[dict[str, Any]]) -> dict[str, Any]:
        for preferred_name in ("high_contrast_sharpened", "grayscale_autocontrast", "original"):
            for variant in variants:
                if variant["name"] == preferred_name:
                    return variant
        return variants[0]

    @staticmethod
    def _to_png_bytes(image: Image.Image) -> bytes:
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()

    def _grayscale_autocontrast(self, image: Image.Image) -> bytes:
        transformed = ImageOps.grayscale(image)
        transformed = ImageOps.autocontrast(transformed, cutoff=1)
        return self._to_png_bytes(transformed)

    def _high_contrast_sharpened(self, image: Image.Image) -> bytes:
        transformed = ImageOps.grayscale(image)
        transformed = ImageOps.autocontrast(transformed, cutoff=1)
        transformed = ImageEnhance.Contrast(transformed).enhance(1.45)
        transformed = transformed.filter(ImageFilter.MedianFilter(size=3))
        transformed = transformed.filter(ImageFilter.SHARPEN)
        return self._to_png_bytes(transformed)

    def _binary_document(self, image: Image.Image) -> bytes:
        transformed = ImageOps.grayscale(image)
        transformed = ImageOps.autocontrast(transformed, cutoff=1)
        transformed = transformed.filter(ImageFilter.MedianFilter(size=3))
        threshold = transformed.point(lambda value: 255 if value > 155 else 0)
        return self._to_png_bytes(threshold)
