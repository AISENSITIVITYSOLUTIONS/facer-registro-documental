from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, status
from google.cloud import storage

from app.config import settings
from app.models import CountryCode, DocumentType


class StorageService:
    def __init__(self) -> None:
        self.client = storage.Client(project=settings.gcp_project_id or None)
        self.bucket = self.client.bucket(settings.gcs_bucket_name)

    def upload_document_image(
        self,
        *,
        image_bytes: bytes,
        content_type: str,
        country: CountryCode,
        document_type: DocumentType,
    ) -> str:
        extension = self._resolve_extension(content_type)
        object_name = (
            f"{settings.gcs_documents_prefix}/{country.value}/{document_type.value}/"
            f"{uuid.uuid4()}{extension}"
        )
        blob = self.bucket.blob(object_name)
        blob.upload_from_string(image_bytes, content_type=content_type)
        return f"gs://{self.bucket.name}/{object_name}"

    def download_document_image(self, gcs_path: str) -> bytes:
        bucket_name, object_name = self._parse_gcs_path(gcs_path)
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        if not blob.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La imagen del documento no se encontró en almacenamiento.",
            )
        return blob.download_as_bytes()

    @staticmethod
    def _parse_gcs_path(gcs_path: str) -> tuple[str, str]:
        if not gcs_path.startswith("gs://"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="La ruta almacenada del documento es inválida.",
            )
        path_without_prefix = gcs_path.replace("gs://", "", 1)
        bucket_name, _, object_name = path_without_prefix.partition("/")
        if not bucket_name or not object_name:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="La ruta almacenada del documento es inválida.",
            )
        return bucket_name, object_name

    @staticmethod
    def _resolve_extension(content_type: str) -> str:
        normalized = content_type.lower().strip()
        mapping = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
        }
        extension = mapping.get(normalized)
        if extension:
            return extension
        return Path(normalized.split("/")[-1]).suffix or ".img"
