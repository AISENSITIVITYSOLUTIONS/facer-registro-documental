from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


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
    auth_api_key: str = ""

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "zona_franca_backend"
    db_user: str = "root"
    db_password: str = "root"
    db_socket_dir: str = "/cloudsql"
    cloud_sql_connection_name: str | None = None
    instance_connection_name: str | None = None
    database_url: str | None = None

    gcp_project_id: str = ""
    gcs_bucket_name: str = ""
    gcs_documents_prefix: str = "documents"
    storage_backend: str = "gcs"
    local_storage_dir: str = "local_storage"
    paddle_home_dir: str = ".paddle"
    paddleocr_home_dir: str = ".paddleocr"
    paddleocr_lang: str = "es"
    paddleocr_use_angle_cls: bool = True
    paddleocr_use_gpu: bool = False
    paddleocr_show_log: bool = False
    paddleocr_det_limit_side_len: int = 1920
    paddleocr_drop_score: float = 0.35
    paddleocr_det_db_box_thresh: float = 0.35
    paddleocr_det_db_thresh: float = 0.25
    document_auto_crop: bool = True
    preprocess_clahe_clip_limit: float = 2.2
    preprocess_adaptive_block_size: int = 31
    preprocess_adaptive_c: int = 15
    preprocess_sharpen_strength: float = 1.35

    max_upload_size_bytes: int = 8 * 1024 * 1024
    min_image_width: int = 900
    min_image_height: int = 600
    min_capture_quality_score: float = 0.45
    max_retry_count: int = 3
    allowed_mime_types: str = "image/jpeg,image/png,image/jpg"

    default_ocr_engine: str = "paddleocr"
    request_timeout_seconds: int = 30

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )

    @computed_field  # type: ignore[misc]
    @property
    def effective_cloud_sql_connection_name(self) -> str | None:
        return self.cloud_sql_connection_name or self.instance_connection_name

    @computed_field  # type: ignore[misc]
    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url

        if self.effective_cloud_sql_connection_name:
            return (
                f"mysql+pymysql://{self.db_user}:{self.db_password}@/{self.db_name}"
                f"?unix_socket={self.db_socket_dir}/{self.effective_cloud_sql_connection_name}"
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
    def local_storage_path(self) -> Path:
        return Path(self.local_storage_dir).expanduser().resolve()

    @computed_field  # type: ignore[misc]
    @property
    def paddle_home_path(self) -> Path:
        return Path(self.paddle_home_dir).expanduser().resolve()

    @computed_field  # type: ignore[misc]
    @property
    def paddleocr_home_path(self) -> Path:
        return Path(self.paddleocr_home_dir).expanduser().resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
