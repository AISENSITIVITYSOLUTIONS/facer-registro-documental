from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, status

from app.config import settings
from app.models import CountryCode, DocumentType


class StorageService:
    def __init__(self) -> None:
        self.backend = settings.storage_backend.lower()
        self.local_storage_root = settings.local_storage_path
        if self.backend == "gcs":
            from google.cloud import storage

            self.client = storage.Client(project=settings.gcp_project_id or None)
            self.bucket = self.client.bucket(settings.gcs_bucket_name)
        else:
            self.client = None
            self.bucket = None

    def upload_document_image(
        self,
        *,
        image_bytes: bytes,
        content_type: str,
        country: CountryCode,
        document_type: DocumentType,
    ) -> str:
        extension = self._resolve_extension(content_type)
        object_name = f"{settings.gcs_documents_prefix}/{country.value}/{document_type.value}/{uuid.uuid4()}{extension}"
        if self.backend == "local":
            return self._upload_local_document_image(object_name=object_name, image_bytes=image_bytes)

        blob = self.bucket.blob(object_name)
        blob.upload_from_string(image_bytes, content_type=content_type)
        return f"gs://{self.bucket.name}/{object_name}"

    def download_document_image(self, gcs_path: str) -> bytes:
        if gcs_path.startswith("local://"):
            return self._download_local_document_image(gcs_path)

        bucket_name, object_name = self._parse_gcs_path(gcs_path)
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        if not blob.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La imagen del documento no se encontró en almacenamiento.",
            )
        return blob.download_as_bytes()

    def _upload_local_document_image(self, *, object_name: str, image_bytes: bytes) -> str:
        destination = self.local_storage_root / Path(object_name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(image_bytes)
        normalized_object_name = object_name.replace("\\", "/")
        return f"local://{normalized_object_name}"

    def _download_local_document_image(self, local_path: str) -> bytes:
        relative_path = local_path.replace("local://", "", 1).strip("/")
        resolved_path = (self.local_storage_root / relative_path).resolve()
        try:
            resolved_path.relative_to(self.local_storage_root)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="La ruta almacenada del documento es invalida.",
            ) from exc

        if not resolved_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La imagen del documento no se encontro en almacenamiento.",
            )

        return resolved_path.read_bytes()

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
