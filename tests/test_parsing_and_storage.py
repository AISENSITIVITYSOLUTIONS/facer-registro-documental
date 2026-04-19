from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.models import CountryCode, DocumentType
from app.services.parsing_service import ParsingService
from app.services.storage_service import StorageService


def test_parse_passport_mrz_extracts_key_fields() -> None:
    service = ParsingService()
    raw_text = """
    P<MEXPEREZ<LOPEZ<<JUAN<CARLOS<<<<<<<<<<<<<<
    A12BC34D5MEX9001011H3001012<<<<<<<<<<<<<<04
    """

    result = service.parse_document(document_type=DocumentType.PASSPORT_MX, raw_text=raw_text)
    fields = result["fields"]

    assert fields["first_name"] == "JUAN CARLOS"
    assert fields["last_name"] == "PEREZ LOPEZ"
    assert fields["document_number"] == "A12BC34D5"
    assert fields["nationality"] == "MEX"
    assert result["validation_status"] == "pending"


def test_parse_ine_extracts_curp_and_ids() -> None:
    service = ParsingService()
    raw_text = """
    INSTITUTO NACIONAL ELECTORAL
    NOMBRE
    JUAN CARLOS PEREZ LOPEZ
    CURP PERJ900101HDFLRN09
    SEXO H
    01/01/1990
    1234567890123
    VIGENCIA 01/01/2030
    """

    result = service.parse_document(document_type=DocumentType.INE, raw_text=raw_text)
    fields = result["fields"]

    assert fields["full_name"] == "JUAN CARLOS PEREZ LOPEZ"
    assert fields["curp"] == "PERJ900101HDFLRN09"
    assert fields["national_id"] == "1234567890123"
    assert fields["document_number"] == "1234567890123"


def test_local_storage_upload_and_download_roundtrip(tmp_path: Path) -> None:
    original_backend = settings.storage_backend
    original_dir = settings.storage_local_dir
    try:
        settings.storage_backend = "local"
        settings.storage_local_dir = str(tmp_path)
        service = StorageService()

        payload = b"fake-image-bytes"
        stored_path = service.upload_document_image(
            image_bytes=payload,
            content_type="image/jpeg",
            country=CountryCode.MX,
            document_type=DocumentType.INE,
        )

        assert stored_path.startswith("file://")
        assert service.download_document_image(stored_path) == payload
    finally:
        settings.storage_backend = original_backend
        settings.storage_local_dir = original_dir
