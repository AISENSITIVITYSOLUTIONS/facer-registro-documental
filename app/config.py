from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "FaceR Document Validation API"
    app_version: str = "3.0.0"
    environment: str = Field(default="development")
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    port: int = 8080

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "zona_franca_backend"
    db_user: str = "root"
    db_password: str = "root"
    db_socket_dir: str = "/cloudsql"
    cloud_sql_connection_name: str | None = None
    database_url: str | None = None

    storage_backend: str = "local"
    storage_local_dir: str = "./data/storage"
    gcp_project_id: str = ""
    gcs_bucket_name: str = ""
    gcs_documents_prefix: str = "documents"

    default_ocr_engine: str = "tesseract"
    vision_feature_type: str = "DOCUMENT_TEXT_DETECTION"
    tesseract_languages: str = "spa+eng"
    tesseract_page_segmentation_mode: int = 6
    enable_image_preprocessing: bool = True
    auto_create_db_schema: bool = True
    request_timeout_seconds: int = 30

    google_credentials_base64: str = ""  # Base64-encoded service account JSON for Google Vision

    max_upload_size_bytes: int = 8 * 1024 * 1024
    min_image_width: int = 900
    min_image_height: int = 600
    min_capture_quality_score: float = 0.45
    max_retry_count: int = 3
    allowed_mime_types: str = "image/jpeg,image/png,image/jpg"

    api_key: str = ""  # Required for production. Set via API_KEY env var.
    cors_origins: str = "*"  # Comma-separated allowed origins. Use "*" for dev, restrict in production.

    @computed_field  # type: ignore[misc]
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[misc]
    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url

        if self.cloud_sql_connection_name:
            return (
                f"mysql+pymysql://{self.db_user}:{self.db_password}@/{self.db_name}"
                f"?unix_socket={self.db_socket_dir}/{self.cloud_sql_connection_name}"
            )

        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def allowed_mime_types_list(self) -> list[str]:
        return [item.strip().lower() for item in self.allowed_mime_types.split(",") if item.strip()]

    @computed_field  # type: ignore[misc]
    @property
    def normalized_storage_backend(self) -> str:
        return self.storage_backend.strip().lower()

    @computed_field  # type: ignore[misc]
    @property
    def normalized_ocr_engine(self) -> str:
        return self.default_ocr_engine.strip().lower()

    @computed_field  # type: ignore[misc]
    @property
    def storage_local_path(self) -> Path:
        return Path(self.storage_local_dir).expanduser().resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
