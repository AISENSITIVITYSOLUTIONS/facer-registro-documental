from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CountryCode(str, enum.Enum):
    MX = "MX"
    CO = "CO"


class DocumentType(str, enum.Enum):
    INE = "INE"
    PASSPORT_MX = "PASSPORT_MX"
    CEDULA_CO = "CEDULA_CO"
    PASSPORT_CO = "PASSPORT_CO"


class ValidationStatus(str, enum.Enum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    NEEDS_REVIEW = "needs_review"


class ComparisonStatus(str, enum.Enum):
    EXACT_MATCH = "exact_match"
    HIGH_MATCH = "high_match"
    MEDIUM_MATCH = "medium_match"
    LOW_MATCH = "low_match"
    MISMATCH = "mismatch"


class DocumentProcessingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    users: Mapped[list[User]] = relationship("User", back_populates="institution")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    institutional_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    institution: Mapped[Institution] = relationship("Institution", back_populates="users")
    documents: Mapped[list[IdentityDocument]] = relationship("IdentityDocument", back_populates="user")


class IdentityDocument(Base):
    __tablename__ = "identity_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    country: Mapped[CountryCode] = mapped_column(Enum(CountryCode, name="country_code_enum"), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type_enum"), nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    national_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    curp: Mapped[str | None] = mapped_column(String(18), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(60), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    extracted_text_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_fields_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_status: Mapped[ValidationStatus] = mapped_column(
        Enum(ValidationStatus, name="validation_status_enum"),
        nullable=False,
        default=ValidationStatus.PENDING,
        server_default=ValidationStatus.PENDING.value,
    )
    comparison_status: Mapped[ComparisonStatus | None] = mapped_column(
        Enum(ComparisonStatus, name="comparison_status_enum"),
        nullable=True,
    )
    comparison_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_image_gcs_path: Mapped[str] = mapped_column(String(255), nullable=False)
    capture_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_engine: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[DocumentProcessingStatus] = mapped_column(
        Enum(DocumentProcessingStatus, name="document_processing_status_enum"),
        nullable=False,
        default=DocumentProcessingStatus.UPLOADED,
        server_default=DocumentProcessingStatus.UPLOADED.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship("User", back_populates="documents")
    audit_logs: Mapped[list[DocumentAuditLog]] = relationship(
        "DocumentAuditLog",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentAuditLog(Base):
    __tablename__ = "document_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("identity_documents.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    document: Mapped[IdentityDocument] = relationship("IdentityDocument", back_populates="audit_logs")
