from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse

from fastapi import HTTPException, status

from app.config import settings
from app.models import CountryCode, DocumentType

try:
    from google.cloud import storage
except ImportError:  # pragma: no cover - depende del entorno
    storage = None


class StorageService:
    def __init__(self) -> None:
        self.backend = settings.normalized_storage_backend
        self.local_root = settings.storage_local_path
        self.client = None
        self.bucket = None

        if self.backend == "gcs":
            if storage is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="La dependencia de Google Cloud Storage no está disponible en este entorno.",
                )
            self.client = storage.Client(project=settings.gcp_project_id or None)
            self.bucket = self.client.bucket(settings.gcs_bucket_name)
        elif self.backend == "local":
            self.local_root.mkdir(parents=True, exist_ok=True)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El backend de almacenamiento configurado no es válido.",
            )

    def upload_document_image(
        self,
        *,
        image_bytes: bytes,
        content_type: str,
        country: CountryCode,
        document_type: DocumentType,
    ) -> str:
        if self.backend == "local":
            return self._upload_local(image_bytes, content_type, country, document_type)
        return self._upload_gcs(image_bytes, content_type, country, document_type)

    def download_document_image(self, stored_path: str) -> bytes:
        if stored_path.startswith("gs://"):
            return self._download_gcs(stored_path)
        if stored_path.startswith("file://"):
            return self._download_local(stored_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La ruta almacenada del documento es inválida.",
        )

    def _upload_local(
        self,
        image_bytes: bytes,
        content_type: str,
        country: CountryCode,
        document_type: DocumentType,
    ) -> str:
        extension = self._resolve_extension(content_type)
        relative_path = Path(settings.gcs_documents_prefix) / country.value / document_type.value / f"{uuid.uuid4()}{extension}"
        absolute_path = (self.local_root / relative_path).resolve()
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(image_bytes)
        return absolute_path.as_uri()

    def _download_local(self, stored_path: str) -> bytes:
        path = self._parse_file_uri(stored_path)
        if not path.exists() or not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La imagen del documento no se encontró en almacenamiento local.",
            )
        return path.read_bytes()

    def _upload_gcs(
        self,
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

    def _download_gcs(self, gcs_path: str) -> bytes:
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
    def _parse_file_uri(file_uri: str) -> Path:
        parsed = urlparse(file_uri)
        if parsed.scheme != "file":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="La ruta almacenada del documento es inválida.",
            )
        return Path(unquote(parsed.path)).resolve()

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
