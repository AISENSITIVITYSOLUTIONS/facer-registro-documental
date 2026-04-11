from __future__ import annotations

from functools import lru_cache

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
    app_version: str = "2.0.0"
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

    gcp_project_id: str = ""
    gcs_bucket_name: str = ""
    gcs_documents_prefix: str = "documents"
    vision_feature_type: str = "DOCUMENT_TEXT_DETECTION"

    max_upload_size_bytes: int = 8 * 1024 * 1024
    min_image_width: int = 900
    min_image_height: int = 600
    min_capture_quality_score: float = 0.45
    max_retry_count: int = 3
    allowed_mime_types: str = "image/jpeg,image/png,image/jpg"

    default_ocr_engine: str = "google_vision"
    request_timeout_seconds: int = 30

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
